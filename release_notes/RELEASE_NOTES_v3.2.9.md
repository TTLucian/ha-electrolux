# Release Notes v3.2.9

## 🔧 Bug Fixes

### Fixed Entities Disappearing When Appliance Unplugged or Offline

**Problem:**
When users unplugged their appliances for energy saving (e.g., overnight), all control entities would permanently disappear from Home Assistant. Cards would fail to render with "Entity not available: number.dryer_anti_crease_duration" errors, and automations would stop working. The entities only came back after restarting Home Assistant.

**Root Cause:**
The periodic cleanup mechanism in `cleanup_removed_appliances()` was incorrectly removing any appliance not present in the API appliance list, without checking if it was simply disconnected/offline versus actually deleted. When an appliance was unplugged, it would be removed from the API list, triggering the cleanup to permanently delete all its entities.

**Fix:**
Enhanced the cleanup mechanism to check `connectivityState` before removing appliances. Now only appliances that are truly deleted (not in API list AND not just disconnected) are removed. Offline/disconnected appliances are preserved with their entities intact, showing their last known state.

**Technical Details:**
- Modified `coordinator.py` cleanup logic to check `connectivityState` field
- Appliances with `connectivityState: "disconnected"` are now preserved
- Only appliances that are both missing from API AND not in disconnected state are removed
- This allows users to safely unplug appliances without losing entities

**Impact:**
Users can now unplug appliances for energy saving without losing entities or requiring HA restart. Entities remain available showing last known state, and automations continue to work. Cards render correctly even when appliances are offline.

---

### Fixed Program-Dependent Entities Not Working Correctly for Dryers

**Problem:**
For dryer appliances, program-dependent entities (like `antiCreaseValue`, temperature controls, etc.) would show as "unsupported" or fail to lock/unlock correctly when switching between programs. Controls that should be locked on certain programs remained editable, and constraints (min/max/step) wouldn't update when changing programs.

**Root Cause:**
Two related bugs affected dryer program detection:

1. **Program Detection Bug:** The `_is_supported_by_program()` method was looking for the current program using only `reported_state.get("program")`, which works for ovens and dishwashers but not for dryers. Dryers store the program in `userSelections/programUID` instead of a top-level `program` key.

2. **Program Capabilities Lookup Bug:** The code that retrieves program-specific capabilities was hardcoded to look only at `capabilities["program"]["values"]`, but dryers store their program capabilities under `capabilities["userSelections/programUID"]["values"]`. This caused the code to never find program-specific constraints or disabled states for dryer entities.

**Example from Sample Data:**
```json
# Reported state (where program is stored):
"reported": {
  "userSelections": {
    "programUID": "COTTON_PR_COTTONSECO",
    "antiCreaseValue": 30
  }
}

# Capabilities (where program constraints are stored):
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
      }
    }
  }
}
```

The code was looking in the wrong locations:
- ❌ Looking for `reported["program"]` (doesn't exist for dryers)
- ❌ Looking for `capabilities["program"]["values"]` (doesn't exist for dryers)

**Fix:**
1. **Program Detection:** Updated 4 locations in `entity.py` to check multiple locations for the current program:
   - Entity initialization (`__init__`)
   - State update handler (`_handle_coordinator_update`)
   - Program support validation (`_is_supported_by_program`)
   - Program constraint lookups (`_get_program_constraint`)

2. **Program Capabilities Lookup:** Created new helper method `_get_program_capabilities()` that checks multiple capability locations:
   - `capabilities["program"]["values"][program_name]` (ovens, dishwashers, washers)
   - `capabilities["userSelections/programUID"]["values"][program_name]` (dryers)
   - `capabilities["cyclePersonalization/programUID"]["values"][program_name]` (fallback)

**Impact:**
- ✅ Program-dependent entity locking now works correctly for all appliance types
- ✅ Entities correctly show as available/unavailable based on actual program
- ✅ Constraints (min/max/step) update properly when switching programs
- ✅ Cache invalidation works when changing between programs
- ✅ Controls lock at appropriate values when program doesn't support them

**Examples:**
- `antiCreaseValue` correctly locks/unlocks based on program (available for COTTON, unavailable for SHOES)
- Temperature controls lock at program defaults (e.g., DEFROST locks at 40°C)
- Drying time constraints update based on program selection

---

### Fixed Time to End Sensor Showing Absolute Time Instead of Countdown

**Problem:**
The `sensor.time_to_end` entity was displaying as an absolute timestamp (e.g., "Feb 21, 3:30 PM") instead of showing a countdown duration (e.g., "3h 19m 0s"). This made it difficult to quickly see how much time remained in a cycle, and the timestamp format was confusing for users in different timezones or when viewing historical data.

**Root Cause:**
The sensor was configured with `SensorDeviceClass.TIMESTAMP` and the value was being converted to a datetime object by adding the remaining seconds to the current time:
```python
return dt_util.now() + timedelta(seconds=value)  # Returns datetime
```

This caused Home Assistant to render it as an absolute timestamp rather than a duration.

**Fix:**
Changed the sensor implementation to use `SensorDeviceClass.DURATION` with `UnitOfTime.SECONDS`:

**In `catalog_core.py`:**
- Changed `device_class=SensorDeviceClass.TIMESTAMP` to `device_class=SensorDeviceClass.DURATION`
- Changed `unit=None` to `unit=UnitOfTime.SECONDS` to enable proper duration formatting

**In `sensor.py`:**
- Changed from returning `dt_util.now() + timedelta(seconds=value)` to returning `int(value)`
- Removed unused imports (`timedelta`, `dt_util`)

**In `tests/test_sensor.py`:**
- Updated 6 test cases to expect `int` values instead of `datetime` objects

**Impact:**
The Time to End sensor now displays as an intuitive countdown timer in `hh:mm:ss` format (e.g., "03:19:00" for 3 hours 19 minutes). This is:
- ✅ More intuitive for users to understand at a glance
- ✅ Consistent with how other duration values are displayed
- ✅ Easier to use in automations and templates
- ✅ Not affected by timezone or locale settings

---

## 🎯 Technical Improvements

### Enhanced Cross-Appliance Type Compatibility

Improved the entity framework to handle different appliance types (ovens, dryers, washers, dishwashers) that store program information in different locations. This ensures consistent behavior for program-dependent features across all appliance types.

**Benefits:**
- Single codebase handles all appliance variations
- More reliable program detection and entity availability
- Consistent user experience across different appliance types
- Future-proof for additional appliance types

---

## 📊 Testing

All 345 tests passing:
- Entity creation and initialization
- Program detection for multiple appliance types
- Constraint lookups and caching
- State update and cache invalidation
- Appliance cleanup and removal logic

---

## 🙏 Credits

Special thanks to our users who reported these issues and provided detailed logs and sample data that made debugging possible. Your patience and detailed bug reports are invaluable!

---

## 📝 Upgrade Notes

This release requires no configuration changes. Simply update the integration and restart Home Assistant. Existing entities will continue to work, and the fixes will automatically apply.
