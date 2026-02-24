# Release Notes v3.3.4

## Overview
v3.3.4 is a significant update adding full support for Steam Ovens with dedicated catalog implementation. This release addresses the architectural differences between regular ovens and steam ovens, which use nested capability structures.

**Key Improvements:**
1. Dedicated steam oven catalog for proper entity mapping
2. Full support for upperOven nested capabilities
3. Steam-specific features (water tank, descaling, steam programs)
4. Fixed entity metadata for all steam oven controls
5. Enhanced configuration entities for steam oven UI settings
6. Fixed temperatureRepresentation entity category violation
7. Removed false positive time jump warnings that occurred during normal operation

## New Feature: Dedicated Steam Oven Catalog

### Problem
Steam ovens (appliance type "SO") were using the same catalog as regular ovens, but their capability structure is fundamentally different:

**Regular Ovens (OV):**
```json
{
  "capabilities": {
    "cavityLight": {...},
    "targetTemperatureC": {...},
    "program": {...}
  }
}
```

**Steam Ovens (SO):**
```json
{
  "capabilities": {
    "upperOven": {
      "cavityLight": {...},
      "targetTemperatureC": {...},
      "program": {...}
    },
    "waterHardness": {...},
    "descalingReminderState": {...}
  }
}
```

This structural difference meant that entity metadata (icons, device classes, entity categories) wasn't being applied correctly, and the catalog couldn't properly define steam-specific features.

### Solution
Created a comprehensive dedicated catalog for steam ovens that properly handles the nested structure and includes all steam-specific capabilities.

**Files Changed:**
- **NEW**: `catalog_steam_oven.py` - Complete steam oven catalog with 40+ entities
- **MODIFIED**: `catalog_core.py` - Added steam oven lazy loader and updated appliance type mapping

### Steam Oven Entities

#### upperOven Container Entities (Nested Capabilities)

**State & Control:**
- `upperOven/applianceState` - Oven operational state (IDLE, READY_TO_START, RUNNING, etc.)
- `upperOven/doorState` - Door open/closed status
- `upperOven/executeCommand` - Start/Stop commands
- `upperOven/program` - Cooking program selection (BAKE, STEAM_HIGH, STEAMIFY, etc.)

**Temperature Control:**
- `upperOven/targetTemperatureC/F` - Target cooking temperature (80-230°C)
- `upperOven/displayTemperatureC/F` - Current cavity temperature
- `upperOven/targetFoodProbeTemperatureC/F` - Food probe target temperature
- `upperOven/displayFoodProbeTemperatureC/F` - Food probe current reading

**Timing Controls:**
- `upperOven/startTime` - Delayed start time (0-86340 seconds)
- `upperOven/targetDuration` - Cooking duration timer
- `upperOven/runningTime` - Elapsed cooking time
- `upperOven/timeToEnd` - Remaining time countdown
- `upperOven/reminderTime` - Kitchen timer / reminder

**Cooking Features:**
- `upperOven/cavityLight` - Oven cavity light control
- `upperOven/fastHeatUpFeature` - Fast preheat mode (DISABLED/ECO/ENABLED)
- `upperOven/processPhase` - Current cooking phase (NORMAL_HEATING, FAST_HEAT_UP, etc.)
- `upperOven/preheatComplete` - Preheat completion status

**Steam-Specific Features:**
- `upperOven/waterTankLevel` - Water tank level (EMPTY, OK, ALMOST_EMPTY, FULL)
- `upperOven/waterTrayInsertionState` - Drip tray detection (INSERTED/NOT_INSERTED)
- `upperOven/foodProbeInsertionState` - Food probe connection status

**End Actions:**
- `upperOven/targetDurationEndAction` - Action when timer completes (OFF, KEEP_HEATING, etc.)
- `upperOven/targetFoodProbeTemperatureEndAction` - Action when probe target reached

#### Root-Level Configuration Entities

**Steam Maintenance:**
- `waterHardness` - Water hardness setting (SOFT, MEDIUM, HARD, STEP_4)
- `descalingReminderState` - Descaling notification status
- `cleaningReminder` - Cleaning cycle reminder

