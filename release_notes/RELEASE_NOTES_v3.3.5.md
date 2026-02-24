# Release Notes v3.3.5

## Overview
v3.3.5 is a critical bug fix release addressing a long-standing issue where several duration controls were incorrectly classified as read-only sensors instead of writable number entities. This release also introduces intelligent UI mode selection for number controls based on their value ranges.

**Key Improvements:**
1. Fixed 7 duration controls across washer, dryer, and washer-dryer catalogs
2. Controls now properly appear as writable number entities instead of read-only sensors
3. Smart UI mode selection: sliders for small ranges (≤100 steps), input boxes for large ranges
4. Better user experience for time and duration controls

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

#### Washer-Dryer Catalog (catalog_washer_dryer.py)
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
4. **custom_components/electrolux/number.py**: Complete rewrite of `mode` property (lines 79-106) with dynamic step-count-based logic, updated to use `NUMBER_MODE_SLIDER_MAX_STEPS` constant
5. **custom_components/electrolux/const.py**: Added maintainable constants for UI thresholds, time conversion, appliance states, and remote control states
6. **custom_components/electrolux/util.py**: Updated time conversion functions to use constants instead of hardcoded values
7. **custom_components/electrolux/sensor.py**: Updated to use `TIME_INVALID_SENTINEL` constant
8. **custom_components/electrolux/entity.py**: Enhanced remote control detection to explicitly handle `NOT_SAFETY_RELEVANT_ENABLED` state

### Test Coverage
Updated `tests/test_number.py` with comprehensive coverage:
- `test_mode_box_for_many_steps`: Validates BOX mode for large ranges (>100 steps)
- `test_mode_slider_for_few_steps`: Validates SLIDER mode for small ranges (≤100 steps)
- `test_mode_box_with_default_fallback_constraints`: Validates fallback behavior when constraints unavailable
- All 33 tests passing

### Validation
- **Code Quality**: No compilation errors, no Pylance type checking issues
- **Test Suite**: 100% pass rate (33/33 tests)
- **Catalog Audit**: Verified all other catalogs (oven, steam_oven, AC, refrigerator, purifier) use correct device classes

## Breaking Changes
**One-time manual cleanup required:** Users must delete stale `sensor.*` entities from Home Assistant UI and reload the integration to create new `number.*` entities.

## Compatibility
- Home Assistant: 2026.2.0+
- Python: 3.11+
- No changes to API communication or device compatibility

## What's Next
- Monitor user feedback on smart mode selection threshold
- Consider user preferences for UI mode if needed
- Continue catalog improvements based on real-world appliance data
