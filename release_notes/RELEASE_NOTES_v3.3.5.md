# Release Notes v3.3.5

## Overview
v3.3.5 is a comprehensive bug fix and enhancement release addressing critical issues with duration controls, dishwasher entity handling, and a design change that gives users more control over entity visibility. This release fixes catalog mismatches discovered through real-world appliance diagnostics and improves overall code quality through systematic constant refactoring.

**Key Improvements:**
1. **Design Change - More User Control**: Removed intentional filtering of nested catalog entities - enables 100+ additional entities across ALL appliance types (WiFi signal, maintenance counters, program options, etc.) for users who want them
2. **Security Protection**: Automatic blocking of dangerous entities (UNINSTALL, authorization commands) to prevent appliance damage
3. **Blacklist Cleanup**: Restored useful entities (maintenance tracking, temperature unit selection) previously blocked by legacy patterns
4. **AC Temperature Fix**: Fixed "Invalid step" errors for AC units with misaligned min/max ranges (e.g., 15.56°C-32.22°C converted from °F)
5. **Duration Controls**: Fixed 7 controls across washer/dryer catalogs that were incorrectly classified as sensors
6. **Smart UI Selection**: Automatic slider vs. input box selection based on value range
7. **Dishwasher Enhancements**: Fixed catalog mismatches for GlassCare 700 and similar models
8. **Entity Availability**: CONFIG/DIAGNOSTIC entities remain visible when appliances offline
9. **Code Quality**: Eliminated hardcoded values with maintainable constants
10. **Logging Improvements**: Reduced verbosity for operational messages

## Critical Bug Fix: Duration Controls Device Class

### Problem
Several duration controls were using `SensorDeviceClass.DURATION` instead of `NumberDeviceClass.DURATION`. This caused a critical issue where:

1. **Entity Platform Mismatch**: The integration's platform override logic (models.py) forces entities with `SensorDeviceClass` to be created as SENSOR platform entities (read-only)
2. **Missing Controls**: After integration reload, entities would show as "no longer being provided by the integration"
3. **Entity Registry Confusion**: Entities were registered as `sensor.*` instead of `number.*`
4. **No Control Capability**: Entities had `capabilities: null` in diagnostics, making them read-only

**User Impact:**
- Time-based controls (startTime, stopTime, dryingTime, antiCreaseValue) appeared to disappear
- Users couldn't set delay start times or adjust cycle parameters
- Entity registry showed stale, non-functional sensor entities

### Root Cause
The device_class determines which platform creates the entity:
- `SensorDeviceClass` → Creates read-only SENSOR entities
- `NumberDeviceClass` → Creates writable NUMBER entities with controls

Duration controls marked as "readwrite" in device details need `NumberDeviceClass.DURATION` to function as writable controls.

### Solution
Changed 7 duration controls from `SensorDeviceClass.DURATION` to `NumberDeviceClass.DURATION`:

#### Dryer Catalog (catalog_dryer.py)
- **stopTime** (line 93): Delay end time control
- **userSelections/antiCreaseValue** (line 346): Anti-crease duration for user programs
- **userSelections/dryingTime** (line 361): Drying duration for user programs
- **cyclePersonalization/antiCreaseValue** (line 541): Anti-crease duration for cycle customization
- **cyclePersonalization/dryingTime** (line 557): Drying duration for cycle customization

#### Washer Catalog (catalog_washer.py)
- **startTime** (line 192): Delay start time control
- **stopTime** (line 205): Delay end time control

#### Washer Dryer Catalog (catalog_washer_dryer.py)
- **stopTime** (line 140): Delay end time control

### Migration Required
Users upgrading to v3.3.5 must perform a one-time cleanup:

1. **Delete Stale Entities**: Remove old `sensor.electrolux_*_start_time`, `sensor.electrolux_*_stop_time`, etc. from Home Assistant UI (Settings → Devices & Services → Entities)
2. **Reload Integration**: Settings → Devices & Services → Electrolux → three-dot menu → Reload
3. **New Entities Appear**: Controls will reappear as `number.electrolux_*_start_time`, `number.electrolux_*_stop_time`, etc. with full control capability

## UX Enhancement: Smart Mode Selection

### Problem
Previously, the mode selection (slider vs. input box) was hardcoded based on entity names:
- `startTime`, `targetDuration` → Input box (BOX mode)
- All others → Slider (SLIDER mode)

