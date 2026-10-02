# Release Notes v3.4.7

## Bug Fixes

### Critical: Manual Sync Always Triggered Full Integration Reload

`perform_manual_sync` used `self.data.get(appliance_id, {})` to check whether an appliance had capabilities. Because `self.data` only has an `"appliances"` key, this lookup always returned `{}`, so `has_capabilities` was always `False`. Every Manual Sync button press triggered a full integration reload instead of the intended lightweight disconnect → refresh → reconnect path.

Fixed by looking up the appliance through `self.data["appliances"].get_appliance(appliance_id).data.capabilities`.

### Critical: Deferred Update Feature Permanently Disabled After 5 Uses (Memory Leak)

The done callback for deferred update tasks removed the task from `_deferred_tasks_by_appliance` but never removed it from `_deferred_tasks` (the set used for the limit check). Completed tasks accumulated in the set indefinitely. Once 5 deferred updates had ever run since HA startup, `len(self._deferred_tasks) >= DEFERRED_TASK_LIMIT` was permanently `True` and the deferred update feature silently stopped working until the next HA restart.

Fixed by adding `self._deferred_tasks.discard(t)` to `cleanup_deferred` and the `cleanup_removed_appliances` task cancellation path.

### Medium: Deprecated `asyncio.get_event_loop()` in Setup Path

Four calls to `asyncio.get_event_loop().time()` in `_setup_single_appliance` used the deprecated API (emits `DeprecationWarning` since Python 3.10, scheduled for removal). Replaced with `self.hass.loop.time()`, consistent with the rest of the coordinator.

### Medium: `asyncio.shield` Misuse in Cleanup Could Orphan Tasks

`_cleanup_appliance_tasks` used `asyncio.shield(asyncio.gather(...))` to wait for already-cancelled tasks to finish. If the surrounding coroutine was cancelled at that `await`, the inner `gather` became an orphaned background task that was never awaited, generating "Task was destroyed but it is pending!" log noise. Replaced with a try/except pattern that drains the gather before re-raising `CancelledError`.

### Medium: Duplicate Catalog Entries in `catalog_washer.py`

`"applianceState"` and `"networkInterface/otaState"` were defined in both `catalog_washer.py` and `catalog_core.py`. The washer-specific definitions silently overrode the core ones for all washer/dryer appliances. Both duplicates removed from the washer catalog; the authoritative definitions in `catalog_core.py` remain.

### Low: O(n²) Loop in `_async_update_data` Results Processing

`list(app_dict.keys())[i]` was called inside a `for i, result in enumerate(results)` loop, rebuilding the full keys list on every iteration. Replaced with a single `keys_list = list(app_dict.keys())` before the loop.

### Low: Dead `hasattr` Guard for `_last_cleanup_time`

`if not hasattr(self, "_last_cleanup_time"): self._last_cleanup_time = 0` was always False because `__init__` always initialises the attribute. Replaced with `getattr(self, "_last_cleanup_time", 0)` as a default in the comparison for robustness without the dead branch.

### Low: Dead `_appliances_cache` Attribute

`self._appliances_cache` was initialised in `__init__` and assigned in `setup_entities` but never read anywhere. The "hot path" comment was aspirational. Removed both assignments to eliminate dead state.

---

## Files Changed

- `custom_components/electrolux/coordinator.py` — all seven coordinator fixes above
- `custom_components/electrolux/catalog_washer.py` — removed `applianceState` and `networkInterface/otaState` duplicate entries
- `tests/test_coordinator_advanced.py` — updated `TestPerformManualSync` tests to use correct coordinator data structure; added `_make_sync_data` helper
- `tests/test_coordinator_coverage_gaps.py` — updated `TestPerformManualSyncGaps` tests
- `tests/test_coordinator_methods.py` — updated `TestPerformManualSync` tests
- `tests/test_coordinator.py` — removed assertion for removed `_appliances_cache` attribute
