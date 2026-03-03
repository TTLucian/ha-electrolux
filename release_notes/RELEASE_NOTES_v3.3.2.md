# Release Notes v3.3.2

## Overview
v3.3.2 is a critical bug fix release addressing four issues and adding one enhancement:
1. **CRITICAL**: Token refresh triggering unwanted integration reload causing entity loss
2. **CRITICAL**: Manual sync recovery for minimal appliances  
4. Added support for Steam Ovens (type "SO") missing from catalog mapping
5. **ENHANCEMENT**: Automatic state refresh on SSE reconnection
6. Fixed some memory leaks and race conditions
7. Updated README.md with Manual Sync button usage instructions (Use it cautiously and sparingly)

## Critical Bug Fix: Token Refresh Reload Issue

### Problem
When automatic token refresh occurred, it would trigger a full integration reload. If the API was slow or timing out during the reload, the appliance would be recreated with minimal data, causing all entities to disappear with the error: "This entity is no longer being provided by the electrolux integration."

### Root Cause
The `_last_token_update` timestamp was set AFTER calling `async_update_entry()`, but the update listener is triggered synchronously by that call. This meant the update listener saw the old timestamp and proceeded with an unnecessary reload.

### Solution
Set the `_last_token_update` timestamp BEFORE calling `async_update_entry()` so the update listener sees it immediately and skips the reload.

**Files Changed:**
- `coordinator.py` - Moved timestamp assignment before config entry update

### Impact
- Token refresh now updates credentials without triggering integration reload
- Entities remain stable during automatic token refresh
- No more entity loss due to API timeouts during token refresh

## Critical Bug Fix: Manual Sync Recovery for Minimal Appliances

### Problem
If an appliance was created with minimal data due to API timeout during setup (showing only a few catalog entities like buttons and connectivity sensor), there was no automatic recovery mechanism. The message "will populate during next 6-hour update cycle" was misleading - that logic didn't exist. Manual sync would only refresh data, not recreate missing entities.

### Root Cause
Once an appliance is created without capabilities data due to timeout, the regular update cycle only refreshes existing entity data. It doesn't detect minimal appliances and recreate missing entities.

### Solution
Enhanced manual sync to detect minimal appliances (no capabilities data) and automatically trigger a full integration reload to recreate all entities properly.

**Files Changed:**
- `coordinator.py` - Added minimal appliance detection in `perform_manual_sync()`

### Impact
- Manual sync button now recovers appliances with missing entities
- Detects minimal data (no capabilities) and triggers full reload
- Logs clear messages explaining the recovery process
- Users have a self-service recovery option without restarting HA

### Recovery Steps
If you see "This entity is no longer being provided by the electrolux integration":
1. Press the Manual Sync button on any remaining entity (like connectivity sensor)
2. The integration will detect minimal data and automatically reload
3. All entities will be recreated properly

## Bug Fix: Steam Oven Support

### Problem
Steam Ovens (appliance type "SO") were not included in the catalog mapping system, causing them to miss catalog metadata and proper entity definitions.

### Solution
Added comprehensive steam oven support by consolidating steam entities into the standard oven catalog since many standard ovens also have steam features (FULL_STEAM, HUMIDITY_HIGH/LOW programs).

**Steam-Specific Entities Added to Oven Catalog:**
- `waterTankLevel` - Detailed water level sensor (EMPTY, ALMOST_EMPTY, OK, ALMOST_FULL, FULL, UNKNOWN)
- `waterHardness` - Water hardness configuration select (SOFT, MEDIUM, HARD, STEP_4)
- `descalingReminderState` - Descaling reminder binary sensor with alert states

**Already Existing in Oven Catalog:**
- `waterTankEmpty` - Binary water tank status
- `waterTrayInsertionState` - Water tray insertion detection
- Steam programs support (FULL_STEAM, HUMIDITY_HIGH, HUMIDITY_LOW, etc.)

**Smart Entity Creation:** The integration only creates entities for capabilities that exist in the API response:
- Standard ovens without steam features won't get steam entities
- Steam ovens get all steam entities automatically
- Both OV and SO appliance types use the same unified oven catalog

**Files Changed:**
- `catalog_oven.py` - Added waterTankLevel, waterHardness, descalingReminderState
- `catalog_core.py` - Mapped "SO" type to use standard oven catalog

### Impact
- Steam Ovens (SO) now fully supported with proper entity definitions
- Standard ovens (OV) with steam features also benefit from enhanced catalog
- Simpler maintenance with unified catalog for both oven types
- Proper catalog metadata (icons, friendly names, entity categories) applied
- All oven features work correctly for both OV and SO appliance types

## Enhancement: Automatic State Refresh on SSE Reconnection

### Problem
When SSE connection experienced disruptions, the integration would reconnect but entity states remained stale until the next periodic update (up to 6 hours). Example: If oven changed from 180°C to 200°C during disconnection, entities showed 180°C until the 6-hour cycle.

### Solution
Added automatic full state refresh immediately after SSE successfully (re)connects. New `_refresh_all_appliances()` method fetches current state for all appliances concurrently.

**Files Changed:**
- `coordinator.py` - Added `_refresh_all_appliances()` and trigger in `listen_websocket()`

### Impact
- Stale data duration reduced from "up to 6 hours" to "seconds"
- Better UX after network issues, router restarts, HA restarts
- 6-hour periodic update remains as safety net
- Non-blocking: SSE stays operational even if refresh fails

## Testing
- All 360 tests passing (4 new tests added)
- Token refresh tested without triggering reload
- Manual sync enhanced with minimal appliance detection
- Temperature fallback values validated

## Breaking Changes
None

## Upgrade Notes
- After upgrading, entities will remain stable during token refresh
- Entity states will automatically synchronize after SSE reconnection
- If you have missing entities, use Manual Sync button to recover them
- Temperature controls will show correct maximum values
- No configuration changes required
