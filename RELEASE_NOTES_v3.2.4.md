# Release Notes v3.2.4

## 🚀 Electrolux Integration: "Stability & UX" Update

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
- **Implemented Multi-Appliance Matrix**: Added support and testing for diverse appliance types, including Ovens, Washers, and Air Conditioners, ensuring feature updates for one don't break the others.
- **Branding & Visual Identity**: Submitted PR #9519 to the official Home Assistant Brands repository. Once merged, the integration will feature official Electrolux Group icons and logos in the dashboard.
- **Custom Error Messages**: Moving away from generic "Out of range" errors to context-aware "Toast" notifications (e.g., "This setting is not supported in the current program").
- **Smart Sliders**: Optimized the balance between visual slider constraints and backend validation to ensure users always know why a control is restricted.

## Entity Availability Rules Implementation

This release also implements comprehensive Entity Availability Rules, refines program support handling, and addresses UI consistency issues for unsupported controls.

### Changes

#### Entity Availability Rules Implementation
- **Number Entities**: Ensured all number controls remain available in HA UI but are clamped/locked at minimum value when not supported by current program, preventing card rendering failures.
- **Program Support Logic**: Refined `_is_supported_by_program()` to only treat core program selectors as always-supported, while other entities follow program-specific constraints.

#### Bug Fixes
- **Optimistic Update State Persistence**: Fixed issue where number controls (particularly `targetFoodProbeTemperatureC`) would revert their state in HA when other controls were changed. The cached value is now only cleared when an actual reported value differs, not when a property is missing from state updates.


#### Technical Improvements
- **Error Message Handling**: Maintained clamped constraints for locked sliders, accepting HA's default validation error as trade-off for UI consistency (custom error would require movable sliders).
- **Program Selector Identification**: Clarified "userSelections/programUID" as a select entity for program selection, distinct from "program" state.
- **Test Coverage**: Verified changes with existing test suite, ensuring no regressions in entity behavior.

#### Code Changes
- `custom_components/electrolux/number.py`: Added targetFoodProbeTemperatureC to clamping logic, maintained min/max clamping for unsupported controls.
- `custom_components/electrolux/entity.py`: Updated global entities list in `_is_supported_by_program()` to only include program selectors.

### Known Issues
- Unsupported number controls display HA's default validation error ("expected float...") instead of custom message when attempting to set values, due to HA's service validation occurring before entity methods.