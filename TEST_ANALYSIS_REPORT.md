# Test Suite Analysis Report
**Date**: February 17, 2026  
**Total Tests**: 184 tests  
**Status**: 149 PASSED (81%) | 35 FAILED (19%)

---

## Executive Summary

The test suite is **comprehensive and well-structured** with good coverage across all entity types. However, there are **35 failing tests** that need attention, falling into several categories:

### Critical Issues (Must Fix)
1. **Mock coordinator missing `_consecutive_auth_failures`** - 9 failures
2. **Entity state caching issues** - Multiple failures across entity types

### Medium Priority Issues
3. **Entity availability rules not matching recent code changes** - 4 failures
4. **Number entity behavior changes** - 10 failures
5. **Select entity cached state issues** - 3 failures

### Low Priority Issues
6. **Binary sensor logic** - 6 failures (may be test expectations vs reality)
7. **Switch entity state** - 2 failures
8. **Text entity state** - 1 failure

---

## Test Coverage by Module

### ✅ **Excellent Coverage:**
- **test_token_manager.py**: 14/14 PASSED (100%) - Token refresh, auth 401 handling, cooldowns
- **test_button.py**: 13/13 PASSED (100%) - Button press, availability, DAM vs legacy
- **test_text.py**: 20/21 PASSED (95%) - Text input entities
- **test_switch.py**: 12/14 PASSED (86%) - Switch on/off, remote control
- **test_util.py**: 2/2 PASSED (100%) - Utility functions
- **test_init.py**: 1/1 PASSED (100%) - Domain constant
- **test_api_logic.py**: 19/19 PASSED (100%) - Deep merge, string_to_boolean

### ⚠️ **Needs Attention:**
- **test_coordinator.py**: 9/12 PASSED (75%) - Missing mock attributes
- **test_coordinator_connectivity.py**: 4/10 PASSED (40%) - Mock initialization issues
- **test_entity_availability_rules.py**: 6/10 PASSED (60%) - Logic changes not reflected
- **test_number.py**: 20/30 PASSED (67%) - State caching and value logic
- **test_select.py**: 15/18 PASSED (83%) - Current option caching
- **test_binary_sensor.py**: 9/15 PASSED (60%) - Is_on logic

### ✅ **Good Coverage:**
- **test_config_flow.py**: 3/3 PASSED (100%) - Config/repair flow

---

## Detailed Failure Analysis

### Category 1: Coordinator Mock Issues (9 failures)
**Root Cause**: Mock coordinator fixture missing recent attributes

**Failing Tests:**
- `test_async_update_data_success`
- `test_async_update_data_auth_error`
- `test_async_update_data_multiple_appliances`
- `test_successful_appliance_poll_updates_state`
- `test_oven_state_processing`
- `test_washer_state_processing`
- `test_ac_state_processing`
- `test_malformed_data_*` (3 tests)

**Error**: `AttributeError: 'ElectroluxCoordinator' object has no attribute '_consecutive_auth_failures'`

**Fix Required**: Update `mock_coordinator` fixture in test files:
```python
coord._consecutive_auth_failures = 0
coord._auth_failure_threshold = 3
```

**Files to Update:**
- `tests/test_coordinator.py`
- `tests/test_coordinator_connectivity.py`

---

### Category 2: Entity State Caching Issues

#### Binary Sensor (6 failures)
**Tests Failing:**
- `test_is_on_boolean_true` - expects True, got False
- `test_is_on_string_conversion` - expects True, got False
- `test_is_on_with_invert` - expects False, got True
- `test_is_on_food_probe_insertion_state` - expects True, got False
- `test_is_on_cleaning_ended` - expects True, got False
- `test_is_on_probe_end_of_cooking` - expects True, got False

**Root Cause**: Tests may not be calling coordinator update handler to populate `_reported_state_cache`

**Pattern**: All entity types now use `_reported_state_cache` after recent performance optimizations

