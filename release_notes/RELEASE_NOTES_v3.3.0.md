# Release Notes v3.3.0

## 🔧 Bug Fixes

### Fixed Program-Dependent Entity Constraints for Dryers

**Problem:**
Continuation of v3.2.9 fix - while the program detection issue was resolved, dryer program-dependent entities (like `antiCreaseValue`, drying time controls, etc.) still failed to show correct min/max/step constraints. Controls would appear with incorrect ranges or fail to update constraint values when switching between programs.

**Root Cause:**
While v3.2.9 fixed finding the current program NAME in the reported state, the code still couldn't retrieve program-specific CAPABILITIES. The constraint lookup was hardcoded to check only `capabilities["program"]["values"]`, which doesn't exist for dryer appliances. Dryers store program capabilities under `capabilities["userSelections/programUID"]["values"]`.

**Example:**
```json
# Dryer capabilities structure:
"capabilities": {
  "userSelections/programUID": {
    "values": {
      "COTTON_PR_COTTONSECO": {
        "userSelections/antiCreaseValue": {
          "min": 30,
          "max": 120,
          "step": 30,
          "disabled": false
        }
      },
      "SHOES_PR_SHOES": {
        "userSelections/antiCreaseValue": {
          "disabled": true  // Not supported by this program
        }
      }
    }
  }
}
```