This approach didn't consider the actual value range:
- **targetDuration**: 0-1440 minutes (step: 1) = 1440 possible values → Input box is appropriate
- **antiCreaseValue**: 30-120 minutes (step: 30) = 4 possible values → Slider is better despite being time-related

### Solution
Implemented dynamic mode selection based on step count:

```python
num_steps = ((max_val - min_val) / step_val) + 1

if num_steps <= NUMBER_MODE_SLIDER_MAX_STEPS:
    return NumberMode.SLIDER  # Visual selection is easy
else:
    return NumberMode.BOX  # Typing is faster
```

**Threshold Rationale:**
- **≤100 steps**: Visual selection remains manageable and intuitive
- **>100 steps**: Input box provides faster, more precise value entry
- Threshold defined as `NUMBER_MODE_SLIDER_MAX_STEPS` constant for easy tuning

### Real-World Examples

**Controls Using SLIDER Mode (≤100 steps):**
- `antiCreaseValue`: 4 steps (30/60/90/120 min) → Slider with 4 positions
- `dryingTime`: 31 steps (30-180 min, step 5) → Slider with visible increments
- `stopTime`: 25 steps (0-24 hours) → Slider for hour selection
- `targetTemperatureC` (oven): 41 steps (150-250°C, step 5) → Slider for temperature
- `targetFoodProbeTemperatureC`: 70 steps (40-110°C, step 1) → Slider for probe temp

**Controls Using BOX Mode (>100 steps):**
- `targetDuration`: 1440 steps (0-1440 min, step 1) → Input box for precise time entry
- `startTime`: 1440 steps (0-1440 min, step 1) → Input box for precise delay scheduling

### User Experience Impact
- **Small ranges**: Quick visual selection with sliders (e.g., pick 60 or 90 min anti-crease)
- **Large ranges**: Fast typing for precise values (e.g., type "65" for 65-minute wash)
- **Temperature controls**: Remain sliders for intuitive adjustment
- **Time durations**: Automatically optimal based on granularity

## Dishwasher Improvements

Based on real-world diagnostics from Electrolux GlassCare 700 dishwasher, this release fixes several catalog mismatches and entity availability issues.

### Design Change: Removed Nested Entity Filtering

**Previous Behavior:**
Line 577 in [models.py](custom_components/electrolux/models.py) used simple string checking to filter out nested catalog entities:
```python
attr_in_reported = catalog_key in self.reported_state
```

This intentionally prevented entities with slash-separated paths (e.g., `networkInterface/linkQualityIndicator`) from being created unless they appeared in the API capabilities list. The goal was to avoid cluttering the UI with sensors that have no value or aren't implemented in the firmware.

**New Approach - User Choice:**
Changed to use the existing `get_state()` method that properly handles slash-separated paths:
```python
attr_in_reported = self.get_state(catalog_key) is not None
```

This allows ALL catalog entities to be created based on what's actually in the appliance state, giving users full visibility and the choice to manually disable entities they don't need.

