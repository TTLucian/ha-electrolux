# Release Notes v3.2.6

## 🐛 Critical Bug Fix: Entity Updates After Polling

### Issue
After updating to v3.2.4, some users experienced all entities showing "unavailable" with restored states that never updated. This occurred when:
- SSE connection failed to establish or dropped
- Integration relied on periodic polling for updates
- After Home Assistant restart

### Root Cause Analysis

Two bugs were identified in `coordinator.py`:

#### Bug #1: Periodic Polling Not Triggering Entity Updates (CRITICAL)
**Location:** `coordinator.py:1130` in `_async_update_data()`

**Problem:**
The method was returning `self.data` directly after updating appliances in-place via `app_obj.update(status)`. Since the dict object reference remained unchanged, Home Assistant's `DataUpdateCoordinator` didn't detect a data change and never notified entities to update their states.

**Before:**
```python
async def _async_update_data(self) -> dict[str, Any]:
    # ... updates appliances in place ...
    return self.data  # Same object reference!
```

**After:**
```python
async def _async_update_data(self) -> dict[str, Any]:
    # ... updates appliances in place ...
    return dict(self.data)  # New dict creates changed reference
```

**Impact:** 
- SSE updates worked fine (they explicitly create new dict at line 609)
- Periodic polling updates silently failed to notify entities
- Entities remained "unavailable" after HA restart if SSE didn't connect
- Entities froze if SSE dropped and polling took over

#### Bug #2: `get_health_status` Method Outside Class (MINOR)
**Location:** `coordinator.py:1335`

**Problem:**
The `get_health_status()` method was defined at module level (no indentation) instead of as a class method of `ElectroluxCoordinator`, causing diagnostics to fail with:
```
'ElectroluxCoordinator' object has no attribute 'get_health_status'
```

**Fix:** Properly indented the method as part of the `ElectroluxCoordinator` class.

---

## What's Fixed

✅ **Entity states now update correctly** after periodic polling refreshes  
✅ **Entities update properly** after Home Assistant restart  
✅ **Diagnostics no longer crash** with AttributeError  
✅ **Integration remains functional** when SSE connection drops  

---

## Testing Recommendations

### Verify the Fix
1. **Restart Home Assistant** (required for code changes)
2. **Check entity states update** within 30 seconds of restart
3. **Verify diagnostics work**: Settings → Devices → Your Appliance → Download Diagnostics
4. **Test polling fallback**: 
   - Temporarily block Electrolux SSE endpoints to force polling
   - Verify entities still update every 30 seconds

### Expected Log Messages
✅ `"First data refresh completed successfully"`  
✅ `"Successfully started SSE listening for X appliances"`  
✅ Entity states show actual values, not "unavailable"  
✅ Diagnostics download successfully without errors

---

## Upgrade Instructions

1. **Update via HACS** to v3.2.6
2. **Clear Python cache** (recommended):
   ```bash
   rm -rf /config/custom_components/electrolux/__pycache__
   find /config/custom_components/electrolux -name "*.pyc" -delete
   ```
3. **Restart Home Assistant** (full restart required)
4. **Verify entities load** within 30 seconds
5. If issues persist:
   - Download diagnostics and check for errors
   - Enable debug logging: `logger: custom_components.electrolux: debug`
   - Report issue with logs

---

## Why This Happened

The bug was introduced during the v3.2.4 refactoring that improved token refresh and SSE handling. The SSE update path was tested thoroughly (creating new dict at line 609), but the periodic polling path was not exercised in testing scenarios where SSE remained connected. The bug only manifested when:
- SSE failed to connect at startup
- SSE connection dropped and polling took over
- Users with network conditions preventing SSE

---

## Credits

Special thanks to **Lukáš** for:
- Reporting the issue with detailed symptoms
- Providing comprehensive diagnostic JSON
- Patience during investigation

This bug report led to identifying a critical coordination pattern issue that would have affected any user experiencing SSE connectivity problems.

---

## For Developers

### Key Lesson
When working with Home Assistant's `DataUpdateCoordinator`:
- **Always return a new dict/object** from `_async_update_data()` if you modify data in-place
- The coordinator detects changes by comparing object references, not deep equality
- In-place mutations with same reference = no entity notifications
- Pattern: `return dict(self.data)` ensures reference changes

### Testing Checklist for Future Updates
- [ ] Test with SSE connected
- [ ] Test with SSE disabled (polling only)
- [ ] Test SSE reconnection after drop
- [ ] Test entity updates after HA restart
- [ ] Verify diagnostics don't crash
- [ ] Check entity states load within 30s
