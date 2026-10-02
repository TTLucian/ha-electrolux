# Release Notes v3.2.4

## 🚀 Electrolux Integration: "Stability & UX" Update and Dryer Appliance Full Support


### 🔧 CRITICAL BUG FIXES

#### ✅ Token Refresh No Longer Causes Integration Reload

**Issue:** Token refresh was triggering a full integration reload every 12 hours, causing:
- SSE disconnection  
- Task cancellation
- ~300ms service disruption
- Loss of real-time updates


**Fixed:**  
✅ Seamless token refresh with zero downtime  
✅ SSE connection remains active  
✅ **State synchronization maintained**  
✅ Tokens properly persisted across restarts  
✅ Entity states update correctly after token refresh
✅ Real-time updates work after reload  
✅ SSE establishes on initial setup AND reloads  
✅ Proper reconnection logic

### 🛠️ Core Infrastructure Improvements
- **Critical Token Refresh Race Condition Fix**: Fixed a race condition where the Electrolux SDK's ApplianceClient could call `refresh_token()` directly during 401 responses, bypassing synchronization and causing "Invalid grant" errors. The `refresh_token()` method now acquires its own lock internally, ensuring thread-safe concurrent refresh attempts.
- **Atomic Token Lifecycle Management**: Implemented a sophisticated ElectroluxTokenManager that solves common OAuth2 failures.
- **Race-Condition Protection**: Added an AsyncLock to ensure that even if multiple sensors update simultaneously, only one refresh call is made to the servers, preventing account lockouts.
- **Deterministic Expiry**: Added a safety buffer to refresh tokens before they expire, ensuring 24/7 data continuity.
- **Verified 401 Recovery**: New test suites confirm the integration gracefully handles expired credentials by attempting a silent refresh or triggering a user-friendly re-authentication flow.
- **Connectivity Resilience**: Refined the ElectroluxCoordinator to differentiate between "Real Errors" and "Network Noise."
- **Appliance Offline Handling**: Network drops now correctly mark entities as Unavailable without triggering unnecessary "Re-auth" pop-ups for the user.
- **SSE Stream Recovery**: Added logic and tests to verify that the Server-Sent Events (SSE) stream can automatically recover from disconnections.
- **Implemented Lazy Loading**: Optimized resource management that loads only required appliance data to reduce memory usage and improve startup speed.
- **Added ElectroluxTokenManager Unit Tests**: Created a comprehensive test suite (`test_token_manager_401.py`) that uses deterministic time-mocking to verify token refresh logic.
- **Verified Lock Logic**: Proved that the AsyncLock correctly prevents race conditions during token rotation.
- **Verified 401 Recovery**: Confirmed the integration correctly triggers the re-authentication flow when a token is rejected.
- **Concurrent Refresh Test**: Added `test_concurrent_sdk_refresh_calls()` to verify multiple simultaneous `refresh_token()` calls are properly serialized and don't cause race conditions.
- **Hardened Data Coordinator**: Introduced `test_coordinator_connectivity.py` to ensure the integration can survive the "messy reality" of IoT networking.
- **Appliance Offline Handling**: The coordinator now correctly identifies network drops vs. authentication failures, preventing unnecessary "Re-auth" pop-ups.
- **SSE Stream Resilience**: Verified that the Server-Sent Events (SSE) stream can initialize and recover safely.

### ✨ User Experience & UI
- **Dryer (Tumble Dryer) Support Added**: Added full support for Electrolux tumble dryers, including all standard controls and monitoring capabilities.
- **Implemented Multi-Appliance Matrix**: Added support and testing for diverse appliance types, including Ovens, Washers, Dryers, and Air Conditioners, ensuring feature updates for one don't break the others.
- **Branding & Visual Identity**: Submitted PR #9519 to the official Home Assistant Brands repository. PR was merged so the integration will feature official Electrolux Group icons and logos in the dashboard.
- **Smart Sliders**: Optimized the balance between visual slider constraints and backend validation to ensure users always know a control is restricted.