#### Switch (2 failures)
- `test_is_on_boolean_true` - expects True, got False
- `test_is_on_non_boolean_conversion` - expects True, got False

#### Select (3 failures)
- `test_current_option_basic` - expects 'Option 1', got ''
- `test_current_option_none_value` - expects None, got ''
- `test_current_option_unknown_value` - expects 'Unknown', got ''

#### Text (1 failure)
- `test_native_value_from_reported_state` - expects 'test value', got None

**Common Fix**: Ensure tests call `entity._handle_coordinator_update()` after setting coordinator data

---

### Category 3: Entity Availability Rules (4 failures)

**Tests Failing:**
- `test_number_entity_shows_minimum_value_when_not_supported_by_program` - expects 30, got 180
- `test_number_entity_prevents_modification_when_not_supported_by_program` - regex mismatch
- `test_food_probe_temperature_prevents_modification_when_not_supported_by_program` - regex mismatch
- `test_entities_remain_available_when_program_changes` - expects 30, got 180

**Root Cause**: Recent changes to entity availability rules (entities stay available but locked at minimum)

**Fix Required**: Update test expectations to match new behavior:
- Entities should remain available (not unavailable)
- Values should be clamped to minimum from device details
- Error messages should match new format: "not supported by current program"

---

### Category 4: Number Entity Logic (10 failures)

**Tests Failing:**
- `test_native_value_basic` - expects 75, got 50
- `test_native_value_time_conversion_start_time` - expects 30, got None
- `test_native_value_start_time_invalid` - expects None, got 1
- `test_native_value_food_probe_not_inserted` - expects 0.0, got None
- `test_native_step_program_specific` - expects 5, got 0.0
- `test_async_set_native_value_*` (5 tests) - regex pattern mismatches

**Root Cause**: 
1. State caching not being populated in tests
2. Recent changes to number entity value processing (startTime, food probe)
3. Error message format changes

**Fix Required**: 
- Call `_handle_coordinator_update()` in test setup
- Update test expectations for new number entity logic
- Update error message regex patterns

---

## Test Quality Assessment

### Strengths:
✅ **Comprehensive coverage** of all entity types  
✅ **Good parametrization** - Tests multiple scenarios per feature  
✅ **Integration tests** - Coordinator connectivity, multi-appliance  
✅ **Edge cases covered** - Invalid data, missing fields, auth failures  
✅ **Token management thoroughly tested** - 14 test cases covering refresh, cooldowns, auth  
✅ **Entity availability rules** - Dedicated test file for critical UI behavior  
✅ **DAM vs Legacy appliance handling** - Both code paths tested  

### Gaps Identified:

#### 1. **Missing SSE Streaming Tests**
- ❌ No tests for duplicate SSE event detection (just added in coordinator)
- ❌ No tests for SSE reconnection logic
- ❌ No tests for deferred update mechanism (Electrolux bug workaround)
- ❌ No tests for incremental vs bulk update paths

**Recommendation**: Add `test_sse_duplicate_detection.py` with tests for:
```python
test_incremental_update_skips_duplicate_values()
test_bulk_update_skips_when_all_values_unchanged()
test_last_seen_time_updated_even_when_duplicate()
test_deferred_update_triggered_when_time_to_end_in_range()
```

#### 2. **Missing Manual Sync Tests**
- ❌ No tests for manual sync button functionality
- ❌ No tests for 60s cooldown
- ❌ No tests for progress events (4 steps)

**Recommendation**: Add to `test_button.py`:
```python
test_manual_sync_disconnects_sse()
test_manual_sync_refreshes_coordinator()
test_manual_sync_reconnects_sse()
test_manual_sync_enforces_cooldown()
```

#### 3. **Missing Sensor Tests**
- ❌ No `test_sensor.py` file!
- ❌ timeToEnd/runningTime filtering logic not tested
- ❌ Alerts sensor not tested

**Recommendation**: Create `tests/test_sensor.py` with tests for:
```python
test_time_to_end_returns_none_when_not_running()
test_time_to_end_shows_countdown_when_running()
test_running_time_returns_none_when_stopped()
test_alerts_sensor_returns_list()
```