**UI & Safety:**
- `childLock` - Control panel lock
- `displayLight` - Display brightness (5 levels: DISPLAY_LIGHT_1 to DISPLAY_LIGHT_5)
- `soundVolume` - System volume (1-4)
- `keySoundTone` - Button sound style (BEEP, CLICK, NONE)
- `clockStyle` - Clock display format (ANALOG, DIGITAL, NOT_SELECTED)
- `language` - Display language (26 languages supported)
- `localTimeAutomaticMode` - Automatic time synchronization (AUTOMATIC/MANUAL)

#### Inherited from Base Catalog
- `temperatureRepresentation` - Temperature unit (Celsius/Fahrenheit)
- `networkInterface/linkQualityIndicator` - WiFi signal strength
- `networkInterface/otaState` - Firmware update status
- `applianceState` - Overall appliance state (root level)
- `alerts` - Diagnostic alerts

### Impact
- ✅ All steam oven controls now have correct metadata (icons, device classes, categories)
- ✅ Commands properly formatted with nested structure: `{"upperOven": {"targetTemperatureC": 190.0}}`
- ✅ Full support for steam-specific features (water management, descaling)
- ✅ Complete UI configuration exposure (display, sound, language settings)
- ✅ Proper entity categorization (DIAGNOSTIC, CONFIG, standard)
- ✅ All 40+ steam oven entities fully functional

### Tested Appliances
- AEG BS7800B Steam Oven (PROFISTEAM_2 variant)
- Model: 944035035 (SO type)

### Command Flow Fixed
With the dedicated catalog, commands now work correctly:

1. **API reports capability**: `upperOven/targetTemperatureC`
2. **Integration creates entity**:
   - `entity_source = "upperOven"`
   - `entity_attr = "targetTemperatureC"`
3. **Catalog lookup**: `"upperOven/targetTemperatureC"` → ✅ Match found
4. **Entity gets correct metadata**:
   - Icon: `mdi:thermometer`
   - Device class: `NumberDeviceClass.TEMPERATURE`
   - Unit: `UnitOfTemperature.CELSIUS`
5. **Command sent**: `{"upperOven": {"targetTemperatureC": 180.0}}`
6. **API validates and executes**: ✅ Success

## Bug Fix: temperatureRepresentation Entity Category

### Problem
The `temperatureRepresentation` entity was defined in the base catalog with `entity_category=EntityCategory.CONFIG`, which is only valid for configuration entities (switches, selects, numbers). However, many appliances report this as read-only (`access: "read"`), making it a sensor entity. Home Assistant rejects sensors with CONFIG category.

### Root Cause
The base catalog assumed this would always be readwrite, but the actual API behavior varies by appliance:
- Some appliances: `"access": "readwrite"` → Should be SELECT entity with CONFIG category ✅
- Other appliances: `"access": "read"` → Becomes SENSOR entity, CONFIG category invalid ❌

### Solution
Changed `temperatureRepresentation` entity category from `EntityCategory.CONFIG` to `EntityCategory.DIAGNOSTIC`. Since DIAGNOSTIC is valid for both sensors and configuration entities, this works for all appliances regardless of access type.

**Files Changed:**
- `catalog_core.py` - Changed temperatureRepresentation entity_category to DIAGNOSTIC

### Impact
- ✅ Eliminates entity registration errors for appliances with read-only temperatureRepresentation
- ✅ Entity still appears in entity lists for monitoring
- ✅ No impact on functionality - just categorization
- ✅ Works for both read-only and readwrite access types

## Backward Compatibility

All changes are backward compatible:
- **Regular Ovens (OV)**: Continue using `CATALOG_OVEN` unchanged
- **Other Appliances**: Unaffected, use their respective catalogs
- **Existing Installations**: No migration required
- **Entity IDs**: No changes to entity naming or IDs

## Future Considerations

### Double Ovens
If appliances with both `upperOven` and `lowerOven` containers are encountered, the same pattern can be extended:
- Add `lowerOven/*` entries to catalog
- Or create dedicated catalog for double oven models

### DAM Appliances
Future support for DAM_* appliance types will follow similar nested structure patterns established in this release.

## Critical Bug Fixes

During comprehensive verification against real steam oven sample data (AEG BS7800B PROFISTEAM_2), several value inconsistencies were identified and corrected:

### 1. Fixed End Action Values
**Issues Corrected:**
- `upperOven/targetDurationEndAction` - Had incorrect values (KEEP_HEATING, KEEP_HEATING_AND_ALERT, NO_ACTION, OFF, OFF_AND_ALERT)
- `upperOven/targetFoodProbeTemperatureEndAction` - Same incorrect values

**Actual Values (per API specification):**
- `END_ACTION_JUST_SHOW_TEMP` - Display target temperature reached
- `END_ACTION_NONE` - No action
- `END_ACTION_SILENT_NOTIFICATION` - Silent notification only
- `END_ACTION_SOUND_ALARM` - Sound alert
- `END_ACTION_SOUND_ALARM_STOP_COOKING` - Sound alert and stop
- `END_ACTION_SOUND_ALARM_WARM_HOLD` - Sound alert and keep warm
- `END_ACTION_START_COOKING` - Begin cooking automatically
- `END_ACTION_STOP_COOKING` - Stop cooking automatically

**Impact:** Without this fix, users would be unable to select proper end actions from the Home Assistant UI, as the integration would reject the incorrect values.

### 2. Fixed Process Phase Values
**Issue:** The `upperOven/processPhase` entity did not define available values in the capability_info.

**Correct Values (per API specification):**
- `FAST_HEAT_UP` - Rapid preheating phase
- `HEAT_AND_HOLD` - Maintain temperature phase
- `NONE` - No active phase
- `NORMAL_HEATING` - Standard heating phase
- `TIME_EXTENSION` - Extended cooking time phase

**Impact:** Proper enum values ensure accurate state representation in Home Assistant UI and enable proper automations based on cooking phase.

### 3. Verification Process
All entity values were cross-referenced against actual steam oven capabilities data (SO-944035035.json, 7561 lines) to ensure 100% accuracy with API specifications.

### 4. Removed False Positive Time Jump Warnings
**Issue:** Users reported frequent warnings about "Large time jump detected" that occurred during normal operation:
- After system sleep/suspend/hibernate
- During SSE connection reconnections (every ~2 hours)
- When >1 hour passed between token validation checks

**Example Warning:**
```
[TOKEN-CHECK] Large time jump detected (7200s), possible clock adjustment or system sleep - token validity may be affected
```

**Root Cause:** The time jump detection logic couldn't distinguish between:
- Normal delays (system sleep, long intervals) → False alarm
- Actual clock changes (system time adjusted) → Real problem

**Solution:** Removed time jump detection entirely because:
1. Token expiry validation (`time_remaining > 900`) already handles expired tokens correctly
2. SDK has built-in error handling for refresh failures
3. False alarms caused unnecessary user confusion
4. Reliable clock change detection requires more sophisticated logic (monotonic time tracking)

**Impact:** Users will no longer see spurious warnings in their logs. Token management continues to work correctly with existing expiry checks.

## Testing Recommendations

For users with steam ovens:
1. ✅ Verify all entities appear correctly in Home Assistant
2. ✅ Test temperature changes, program selection, and start/stop commands
3. ✅ Check entity metadata (icons, device classes, categories)
4. ✅ Validate state updates via SSE streaming
5. ✅ Test steam-specific features (water tank, descaling reminders)
6. ✅ Verify UI configuration entities (display, sound, language)

## Files Modified

### New Files
- `custom_components/electrolux/catalog_steam_oven.py` (395 lines) - Complete steam oven catalog

### Modified Files
- `custom_components/electrolux/catalog_core.py` - Added steam oven support
- `custom_components/electrolux/util.py` - Removed time jump detection logic
- `tests/test_token_manager.py` - Removed obsolete time jump test
- `STEAM_OVEN_FIX.md` - Technical documentation
- `README.md` - Updated device types section
- `RELEASE_NOTES_v3.3.4.md` - This file

## Summary

v3.3.4 brings steam ovens to first-class citizen status with dedicated catalog implementation. Steam oven users will now experience proper entity metadata, full feature support, and reliable command execution. The architecture improvements also set the foundation for future nested capability structures in DAM appliances and multi-cavity ovens.

**Upgrade immediately if you have steam ovens** for full functionality and proper entity organization.