## Entity Availability Rules Implementation

This release also implements comprehensive Entity Availability Rules, refines program support handling, and addresses UI consistency issues for unsupported controls.

### Changes

#### Entity Availability Rules Implementation
- **Number Entities**: Ensured all number controls remain available in HA UI but are clamped/locked at minimum value when not supported by current program, preventing card rendering failures.
- **Program Support Logic**: Refined `_is_supported_by_program()` to only treat core program selectors as always-supported, while other entities follow program-specific constraints.

#### Bug Fixes
- **Optimistic Update State Persistence**: Fixed issue where number controls would revert their state in HA when other controls were changed. The cached value is now only cleared when an actual reported value differs, not when a property is missing from state updates.

#### Technical Improvements
- **Error Message Handling**: Maintained clamped constraints for locked sliders, accepting HA's default validation error as trade-off for UI consistency (custom error would require movable sliders).
- **Program Selector Identification**: Clarified "userSelections/programUID" as a select entity for program selection, distinct from "program" state.
- **Test Coverage**: Verified changes with existing test suite, ensuring no regressions in entity behavior.


### Known Issues
- Unsupported number controls display HA's default validation error ("expected float...") instead of custom message when attempting to set values, due to HA's service validation occurring before entity methods.

---

## 📊 Technical Details

### Understanding the Token Refresh Fix

1. **Maintains object references**: Updates the existing dict in-place, keeping all HA references valid
2. **Persists to storage**: Writes changes to `.storage/core.config_entries` for restart persistence
3. **Broadcasts updates**: Notifies all listeners that config entry changed (without reload)
4. **Type-safe**: Uses HA's official API with proper validation

### Testing Recommendations

1. **Monitor token refresh** (every 12 hours):
   - ✅ Should see: `"Config entry updated successfully - new tokens persisted (no reload)"`
   - ❌ Should NOT see: `"SSE disconnect"` or `"cleanup_tasks called"`
   - ✅ Entities remain available throughout refresh

2. **Test integration reload**:
   - Settings → Devices & Services → Electrolux → Reconfigure
   - Change any option → Submit
   - ✅ Should see: `"HA already running - starting background tasks immediately"`
   - ✅ Should see: `"Successfully started SSE listening for X appliances"`

3. **Verify state sync after token refresh**:
   - Wait for token refresh OR manually trigger refresh
   - Toggle cavity light via HA
   - ✅ HA UI should update to match appliance state
   - ✅ Select controls should show current program
   - ❌ Should NOT see empty boxes or "unavailable"

---

## 🐛 Issues Fixed

| Issue | Description | Status |
|-------|-------------|--------|
| Token Refresh Reload | Token refresh triggered full integration reload | ✅ Fixed |
| State Sync Broken | Direct data assignment broke entity state updates | ✅ Fixed |
| SSE No Reconnect | SSE never reconnected after reload | ✅ Fixed |
| Service Disruption | 300ms+ disruption every 12 hours | ✅ Fixed |
| Entities Unavailable | All entities became unavailable after token refresh | ✅ Fixed |

---

**Key Lesson:** Always use Home Assistant's official API methods. Direct manipulation of internal attributes can break implicit contracts and reference chains that aren't immediately obvious.

---

## 📝 Upgrade Instructions

1. Update to v3.2.4
2. **Restart Home Assistant** (required for code changes)
3. Reauthentication may be required after first restart if tokens are expired or invalid
3. Monitor logs for successful SSE connection
4. Wait ~12 hours for first token refresh to verify fix works
5. Verify entities remain available and responsive throughout

---

## 🙏 Credits

Special thanks to the users who:
1. Provided detailed logs revealing the token refresh reload cycle
2. Tested previous versions and reported the state synchronization failure
3. Helped identify the correct fix by describing exact symptoms
4. Provided diagnostics json files
5. Supported this integration's development so far