The code couldn't find these constraints because it was looking in the wrong location:
- ❌ Looking at `capabilities["program"]["values"]` (doesn't exist for dryers)
- ✅ Should check `capabilities["userSelections/programUID"]["values"]` (dryers)

**Fix:**
Created universal `_get_program_capabilities()` helper method in `entity.py` that intelligently checks multiple capability structure locations:

```python
def _get_program_capabilities(self, current_program: str) -> dict:
    """Get program-specific capabilities across different appliance structures.
    
    Checks multiple locations where program capabilities might be stored:
    - capabilities["program"]["values"] - Used by ovens, dishwashers, washers
    - capabilities["userSelections/programUID"]["values"] - Used by dryers
    - capabilities["cyclePersonalization/programUID"]["values"] - Fallback location
    """
```

Updated constraint retrieval methods:
- `_is_supported_by_program()` - Now correctly detects if entity is available for current program
- `_get_program_constraint()` - Now retrieves accurate min/max/step/default values for all appliance types

**Impact:**
- ✅ Dryer anti-crease duration shows correct range (30-120 minutes in 30-minute steps)
- ✅ Drying temperature controls display accurate min/max constraints
- ✅ Program-dependent entities correctly lock/unlock when switching programs
- ✅ All appliance types (ovens, dryers, washers, dishwashers) now supported

**Testing:**
Added comprehensive test suite (`tests/test_program_capabilities.py`) with 11 new tests using real appliance data structures to prevent regression. Tests verify constraint lookup works for both oven-style and dryer-style capability structures.

**Files Modified:**
- `custom_components/electrolux/entity.py` - Added `_get_program_capabilities()` helper (lines 687-718)
- `custom_components/electrolux/entity.py` - Updated constraint retrieval logic (lines 755-867)
- `tests/test_program_capabilities.py` - New comprehensive test file (507 lines, 11 tests)

---

### Fixed Duration Sensor Unit Definitions

**Problem:**
Duration-type sensors were inconsistent in their unit of measurement definitions. Some sensors that should use `UnitOfTime.MINUTES` or `UnitOfTime.SECONDS` had incomplete or incorrect unit specifications, potentially causing display issues in Home Assistant dashboards.

**Fix:**
Standardized all duration sensor unit definitions across appliance catalogs:

**Sensors Using MINUTES:**
- `applianceTotalWorkingTime` - Total appliance working time (diagnostic)
- `antiCreaseValue` - Anti-crease duration for dryers
- `delayTime` - Delayed start time for washers/washer-dryers

**Sensors Using SECONDS:**
- `timeToEnd` - Countdown timer for all appliances (primary)
- `totalTime` - Total cycle time for dryers
- `totalCycleTime` - Total cycle time for washers
- `startTime` - Delayed start time for ovens
- `targetDuration` - Target cooking duration for ovens
- All refrigerator vacation mode timers

**Guidelines Applied:**
- **Countdown timers** (real-time decreasing) → `SECONDS` for precision
- **Duration settings** (user-configurable periods) → `MINUTES` for user convenience
- **Total time displays** → Match the appliance's native reporting unit
- All duration sensors use appropriate `SensorDeviceClass.DURATION` or `NumberDeviceClass.DURATION`
- Users can change the default unit of measurement for any duration sensor in the entity's options according to theyr preference.

**Impact:**
- ✅ Consistent time unit display across all appliance dashboards
- ✅ Proper Home Assistant duration sensor integration
- ✅ Improved dashboard card compatibility
- ✅ Correct unit conversions in automations

**Files Modified:**
- `custom_components/electrolux/catalog_core.py` - Verified base duration sensors
- `custom_components/electrolux/catalog_oven.py` - Standardized oven time controls
- `custom_components/electrolux/catalog_dryer.py` - Standardized dryer duration entities
- `custom_components/electrolux/catalog_washer.py` - Standardized washer time controls
- `custom_components/electrolux/catalog_washer_dryer.py` - Standardized washer-dryer durations
- `custom_components/electrolux/catalog_refrigerator.py` - Verified refrigerator timers

---

## 📊 Testing

**Test Suite Status:**
- Total tests: 356 (345 existing + 11 new)
- All tests passing ✅
- New test coverage for program capability lookup across different appliance structures
- Tests now validate actual implementation rather than mocked behavior

**Test Files:**
- `tests/test_program_capabilities.py` (NEW) - Comprehensive program constraint testing
  - 5 tests for `_get_program_capabilities()` helper method
  - 3 tests for `_is_supported_by_program()` with real data
  - 3 tests for `_get_program_constraint()` with real data
  - Uses authentic oven and dryer capability structures

---

## 🔍 Technical Details

### Program Capabilities Lookup Architecture

**Before v3.3.0:**
```python
# Hardcoded to single location (failed for dryers)
program_caps = capabilities.get("program", {}).get("values", {}).get(current_program, {})
```

**After v3.3.0:**
```python
# Universal lookup checking multiple locations
def _get_program_capabilities(self, current_program: str) -> dict:
    # Try oven/dishwasher/washer location
    program_caps = capabilities.get("program", {}).get("values", {}).get(current_program, {})
    if program_caps:
        return program_caps
    
    # Try dryer location
    program_caps = capabilities.get("userSelections/programUID", {}).get("values", {}).get(current_program, {})
    if program_caps:
        return program_caps
    
    # Try fallback location
    program_caps = capabilities.get("cyclePersonalization/programUID", {}).get("values", {}).get(current_program, {})
    return program_caps  # Returns empty dict if not found (graceful fallback)
```

**Capability Structure Examples:**

**Ovens/Dishwashers/Washers:**
```json
"capabilities": {
  "program": {
    "values": {
      "CONVENTIONAL": {
        "targetTemperatureC": {
          "min": 30,
          "max": 230,
          "step": 5
        }
      }
    }
  }
}
```

**Dryers:**
```json
"capabilities": {
  "userSelections/programUID": {
    "values": {
      "COTTON_PR_COTTONSECO": {
        "userSelections/antiCreaseValue": {
          "min": 30,
          "max": 120,
          "step": 30
        }
      }
    }
  }
}
```

---

## ⚠️ Breaking Changes

None. This release is fully backward compatible.

---

## 🙏 Credits

Thanks to the community for reporting the persistent dryer constraint issues and providing detailed appliance data for testing and validation.

---

## 📝 Related Issues

- Fixes dryer program constraint detection issues reported in v3.2.9
- Resolves antiCreaseValue showing incorrect range limitations
- Addresses duration sensor unit inconsistencies across appliance types