**Impact:**
This change affects **100+ entities across ALL appliance types**:
- **Core catalog**: 8 entities (networkInterface/*, userSelections/programUID)
- **Steam Oven**: 25+ entities (all upperOven/* entities)
- **Washer/Dryer**: 50+ entities (userSelections/*, cyclePersonalization/*, autoDosing/*, fCMiscellaneousState/*)
- **Refrigerator**: 15+ entities (freezer/*, fridge/*, extraCavity/*)
- **Dishwasher**: 15+ entities (userSelections/*, miscellaneousState/*, applianceCareAndMaintenance0/*)
- **Air Conditioner**: Multiple networkInterface/* entities

After upgrading, users will see many additional entities including WiFi signal strength indicators, software version info, maintenance counters, and various program options. Some may be unimplemented or have no useful value - users can manually disable these entities through Home Assistant's UI (Settings → Devices & Services → Entities).

**🔒 SECURITY: Automatic Dangerous Entity Blocking**

To protect users from accidentally damaging their appliances, the integration now automatically blocks creation of dangerous entities that control low-level system functions. The following entities are **permanently blocked** and will never be created:

- `networkInterface/startUpCommand` - Contains UNINSTALL command that can factory reset the network module
- `networkInterface/command` - Contains authorization commands (APPLIANCE_AUTHORIZE, USER_AUTHORIZE, USER_NOT_AUTHORIZE) that can unpair the appliance

**Implementation Details:**
- Dangerous entities defined in `DANGEROUS_ENTITIES_BLACKLIST` (const.py) using regex patterns
- Filtered at entity creation level (models.py) - checked for both catalog and API capabilities sources
- Previous parent-level blocking (`networkInterface` in `ATTRIBUTES_BLACKLIST`) removed to allow safe diagnostic entities through
- Safe entities like `networkInterface/linkQualityIndicator`, `networkInterface/swVersion`, `networkInterface/otaState` now properly discovered from API capabilities
- Granular blocking approach: only dangerous children blocked, safe children allowed

**Why This Matters:**
These commands can permanently break WiFi connectivity, unpair the appliance from your account, or require professional service to restore. By blocking them at the code level, this prevents accidental use through automations, dashboards, or voice assistants.

**For Developers:**
The blacklist is easily maintainable using regex patterns. To add more dangerous entities, update `DANGEROUS_ENTITIES_BLACKLIST` in const.py.

### ATTRIBUTES_BLACKLIST Cleanup

**Removed Patterns:**
- `applianceCareAndMaintenance.*` - **Now Available**: Maintenance tracking entities showing service intervals, filter replacement reminders, and threshold counters. These provide useful information to users about when maintenance is needed (e.g., dishwasher filter cleaning after 60 cycles).
- `temperatureRepresentation` - **Now Available**: Changed from DIAGNOSTIC to CONFIG category, allowing users to select their preferred temperature unit (Celsius/Fahrenheit) for temperature displays.
- `^fPPN_OV.+` - **Removed**: Legacy pattern with no references in code or sample data.

**Remaining Patterns Documented:**
Each remaining blacklist pattern now includes explanatory comments:
- `^fCMiscellaneous.+` - Blocks fCMiscellaneous from API auto-discovery; whitelist allows specific useful children (waterUsage, tankAReserve, tankBReserve)
- `fcOptisenseLoadWeight.*` - Catalog-only with special error code filtering in sensor.py (filters 65408-65532 error codes)
- `applianceMainBoardSwVersion` - Catalog-only diagnostic info (disabled by default in entity registry)
- `coolingValveState` - Catalog-only exposure for refrigerators

**Why This Matters:**
The cleanup ensures useful entities are not inadvertently blocked while maintaining intentional control over entity discovery. Users now have access to maintenance tracking and temperature unit selection.

### Fixed displayOnFloor Entity Catalog

**Problem:**
The `displayOnFloor` select entity only defined "OFF" and "ON" values in the catalog, but real dishwashers support "GREEN" and "RED" LED options. This caused the entity to always show "unknown" when appliances used these additional values.

**Solution:**
Updated `catalog_dishwasher.py` (lines 138-152) to include all supported values:
- OFF: Display off
- ON: Display on
- **GREEN: Green LED indicator (NEW)**
- **RED: Red LED indicator (NEW)**

Users can now properly control and view all LED display options on compatible dishwashers.

### Fixed rinseAidLevel Locking Behavior

**Problem:**
The `rinseAidLevel` number entity was being locked (min=max) whenever the dishwasher's current program didn't explicitly support it. This prevented users from refilling rinse aid settings even when the appliance was OFF.

**Root Cause:**
`rinseAidLevel` is an appliance configuration setting (like waterHardness), not a cycle-dependent parameter. It should always be adjustable regardless of what program is running or whether the appliance is active.

**Solution:**
1. Changed `rinseAidLevel` entity_category to `EntityCategory.CONFIG` (lines 87-99)
2. Updated `number.py` `_is_locked_by_program()` to exempt all CONFIG entities (lines 239-256)
3. Modified `entity.py` `extract_value()` to preserve CONFIG/DIAGNOSTIC entity values even when appliance offline (lines 563-573)

**Impact:**
- Users can now adjust rinse aid level at any time
- Settings remain visible and editable when dishwasher is OFF
- Consistent behavior with other CONFIG entities (waterHardness, etc.)

### Reduced Logging Verbosity

**Problem:**
During dishwasher cycles, the integration logged `"[DEFERRED-DEBUG] SSE timeToEnd update"` at INFO level every minute, flooding logs with operational details.

**Solution:**
Changed logging level from INFO to DEBUG in `coordinator.py` (line 389).

**Impact:**
- Cleaner INFO logs show only user-relevant events
- Operational tracking messages only appear when DEBUG logging enabled
- Reduces log file size for long-running cycles

### Enhanced Offline Entity Behavior

**Improvement:**
CONFIG and DIAGNOSTIC entities now remain visible with their last known values even when appliances are disconnected, preventing UI rendering issues and providing better troubleshooting data.

**Implementation:**
Modified `entity.py` `extract_value()` method to exempt:
- `connectivityState` (connection status)
- All `EntityCategory.CONFIG` entities (appliance settings)
- All `EntityCategory.DIAGNOSTIC` entities (troubleshooting data)

**Benefits:**
- Dishwasher settings remain accessible during network outages
- Diagnostic data preserved for troubleshooting
- Prevents UI cards from failing to render due to unavailable entities

### Fixed AC Temperature Step Alignment Issue

**Problem:**
AC units with misaligned temperature ranges (e.g., min=15.56°C from 60°F conversion, step=1.0) caused temperature commands to fail with "Invalid step" errors. When users set temperature to 24°C, the integration incorrectly calculated and sent 23.56°C to the appliance.

**Root Cause:**
The step validation logic in `format_command_for_appliance()` used the raw API minimum value (15.56) as the step base, causing step calculations to produce invalid intermediate values:
```python
# Before fix:
step_base = 15.56  # Raw API min
steps_from_base = (24.0 - 15.56) / 1.0 = 8.44
result = 15.56 + round(8.44) * 1.0 = 23.56  # ❌ Invalid!
```

Real-world valid values for this AC unit are integers: 16, 17, 18... 30°C, not fractional temperatures.

**Solution:**
Updated `util.py` `format_command_for_appliance()` (lines 1015-1025) to align the step base to the nearest step boundary:
```python
# After fix:
step_base = round(15.56 / 1.0) * 1.0 = 16.0  # Aligned to step boundary
steps_from_base = (24.0 - 16.0) / 1.0 = 8.0
result = 16.0 + round(8.0) * 1.0 = 24.0  # ✓ Valid!
```

**Impact:**
- AC temperature commands now work correctly with misaligned API ranges
- Prevents "Invalid step" validation errors from appliance API
- Handles unit conversion artifacts (°F to °C) automatically
- No user configuration required - fix is automatic

**Test Coverage:**
Added comprehensive test in `test_util.py` covering the AC unit scenario with min=15.56°C, max=32.22°C, step=1.0.

## Technical Details

### Code Quality Improvements: Constant Refactoring

Eliminated hardcoded "magic values" throughout the codebase by introducing maintainable constants in `const.py`:

**Time Conversion Constants:**
- `TIME_INVALID_SENTINEL = -1` - Indicates invalid/unset time values
- `SECONDS_PER_MINUTE = 60` - Used in time conversion functions
- `SECONDS_PER_HOUR = 3600` - Time calculation constant
- `SECONDS_PER_DAY = 86400` - Day conversion constant

**Appliance State Constants:**
- `FOOD_PROBE_STATE_INSERTED / NOT_INSERTED` - Food probe status
- `TIME_INVALID_OR_NOT_SET` - Time sentinel value
- `CONNECTIVITY_STATE_CONNECTED / DISCONNECTED` - Connection states

**Remote Control State Constants:**
- `REMOTE_CONTROL_ENABLED` - Standard remote control
- `REMOTE_CONTROL_NOT_SAFETY_RELEVANT_ENABLED` - Non-safety remote features
- `REMOTE_CONTROL_DISABLED` - Remote control disabled

**UI Behavior Constants:**
- `NUMBER_MODE_SLIDER_MAX_STEPS = 100` - Slider vs. input box threshold

**Benefits:**
- Single source of truth for all magic values
- Better code documentation through named constants
- Easier maintenance and future adjustments
- Type safety and consistency across modules
- Explicit handling of all appliance states (including `NOT_SAFETY_RELEVANT_ENABLED`)

### Files Modified
1. **custom_components/electrolux/catalog_dryer.py**: Fixed 5 duration entities, added NumberDeviceClass import
2. **custom_components/electrolux/catalog_washer.py**: Fixed 2 duration entities
3. **custom_components/electrolux/catalog_washer_dryer.py**: Fixed 1 duration entity, removed unused SensorDeviceClass import
4. **custom_components/electrolux/catalog_dishwasher.py**: Added GREEN/RED to displayOnFloor, changed rinseAidLevel to CONFIG category
5. **custom_components/electrolux/models.py**: Removed intentional nested entity filtering (line 577) - enables 100+ additional catalog entities; added security filtering for dangerous entities (lines 571-585, 639-652) using DANGEROUS_ENTITIES_BLACKLIST
6. **custom_components/electrolux/number.py**: Complete rewrite of `mode` property (lines 79-106) with dynamic step-count-based logic, updated to use `NUMBER_MODE_SLIDER_MAX_STEPS` constant, added CONFIG entity exemption in `_is_locked_by_program()` (lines 239-256)
7. **custom_components/electrolux/const.py**: Added maintainable constants for UI thresholds, time conversion, appliance states, remote control states, and **DANGEROUS_ENTITIES_BLACKLIST** (lines 73-79) for security protection; cleaned up **ATTRIBUTES_BLACKLIST** (removed `applianceCareAndMaintenance.*`, `temperatureRepresentation`, `^fPPN_OV.+`) with documented rationale for remaining patterns
8. **custom_components/electrolux/util.py**: Updated time conversion functions to use constants instead of hardcoded values; fixed step alignment bug in `format_command_for_appliance()` (lines 1015-1025) to handle misaligned API min values with step boundaries (AC temperature fix)
9. **custom_components/electrolux/sensor.py**: Updated to use `TIME_INVALID_SENTINEL` constant
10. **custom_components/electrolux/entity.py**: Enhanced remote control detection to explicitly handle `NOT_SAFETY_RELEVANT_ENABLED` state, modified `extract_value()` to preserve CONFIG/DIAGNOSTIC entities when offline (lines 563-573)
11. **custom_components/electrolux/coordinator.py**: Changed DEFERRED-DEBUG logging from INFO to DEBUG (line 389)
12. **tests/test_number.py**: Updated test fixture and test entity categories to correctly distinguish CONFIG vs program-dependent entities
13. **tests/test_entity_availability_rules.py**: Fixed test entity categories to match real-world behavior
14. **tests/test_util.py**: Added test for misaligned min/step AC temperature scenario (validates step alignment fix)

### Test Coverage
Updated test suites with comprehensive coverage for all changes:

**Number Entity Tests (tests/test_number.py):**
- `test_mode_box_for_many_steps`: Validates BOX mode for large ranges (>100 steps)
- `test_mode_slider_for_few_steps`: Validates SLIDER mode for small ranges (≤100 steps)
- `test_mode_box_with_default_fallback_constraints`: Validates fallback behavior when constraints unavailable
- Fixed entity_category for program-dependent entities (must be None, not CONFIG)
- 33/33 tests passing

**Entity Availability Tests (tests/test_entity_availability_rules.py):**
- Validates CONFIG entities never locked by program state
- Tests program-dependent entities properly locked when not supported
- Verifies offline behavior for CONFIG/DIAGNOSTIC entities
- Fixed 6 tests with incorrect entity_category assumptions
- All availability rule tests passing

**Full Test Suite:**
- 360 tests passing
- 12 warnings (pre-existing mock warnings, not errors)
- Zero compilation errors

### Validation
- **Code Quality**: No compilation errors, no Pylance type checking issues
- **Test Suite**: 100% pass rate (360/360 tests)
- **Catalog Audit**: Verified all other catalogs (oven, steam_oven, AC, refrigerator, purifier) use correct device classes
- **Real-World Testing**: Changes validated against actual Electrolux GlassCare 700 dishwasher diagnostics

## Breaking Changes
**Duration Controls Only (One-time cleanup required):**
Users with affected washer/dryer appliances must delete stale `sensor.*` duration entities from Home Assistant UI and reload the integration to create new `number.*` entities.

**Dishwasher Improvements:**
No breaking changes. All fixes are backward-compatible enhancements:
- New displayOnFloor values automatically available
- rinseAidLevel behavior improved (no longer incorrectly locked)
- Logging changes transparent to users
- Entity availability improvements prevent UI issues

## Compatibility
- Home Assistant: 2026.2.0+
- Python: 3.11+
- No changes to API communication or device compatibility

## What's Next
- Monitor user feedback on smart mode selection threshold
- Continue catalog improvements based on real-world appliance diagnostics
- Review other appliance catalogs for similar CONFIG entity issues
- Gather feedback on newly visible entities to assess which are most useful vs. should be hidden by default
