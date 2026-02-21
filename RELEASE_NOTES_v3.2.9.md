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
The `_is_supported_by_program()` method was looking for the current program using only `reported_state.get("program")`, which works for ovens and dishwashers but not for dryers. Dryers store the program in `userSelections/programUID` instead of a top-level `program` key. When the code couldn't find the program, it would default to assuming everything is supported, breaking program-specific locking and constraint logic.

**Example from Sample Data:**
```json
"reported": {
  "userSelections": {
    "programUID": "COTTON_PR_COTTONSECO",
    "antiCreaseValue": 30
  },
  "cyclePhase": "ANTICREASE"
}
```

The code was looking for `reported["program"]` (doesn't exist) instead of `reported["userSelections"]["programUID"]`.

**Fix:**
Updated 4 locations in `entity.py` to check multiple locations for the current program:
1. Entity initialization (`__init__`)
2. State update handler (`_handle_coordinator_update`)
3. Program support validation (`_is_supported_by_program`)
4. Program constraint lookups (`_get_program_constraint`)

Each location now checks:
- `reported_state["program"]` (ovens, dishwashers, washers)
- `reported_state["userSelections"]["programUID"]` (dryers, some washers)
- `reported_state["cyclePersonalization"]["programUID"]` (alternative location)

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
Changed the sensor implementation to use `SensorDeviceClass.DURATION` and return raw seconds:

**In `catalog_core.py`:**
- Changed `device_class=SensorDeviceClass.TIMESTAMP` to `device_class=SensorDeviceClass.DURATION`

**In `sensor.py`:**
- Changed from returning `dt_util.now() + timedelta(seconds=value)` to returning `int(value)`
- Removed unused imports (`timedelta`, `dt_util`)

**In `tests/test_sensor.py`:**
- Updated 6 test cases to expect `int` values instead of `datetime` objects

**Impact:**
The Time to End sensor now displays as an intuitive countdown timer showing hours, minutes, and seconds remaining (e.g., "3h 19m 0s"). This is:
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
