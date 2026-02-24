# Steam Oven Implementation Fix

## Problem Analysis

Steam ovens (appliance type "SO") have a different capability structure compared to regular ovens (type "OV"):

### Regular Oven (OV) Structure:
```json
{
  "capabilities": {
    "cavityLight": {...},
    "targetTemperatureC": {...},
    "program": {...}
  }
}
```

### Steam Oven (SO) Structure:
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

**Key Difference**: Steam ovens nest their oven control capabilities under an `upperOven` container, while also having steam-specific configuration at the root level.

## Root Cause

The original implementation used the same catalog (`CATALOG_OVEN`) for both OV and SO appliance types. This catalog defined entities like:
- `"cavityLight"`
- `"targetTemperatureC"`  
- `"program"`

However, for steam ovens, the API returns these capabilities with paths like:
- `"upperOven/cavityLight"`
- `"upperOven/targetTemperatureC"`
- `"upperOven/program"`

When the integration tried to send commands for these entities:
- **Entity source**: `"upperOven"`
- **Entity attribute**: `"cavityLight"`
- **Command format**: `{"upperOven": {"cavityLight": true}}`

The commands appeared correct, but the catalog entries didn't match the capability paths, causing entity metadata (icons, device classes, entity categories) to not be applied correctly.

## Solution Implemented

Created a dedicated steam oven catalog that accounts for the nested structure:

### 1. New File: `catalog_steam_oven.py`

Defines all steam oven entities with correct paths:
- **upperOven entities**: `"upperOven/cavityLight"`, `"upperOven/targetTemperatureC"`, etc.
- **Root-level steam entities**: `"waterHardness"`, `"descalingReminderState"`, `"cleaningReminder"`
- **UI configuration entities**: `"displayLight"`, `"soundVolume"`, `"keySoundTone"`, `"language"`, `"clockStyle"`

### 2. Updated: `catalog_core.py`

Added lazy loader for steam oven catalog:
```python
@lru_cache(maxsize=None)
def _get_catalog_steam_oven():
    """Lazy load steam oven catalog."""
    from .catalog_steam_oven import CATALOG_STEAM_OVEN
    return CATALOG_STEAM_OVEN
```

Updated appliance type mapping:
```python
"SO": _get_catalog_steam_oven(),  # Steam Oven (dedicated catalog for upperOven nesting)
```

## Entities Covered

### upperOven Container Entities
- **State & Control**:
  - `upperOven/applianceState` - Oven operational state
  - `upperOven/doorState` - Door open/closed status
  - `upperOven/executeCommand` - Start/Stop commands
  - `upperOven/program` - Cooking program selection

- **Temperature Control**:
  - `upperOven/targetTemperatureC/F` - Target cooking temperature
  - `upperOven/displayTemperatureC/F` - Current cavity temperature
  - `upperOven/targetFoodProbeTemperatureC/F` - Food probe target
  - `upperOven/displayFoodProbeTemperatureC/F` - Food probe reading

- **Timing**:
  - `upperOven/startTime` - Delayed start time
  - `upperOven/targetDuration` - Cooking duration
  - `upperOven/runningTime` - Elapsed time
  - `upperOven/timeToEnd` - Remaining time
  - `upperOven/reminderTime` - Reminder timer

- **Features**:
  - `upperOven/cavityLight` - Oven light control
  - `upperOven/fastHeatUpFeature` - Fast preheat mode
  - `upperOven/processPhase` - Current cooking phase
  - `upperOven/preheatComplete` - Preheat status

- **Steam Specific**:
  - `upperOven/waterTankLevel` - Water tank level
  - `upperOven/waterTrayInsertionState` - Drip tray status
  - `upperOven/foodProbeInsertionState` - Probe connection status

- **End Actions**:
  - `upperOven/targetDurationEndAction` - Action when timer ends
  - `upperOven/targetFoodProbeTemperatureEndAction` - Action when probe target reached

### Root-Level Configuration Entities
- `waterHardness` - Water hardness setting
- `descalingReminderState` - Descaling notification
- `cleaningReminder` - Cleaning notification
- `childLock` - Control panel lock
- `displayLight` - Display brightness (5 levels)
- `soundVolume` - Volume level (1-4)
- `keySoundTone` - Button sound style
- `clockStyle` - Clock display format
- `language` - Display language
- `localTimeAutomaticMode` - Time sync mode

### Inherited from Base Catalog
- `temperatureRepresentation` - Temperature unit (Celsius/Fahrenheit)
- `networkInterface/linkQualityIndicator` - WiFi signal strength
- `networkInterface/otaState` - Firmware update status
- `applianceState` - Overall appliance state (root level)
- `alerts` - Diagnostic alerts

## Command Flow

With this fix, commands now work correctly:

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

## Testing Recommendations

1. **Verify Entity Creation**: Check that all steam oven entities appear in Home Assistant
2. **Test Commands**: Ensure temperature changes, program selection, and start/stop work
3. **Check Metadata**: Verify entities have correct icons, device classes, and categories
4. **Validate State Updates**: Confirm SSE events correctly update entity states
5. **Test Steam Features**: Verify water tank level, descaling reminders work correctly

## Backwards Compatibility

- **Regular Ovens (OV)**: No changes, continue using `CATALOG_OVEN`
- **Other Appliances**: Unaffected, use their respective catalogs
- **API Compatibility**: No API changes required, only catalog mapping

## Future Considerations

If double ovens with `lowerOven` container are encountered, the same pattern can be applied by adding `lowerOven/*` entries to the catalog or creating a dedicated catalog for double oven models.