#### 4. **Missing Climate Tests**
- ❌ No climate entity tests at all

**Recommendation**: Verify if climate entities exist, add tests if needed

#### 5. **Missing Performance Tests**
- ❌ No tests for cache performance (_reported_state_cache, _constraint_cache, etc.)
- ❌ No tests verifying cache invalidation on program change

**Recommendation**: Add performance regression tests

---

## Immediate Action Items

### Priority 1: Fix Mock Coordinator (Blocks 9 tests)
```python
# In tests/test_coordinator.py and tests/test_coordinator_connectivity.py
# Add to mock_coordinator fixture:
coord._consecutive_auth_failures = 0
coord._auth_failure_threshold = 3
coord._last_time_to_end = {}
coord._deferred_tasks = set()
coord._deferred_tasks_by_appliance = {}
```

### Priority 2: Fix Entity State Cache Tests (Blocks 12 tests)
```python
# Pattern to add to entity test setup:
entity._handle_coordinator_update()  # Populate _reported_state_cache
```

### Priority 3: Update Entity Availability Test Expectations (4 tests)
- Update expected values to match new clamping behavior
- Update error message regex patterns
- Verify entities remain available (not unavailable)

### Priority 4: Add Missing Test Files
1. Create `tests/test_sensor.py` - Critical gap!
2. Create `tests/test_sse_duplicate_detection.py` - Recent feature
3. Add manual sync tests to `tests/test_button.py`

---

## Test Execution Summary

```
Platform: Windows (Python 3.14.0)
Test Framework: pytest 9.0.2
Execution Time: 6.10 seconds
Collection Time: 7.18 seconds

Results:
  ✅ 149 PASSED (81%)
  ❌ 35 FAILED (19%)
  ⚠️ 0 SKIPPED
  ⏭️ 0 XFAIL

Coverage by Domain:
  API Logic:           19/19 ✅
  Token Manager:       14/14 ✅
  Util:                2/2 ✅
  Config Flow:         3/3 ✅
  Button:              13/13 ✅
  Text:                20/21 ⚠️
  Switch:              12/14 ⚠️
  Select:              15/18 ⚠️
  Coordinator:         13/22 ❌
  Number:              20/30 ❌
  Binary Sensor:       9/15 ❌
  Entity Rules:        6/10 ❌
```

---

## Recommendations

### Short Term (This Sprint)
1. ✅ **Fix import error** - Changed `parsing` to `util` (DONE)
2. ⚠️ **Fix coordinator mocks** - Add missing attributes
3. ⚠️ **Fix entity state caching** - Call update handler in tests
4. ⚠️ **Update test expectations** - Match new entity availability logic

### Medium Term (Next Sprint)
5. 📝 **Create test_sensor.py** - Major gap in coverage
6. 📝 **Add SSE duplicate tests** - Test recent coordinator changes
7. 📝 **Add manual sync tests** - Verify button functionality
8. 📝 **Update number entity tests** - Match recent changes

### Long Term (Backlog)
9. 📊 **Add performance regression tests** - Verify cache effectiveness
10. 🔍 **Add integration tests** - Full flow from API to entity
11. 📈 **Increase test coverage** - Target 90%+ line coverage
12. 🎯 **Add mutation testing** - Verify test effectiveness

---

## Conclusion

The test suite is **fundamentally sound** with good coverage of critical paths. The 35 failing tests are primarily due to:

1. **Mock fixtures not updated** after coordinator changes (quick fix)
2. **Test setup issues** - Missing cache population calls (quick fix)
3. **Expected behavior changes** - Tests need update to match new logic (medium fix)

**Estimated fix time**: 2-4 hours for immediate issues, 8-16 hours for comprehensive completion

**Test quality grade**: B+ (Good foundation, needs maintenance)

**Recommendation**: Fix Priority 1 and 2 issues immediately, then add missing sensor tests before next release.
