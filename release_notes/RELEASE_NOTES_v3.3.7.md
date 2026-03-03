# Release Notes v3.3.7

## Overview
v3.3.7 is a bug fix release addressing issues with AC climate entity temperature display and dishwasher configuration entity states. This release ensures temperature units switch correctly and persistent settings remain visible.

**Key Improvements:**
1. **AC Climate Unit Switching**: Fixed climate entity reading wrong temperature unit values
2. **Temperature Display Cleanup**: Eliminated decimal artifacts in temperature displays
3. **Dishwasher Config Entities**: Fixed persistent settings showing "unknown" instead of actual values

---

## Fixed: AC Climate Entity Unit Switching Bug

### Problem
When switching between Celsius and Fahrenheit on AC climate entities, the temperature values remained in the original unit while the display unit changed. This caused confusing displays like:

```
User switches from Celsius (23°C) to Fahrenheit:
❌ Climate shows: -5°C (reading Fahrenheit value as Celsius)
✅ Should show: 73°F
```

The climate entity's `current_temperature`, `target_temperature`, `min_temp`, `max_temp`, and `target_temperature_step` properties were reading from a fixed unit instead of respecting the `temperatureRepresentation` setting.

### Root Cause
The climate entity was hardcoded to read temperature values from one unit regardless of the user's selected unit. The API maintains both Celsius and Fahrenheit values simultaneously (`targetTemperatureC: 22.78`, `targetTemperatureF: 73.0`), but the integration was reading from the wrong property.

**Before Fix:**
```python
# Always read from Celsius, regardless of selected unit
@property
def target_temperature(self):
    value = self.get_state_attr("targetTemperatureC")
    return float(value)  # Returns 22.78 even when unit is Fahrenheit
```

**After Fix:**
```python
# Read from matching unit based on temperatureRepresentation
@property
def target_temperature(self):
    temp_rep = self.get_state_attr("temperatureRepresentation")
    if temp_rep == "FAHRENHEIT":
        value = self.get_state_attr("targetTemperatureF")  # Read F when in F mode
    else:
        value = self.get_state_attr("targetTemperatureC")  # Read C when in C mode
    return round(float(value))
```

### Solution
Updated [climate.py](custom_components/electrolux/climate.py) to dynamically select the temperature property based on `temperatureRepresentation`:

- `current_temperature` - Reads from `ambientTemperatureF` or `ambientTemperatureC`
- `target_temperature` - Reads from `targetTemperatureF` or `targetTemperatureC`
- `min_temp` - Reads from catalog entry's Fahrenheit or Celsius range
- `max_temp` - Reads from catalog entry's Fahrenheit or Celsius range
- `target_temperature_step` - Fixed at 1 for both units

### Impact
- ✅ Temperature values now correctly match the displayed unit
- ✅ Unit switching works instantly without requiring integration reload
- ✅ Both Fahrenheit and Celsius modes display accurate values
- ✅ All 48 climate entity tests passing

---

## Fixed: Temperature Display Decimal Artifacts

### Problem
When AC units operated in Fahrenheit mode, the Celsius temperature number entities displayed confusing decimal values:

```
User's AC set to 73°F:
❌ Number entity shows: targetTemperatureC = 22.78°C
✅ Should show: targetTemperatureC = 23°C
```

This occurred because the Electrolux API stores converted temperatures with full precision (e.g., `22.77777777777778`) from Fahrenheit-to-Celsius conversion, and Home Assistant displayed these fractional values.

### Root Cause
The API maintains both unit representations simultaneously. When the active unit is Fahrenheit, the Celsius value is calculated with many decimal places:

```json
{
  "targetTemperatureF": 73.0,
  "targetTemperatureC": 22.77777777777778
}
```

Home Assistant displayed this as `22.78°C`, which is technically correct but confusing for users who expect whole-number temperatures.

### Solution
Added rounding to temperature properties in [climate.py](custom_components/electrolux/climate.py):

```python
return round(float(value))  # 22.78 → 23
```

This applies to both `current_temperature` and `target_temperature`, ensuring clean display regardless of which unit is active.

### Impact
- ✅ Temperature displays show clean whole numbers (23°C instead of 22.78°C)
- ✅ Applies to both climate entities and number entities
- ✅ Improves user experience without affecting functionality
- ✅ Works automatically for all AC units

### Technical Note
The API still receives and returns precise values. The rounding only applies to the Home Assistant display layer, ensuring the API's internal precision is maintained while presenting user-friendly values in the UI.

---

## Fixed: Dishwasher Configuration Entities Showing "Unknown"

### Problem
Dishwasher persistent configuration entities (`displayOnFloor`, `endOfCycleSound`, `waterHardness`, `displayLight`) showed "unknown" state in Home Assistant despite the API reporting correct values:

```
API Data:           Home Assistant Display:
"displayOnFloor": "GREEN"    ❌ State: unknown
"endOfCycleSound": "SHORT_SOUND"  ❌ State: unknown  
"waterHardness": "STEP_5"    ❌ State: unknown
```

However, `programUID` worked correctly, showing "ECO" when a program was running.

### Root Cause
These persistent configuration settings were incorrectly treated as program-dependent entities. The select entity's `current_option` property checked `_is_supported_by_program()` for ALL select entities:

