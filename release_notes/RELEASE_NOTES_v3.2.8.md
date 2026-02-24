# Release Notes v3.2.8

## 🔧 Bug Fixes

### Fixed Appliances Lost Due to Transient Network Errors During Startup

**Problem:**
If a network error occurred while fetching appliance data during Home Assistant startup (e.g., DNS resolution delay, momentary network loss), the appliance would be permanently lost until HA restart. This affected users with slower networks or during HA startup when network services might not be fully available.

**Root Cause:**
When `get_appliances_info` or `get_appliance_state` failed during initial setup, the setup process would abort completely for that appliance, leaving it permanently unavailable even after the network recovered.

**Fix:**
Implemented resilient appliance setup that creates a minimal appliance entry when network errors occur during startup. The appliance will automatically be populated with full data during the next update cycle (within 6 hours). This ensures appliances are not permanently lost due to transient startup issues.

**Impact:**
Appliances survive network hiccups during startup and recover automatically. Users no longer need to restart HA when temporary network issues occur during startup.

---

### Fixed Schema Validation Errors for Locked Number Controls

**Problem:**
Number controls like `target_food_probe_temperature_c` and `target_temperature_c` displayed schema validation errors ("expected float for dictionary value @ data['value']") when locked at their minimum values by certain oven programs (e.g., DEFROST, DOUGH_PROVING).

**Root Cause:**
- The value `0` was being treated as falsy in Python checks (`if not value:`), causing the entity to return `None` instead of `0`
- Step constraints could be set to `0`, which Home Assistant schema validation rejects

**Fix:**
- Changed value validation to explicit None checks (`if value is None:`)
- Ensured step constraints never return `0` (minimum value of `1.0`)
- Locked controls now properly display their locked values with correct min/max/step constraints

**Impact:**
Locked number controls work correctly without schema validation errors. Controls remain available but properly disabled when locked by program constraints.

---

### Fixed UI "Snap Back" After Control Changes

**Problem:**
After changing controls (switches, numbers, selects, climate), the UI would briefly snap back to the previous value, then update 1-2 seconds later when the SSE update arrived. This caused confusion and "appliance already in desired state" errors when users tried to toggle controls again thinking the command didn't work.

**Root Cause:**
Entities were not updating their local state after successfully sending commands to the API, relying solely on SSE (Server-Sent Events) updates which arrive with a 1-2 second delay.

**Fix:**
Implemented optimistic state updates for all command-based entity platforms:
- **Switch entities** (cavity light, etc.)
- **Number entities** (temperature, duration controls)
- **Select entities** (program selection)
- **Climate entities** (HVAC mode, temperature)

Controls now update immediately after command success while SSE updates continue to provide confirmation and correction if needed.

**Impact:**
Controls respond instantly to user input with no visual "snap back" behavior. The UI stays in sync with command state, preventing duplicate command attempts.

---

### Fixed Select Entity Case Sensitivity Bug

**Problem:**
Program selection showed validation errors in logs: "value Drying does not exist in the list" followed by "value DRYING does not exist in the list", causing the options list to become corrupted.

**Root Cause:**
Optimistic update was storing the UI-friendly value ("Drying") instead of the API format value ("DRYING"), causing a mismatch when SSE sent the actual API value.

**Fix:**
Changed optimistic update to store `formatted_value` (API format) instead of `option` (UI format), ensuring consistency with SSE updates.

**Impact:**
Select entities work correctly without validation errors or list corruption.

---

## 🎯 Code Quality & Performance Improvements

### Optimized Code Architecture

**Improvement: Eliminated Duplicate Code**

Extracted repeated optimistic update pattern into a reusable base class method (`_apply_optimistic_update()` in `entity.py`). This consolidates 80+ lines of duplicated code across 4 entity platforms (number, switch, select, climate) into a single, maintainable implementation.

**Benefits:**
- Easier maintenance and bug fixes
- Consistent behavior across all entity types
- Reduced code duplication by ~70 lines

---

### Fixed Token Update Race Condition

**Problem:**
Token refresh timestamp was set before `async_update_entry()` completed. In rare cases where user settings changed during token refresh, the update listener would skip the reload due to the timestamp, causing settings to not be applied.

**Fix:**
Moved timestamp assignment to after `async_update_entry()` succeeds, ensuring the timestamp is only set when the config entry is fully updated.

**Impact:**
Eliminated theoretical race condition that could prevent user settings from being applied during token refresh.

---

### Improved Resource Cleanup

**Enhancement: Better Task Cancellation Pattern**

Improved task cleanup in `_setup_single_appliance()` by:
- Extracting cleanup logic into dedicated `_cleanup_appliance_tasks()` method
- Using `asyncio.shield()` to ensure cleanup completes even if interrupted
- Better error handling during task cancellation

**Benefits:**
- More robust task cleanup during appliance setup failures
- Reduced risk of orphaned tasks
- Clearer code organization

---

### Reduced Appliance Cleanup Interval

**Change:**
Reduced appliance cleanup check interval from 24 hours to 1 hour.

**Benefit:**
Removed appliances from user accounts now disappear from Home Assistant within 1 hour instead of 24 hours, improving user experience.

---

### Performance Optimizations

**SSE Hot Path Optimization**
- Eliminated unnecessary dictionary copies on every SSE update (3 locations)
- Cached appliances reference to avoid repeated dictionary lookups
- Benefit: Reduced CPU and memory overhead on the critical SSE message processing path

**Debug Logging Optimization**  
- Converted 7 debug logs from f-strings to lazy % formatting
- Benefit: String formatting only occurs when debug logging is enabled, improving performance for production users (INFO/WARNING levels)

**Deferred Task Monitoring**
- Added debug logging when deferred task limit is reached
- Benefit: Visibility into whether the limit (5 concurrent tasks) needs adjustment for multi-appliance households

---

## 📊 Technical Summary

- **Bug Fixes:** 4 (transient network errors, schema validation, UI snap back, select case sensitivity)
- **Code Reduction:** ~70 lines of duplicate code eliminated
- **Race Conditions Fixed:** 1 (token update timestamp)
- **Performance Improvements:** Faster appliance cleanup (1h vs 24h), optimized SSE processing
- **Breaking Changes:** None
- **Test Coverage:** All 345 tests passing

---

## 📦 Release Information

**Version:** 3.2.8  
**Release Date:** February 20, 2026  
**Minimum Home Assistant Version:** 2024.1.0  
**Focus:** Bug fixes, code quality, maintainability, edge case fixes

All 345 integration tests passing ✅
