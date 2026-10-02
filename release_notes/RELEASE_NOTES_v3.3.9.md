# Release Notes v3.3.9

## Overview
v3.3.9 is a critical bug fix release addressing a regression introduced in v3.3.8 that prevented numeric, string, and boolean entity values from being created. This release also corrects the catalog definitions for oven Fahrenheit temperature control entities.

**CRITICAL FIXES:**
- **Entity Creation Regression**: Fixed `get_state()` method returning `None` for all numeric, string, and boolean values, causing these entities to be silently skipped during entity creation
- **Oven Fahrenheit Control Entities**: Changed oven `targetTemperatureF` and `targetFoodProbeTemperatureF` from writable number controls to read-only sensors (API only supports writing to Celsius versions for ovens. Air conditioners with temperature unit selection are not affected.)

---

## Fixed: Entity Creation Regression (Introduced in v3.3.8)

### Problem
After upgrading to v3.3.8, several entities were missing from appliances even though the values existed in the appliance's reported state. Most notably, **oven Fahrenheit temperature sensors** were missing:

**Oven Fahrenheit Temperature Sensors (Missing):**
- `displayTemperatureF` - Current oven temperature in Fahrenheit
- `displayFoodProbeTemperatureF` - Current food probe temperature in Fahrenheit
- `targetTemperatureF` - Target cooking temperature in Fahrenheit
- `targetFoodProbeTemperatureF` - Target food probe temperature in Fahrenheit

**Example from device diagnostics:**
```json
"reported": {
  "displayTemperatureC": 30.0,     // ✅ Entity created
  "displayTemperatureF": 86.0,     // ❌ Missing entity
  "targetTemperatureC": 150.0,     // ✅ Entity created
  "targetTemperatureF": 302.0,     // ❌ Missing entity
  "targetFoodProbeTemperatureC": 70.0,   // ✅ Entity created
  "targetFoodProbeTemperatureF": 158.0   // ❌ Missing entity
}
```

The Celsius entities were created successfully, but their Fahrenheit counterparts were silently omitted even though they were properly defined in the catalog and present in the appliance state.