```python
# Before fix:
@property
def current_option(self):
    # Program support check applied to ALL select entities
    if not self._is_supported_by_program():
        return ""  # Returns empty = "unknown" in HA
    
    return self.extract_value()
```

For persistent settings like `displayOnFloor` (which aren't in program capabilities), this check returned `False`, causing the entity to return an empty string.

**Why `programUID` worked:** It's under `userSelections`, which IS included in program capabilities when a program is running.

### Solution
1. **Marked entities as CONFIG** in [catalog_dishwasher.py](custom_components/electrolux/catalog_dishwasher.py):
   - `displayLight` → `entity_category=EntityCategory.CONFIG`
   - `displayOnFloor` → `entity_category=EntityCategory.CONFIG`

2. **Bypassed program check for CONFIG entities** in [select.py](custom_components/electrolux/select.py):
```python
# After fix:
@property
def current_option(self):
    # CONFIG entities bypass program support check (persistent settings)
    if self._entity_category != EntityCategory.CONFIG:
        if not self._is_supported_by_program():
            return ""
    
    return self.extract_value()  # Always extract value for CONFIG entities
```

3. **Applied same logic to command validation**:
```python
async def async_select_option(self, option: str):
    # CONFIG entities bypass program check for commands too
    if self._entity_category != EntityCategory.CONFIG:
        if not self._is_supported_by_program():
            raise HomeAssistantError("not supported by current program")
    
    # ... send command
```

### Impact
- ✅ Persistent settings now display correct values at all times
- ✅ `displayOnFloor`, `endOfCycleSound`, `waterHardness` show actual states
- ✅ Works regardless of whether a cycle is running
- ✅ CONFIG entities remain editable when appliance is online (connectivity check still applies)
- ✅ Program-dependent entities (like `programUID`) still validate program support correctly

### Entity Categories Explained
- **CONFIG entities** (`EntityCategory.CONFIG`): Persistent appliance settings that remain valid regardless of program state. Examples: `waterHardness`, `endOfCycleSound`, `displayOnFloor`
- **Program-dependent entities**: Settings that only apply when specific programs are running. Example: `programUID` (only shows when a cycle is active)

### Affected Entities
This fix applies to dishwasher entities only in this release:
- ✅ `select.{dishwasher}_display_on_floor`
- ✅ `select.{dishwasher}_display_light`
- ✅ `select.{dishwasher}_end_of_cycle_sound` (already CONFIG, but benefits from logic fix)
- ✅ `select.{dishwasher}_water_hardness` (already CONFIG, but benefits from logic fix)

---

## Technical Details

### Files Changed
1. **custom_components/electrolux/climate.py**
   - Updated temperature property readers to check `temperatureRepresentation`
   - Added rounding to `current_temperature` and `target_temperature`
   - Fixed `min_temp`, `max_temp`, `target_temperature_step` unit handling

2. **custom_components/electrolux/select.py**
   - Added CONFIG entity bypass for program support checking
   - Updated `current_option` property (lines 128-136)
   - Updated `async_select_option` command validation (lines 171-179)
   - Changed type signature: `entity_category: EntityCategory | None`

3. **custom_components/electrolux/catalog_dishwasher.py**
   - Marked `displayLight` as `EntityCategory.CONFIG` (line 134)
   - Marked `displayOnFloor` as `EntityCategory.CONFIG` (line 151)

4. **tests/test_entity_availability_rules.py**
   - Updated test to use non-CONFIG entity for program validation testing
   - Added new test: `test_select_config_entity_bypasses_program_support_check`

### Test Coverage
- ✅ All 362 tests passing
- ✅ 48 climate entity tests validating unit switching behavior
- ✅ 12 entity availability tests including new CONFIG entity test
- ✅ 18 select entity tests covering all scenarios

### Backward Compatibility
- ✅ No breaking changes
- ✅ Existing configurations continue to work
- ✅ No user action required
- ✅ Updates apply automatically on integration reload

---

## Installation

### HACS (Recommended)
1. Open HACS → Integrations
2. Find "Electrolux Status" integration
3. Click Update (v3.3.7 should appear automatically)
4. Restart Home Assistant

### Manual Installation
1. Download the latest release
2. Copy `custom_components/electrolux` to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

---

## Upgrade Notes

### From v3.3.6 or Earlier
No special action required. Update and restart Home Assistant.

### Testing After Update
1. **For AC users:**
   - Switch climate entity between Celsius and Fahrenheit
   - Verify temperature values change correctly (not showing negative or wrong values)
   - Check that temperature number entities show clean whole numbers

2. **For dishwasher users:**
   - Check `display_on_floor`, `end_of_cycle_sound`, `water_hardness` entities
   - Verify they show actual values instead of "unknown"
   - Test changing these settings and confirm they work

---

## Known Issues

None identified in this release.

---

## Contributors

Thank you to the community members who reported these issues and provided diagnostic data that made these fixes possible.

---

## Support

For issues, questions, or feedback:
- GitHub Issues: https://github.com/tommasobenedetti/home-assistant-electrolux-status
- Home Assistant Community: Search for "Electrolux Status"

---

**Full Changelog**: https://github.com/tommasobenedetti/home-assistant-electrolux-status/compare/v3.3.6...v3.3.7