### Root Cause
A change made in v3.3.8 to the `get_state()` method in [models.py](custom_components/electrolux/models.py#L218) introduced an incorrect type filter that returned `None` for all non-dictionary values:

**v3.3.8 Code (BUG):**
```python
def get_state(self, attr_name: str) -> dict[str, Any] | None:
    keys = attr_name.split("/")
    result: dict[str, Any] | None = self.reported_state
    
    for key in keys:
        if not isinstance(result, dict):
            return None
        result = result.get(key)
        if result is None:
            return None
    
    # ❌ BUG: Returns None for numeric/string/boolean values
    return result if isinstance(result, dict) else None
```

The `get_state()` method is used during entity creation to check if an attribute exists in the appliance's reported state:

```python
# Line 598 in models.py
attr_in_reported = self.get_state(catalog_key) is not None
```

When `get_state()` returned `None` for numeric values like `302.0`, the entity creation logic assumed the attribute didn't exist in the reported state and skipped creating the entity.

### Impact Scope
This regression affected **all appliance types** (ovens, refrigerators, washers, dryers, AC units, air purifiers) with entities that have direct numeric, string, or boolean values rather than nested dictionary structures.

**Most Visibly Affected:**
- **Ovens**: Fahrenheit temperature sensors (4 entities missing per oven)
- **All Appliances**: Any numeric sensors with direct number values (not nested in objects)
- **All Appliances**: Any string sensors with direct string values
- **All Appliances**: Any binary sensors with direct boolean values

**Why Celsius Worked But Fahrenheit Didn't:**
The bug affected both Celsius and Fahrenheit equally - they're both numeric values. However, the entity creation logic in v3.3.8 had a fallback mode that would create entities even when not found in reported state if they were marked as "writable" in capabilities. The Celsius entities were likely being created through this fallback mechanism, while Fahrenheit entities (being read-only display values) had no such fallback and were completely skipped.

### Fix
Removed the incorrect type filter from `get_state()` to allow it to return values of any type:

**v3.3.9 Code (FIXED):**
```python
def get_state(self, attr_name: str) -> Any:
    keys = attr_name.split("/")
    result: dict[str, Any] | None = self.reported_state
    
    for key in keys:
        if not isinstance(result, dict):
            return None
        result = result.get(key)
        if result is None:
            return None
    
    # ✅ FIXED: Returns values of any type (numbers, strings, bools, dicts)
    return result
```

**Changes Made:**
1. Changed return type from `dict[str, Any] | None` to `Any`
2. Removed the `if isinstance(result, dict) else None` check at the end
3. Method now correctly returns numeric values (302.0, 86.0), strings, booleans, and dictionaries

### Result
After upgrading to v3.3.9, all missing entities will be created on the next Home Assistant restart:

- ✅ Oven Fahrenheit temperature sensors will appear
- ✅ Any other missing numeric/string/boolean entities will be restored
- ✅ Entity creation logic works correctly for all value types
- ✅ No changes required to existing entity definitions or catalogs

### Testing
- All 364 integration tests pass
- MyPy type checking passes (32 source files, 0 errors)
- No regressions in existing functionality
- Verified fix with real oven device diagnostics showing all 4 Fahrenheit sensors in reported state

---

## Fixed: Oven Fahrenheit Temperature Control Entities

### Problem
After the `get_state()` fix above, two **oven** Fahrenheit temperature entities appeared but were locked at 0 and could not be adjusted:
- `targetTemperatureF` - Target cooking temperature in Fahrenheit (Number entity)
- `targetFoodProbeTemperatureF` - Target food probe temperature in Fahrenheit (Number entity)

These were created as writable number controls (with sliders/input boxes) but displayed min=0, max=0, making them read-only and unusable.

**Important: This issue only affects ovens. Air conditioners and other appliances with temperature unit selection are not affected.**

### Root Cause
The oven catalog incorrectly defined these entities as writable number controls with `"access": "readwrite"` and `NumberDeviceClass.TEMPERATURE`. However, **the Electrolux API only provides write capabilities for the Celsius versions** (`targetTemperatureC`, `targetFoodProbeTemperatureC`) for ovens.

**How Ovens Differ from Air Conditioners:**
- **Ovens**: No temperature unit selection. Both C and F values always reported simultaneously. API only supports writing to Celsius. Fahrenheit values are read-only conversions.
- **Air Conditioners**: Have `temperatureRepresentation` select entity to choose C or F. API supports writing to whichever unit is selected. Use climate entity platform with dynamic unit handling.

The Fahrenheit values in the API's reported state are **read-only conversions** provided for display purposes only. When the program capabilities (e.g., "TRUE_FAN") were checked, they only contained definitions for the Celsius controls:

```json
"TRUE_FAN": {
  "targetTemperatureC": {
    "min": 30.0,
    "max": 230.0,
    "step": 5.0
  },
  // ❌ No targetTemperatureF definition
}
```

When the number entity couldn't find its entity name in program capabilities, it marked itself as "not supported by program" and locked the control at min=max=0.

### Fix
Changed the catalog definitions for `targetTemperatureF` and `targetFoodProbeTemperatureF` from writable number controls to read-only sensor entities:

**Before (v3.3.8):**
```python
"targetTemperatureF": ElectroluxDevice(
    capability_info={"access": "readwrite", "type": "temperature"},  # ❌ Wrong
    device_class=NumberDeviceClass.TEMPERATURE,  # ❌ Number control
    unit=UnitOfTemperature.FAHRENHEIT,
)
```

**After (v3.3.9):**
```python
"targetTemperatureF": ElectroluxDevice(
    capability_info={"access": "read", "type": "temperature"},  # ✅ Read-only
    device_class=SensorDeviceClass.TEMPERATURE,  # ✅ Sensor
    unit=UnitOfTemperature.FAHRENHEIT,
)
```

### Result
After upgrading to v3.3.9, **oven temperature entities** are correctly categorized:

**Display/Read-Only Sensors (Correct - all 4):**
- ✅ `displayTemperatureC` - Current oven temperature (Celsius) - **Sensor**
- ✅ `displayTemperatureF` - Current oven temperature (Fahrenheit) - **Sensor**
- ✅ `displayFoodProbeTemperatureC` - Current probe temperature (Celsius) - **Sensor**
- ✅ `displayFoodProbeTemperatureF` - Current probe temperature (Fahrenheit) - **Sensor**

**Target/Control Entities (Correct - only Celsius are writable):**
- ✅ `targetTemperatureC` - Target cooking temperature (Celsius) - **Number control**
- ✅ `targetTemperatureF` - Target cooking temperature (Fahrenheit) - **Sensor** (changed to read-only)
- ✅ `targetFoodProbeTemperatureC` - Target probe temperature (Celsius) - **Number control**  
- ✅ `targetFoodProbeTemperatureF` - Target probe temperature (Fahrenheit) - **Sensor** (changed to read-only)

**For oven users who prefer working in Fahrenheit:**
1. View the Fahrenheit sensor values (all 4 Fahrenheit entities display correctly)
2. Adjust the Celsius number controls (which automatically update the Fahrenheit display values)

**Air conditioner users are not affected** - AC units continue to use the climate entity with native Fahrenheit control via the temperature unit selection.

---

## Technical Details

### Files Changed
- **[models.py](custom_components/electrolux/models.py#L218-L247)**: Fixed `get_state()` method (lines 218-247)
  - Changed return type from `dict[str, Any] | None` to `Any`
  - Removed incorrect `isinstance(result, dict)` check

- **[catalog_oven.py](custom_components/electrolux/catalog_oven.py#L203-L223)**: Fixed oven Fahrenheit target temperature entities (ovens only - AC units not affected)
  - Changed `targetTemperatureF` from number control to sensor (line 217)
  - Changed `targetFoodProbeTemperatureF` from number control to sensor (line 203)
  - Changed `capability_info["access"]` from `"readwrite"` to `"read"`
  - Changed `device_class` from `NumberDeviceClass.TEMPERATURE` to `SensorDeviceClass.TEMPERATURE`

### Type Safety
The change from a specific return type to `Any` maintains type safety because:
1. The method is only used internally within the `Appliance` class
2. Callers check for `None` explicitly: `self.get_state(catalog_key) is not None`
3. MyPy type checking validates all usage patterns remain safe
4. The method's purpose is to return any value from the reported state, so `Any` is the correct type

### Migration Notes
**Action required for oven users with Fahrenheit automations:**

After upgrading to v3.3.9, the following **oven** entities will **change type** from number controls to sensors:
- `sensor.oven_target_temperature_f` (was `number.oven_target_temperature_f`)
- `sensor.oven_target_food_probe_temperature_f` (was `number.oven_target_food_probe_temperature_f`)

**Impact for oven users:**
- Any automations or dashboards referring to the old number entities will need to be updated with the new sensor entity IDs
- The Fahrenheit values remain visible and update automatically when you adjust the Celsius controls
- If you need to control oven temperatures in Fahrenheit, adjust the corresponding Celsius number entities instead

**No action required for:**
- **Air conditioner users** - AC units are not affected; continue using the climate entity with temperature unit selection
- **Other entities** - All other missing entities will automatically appear after upgrading and restarting Home Assistant
- If you manually disabled any Fahrenheit temperature entities, you may want to re-enable them

---

## Recommendation
Users on v3.3.8 should upgrade to v3.3.9 immediately to restore missing entities. This is particularly important for oven users who rely on Fahrenheit temperature monitoring.

