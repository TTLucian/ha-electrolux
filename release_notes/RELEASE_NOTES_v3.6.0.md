# Release Notes v3.6.0

## Bug Fixes

### Air Purifier (Muju): Fan speed slider now hidden in Auto / Quiet mode instead of showing an error popup

In v3.5.9.4, dragging the fan speed slider while in Auto or Quiet mode raised a
visible error notification in the HA frontend:

> *Fan speed cannot be adjusted in Auto mode. Switch to Manual mode first to
> control fan speed.*

While the underlying logic was correct (speed cannot be changed in those modes),
showing an error popup is poor UX. The standard Home Assistant pattern is to
**hide the control entirely** when it is not applicable to the current state.

The `supported_features` property of the fan entity is now dynamic: when
`_is_fanspeed_disabled()` returns True (i.e. the appliance's Workmode capability
declares `Fanspeed: disabled: true` for the current mode), `FanEntityFeature.SET_SPEED`
is removed from the feature flags at runtime. Home Assistant reacts by hiding the
speed slider in the fan card completely — no slider, no error, no confusion.

The `HomeAssistantError` in `async_set_percentage` is retained as a safety net for
automations or scripts that attempt to set fan speed programmatically while the mode
lock is active.

### Air Purifier (Muju): `number.fanspeed` slider greys out in Auto / Quiet mode

The `Fan speed` number entity (`number.*_fanspeed`) now uses the standard HA
min=max locking pattern when `_is_disabled_by_trigger()` is True: both
`native_min_value` and `native_max_value` return the same locked value, causing
the slider to render as greyed-out and non-interactive — consistent with how
program-locked temperature controls behave elsewhere in the integration.

---

## SSE Stale-Session Recovery

### Problem
The Electrolux SDK fetches the SSE livestream URL **once** per connection attempt, then loops over the same URL indefinitely. If that URL becomes stale (e.g. the regional SSE server stops accepting it) the SDK's internal retry loop keeps failing silently every 10 seconds, producing:

```
WARNING: SSE connection object closed
ERROR:   SSE connection error: SSE response stream closed unexpectedly
```

…without ever logging `Connected to SSE stream`. This could cause real-time appliance updates to stop working for 60+ minutes (until the next scheduled 6-hour SSE renewal was triggered).

### Fix
A lightweight **SSE health monitor task** now runs in the background alongside the existing renewal task.

- Every 60 seconds it checks how long ago the last successful SSE connection was opened.
- If more than **5 minutes** have elapsed without a successful connection, it logs a `WARNING`, immediately cancels the stale SSE task, and starts a fresh one (which re-fetches the livestream URL from the server).
- The monitor resets its own liveness timestamp when it triggers, preventing cascading back-to-back restarts.
- The monitor is created and cancelled together with the other background tasks, honouring the HA entry lifecycle.

**Worst-case recovery time** drops from ~72 minutes → **≤ 6 minutes** (one health-check interval beyond the 5-minute threshold).

### Technical details
- `api_client.py`: `watch_for_appliance_state_updates` gains an optional `on_connected` callback forwarded to the SDK's `start_event_stream(do_on_livestream_opening_list=...)`.
- `coordinator.py`: new `_on_sse_connected()` callback (updates `_last_sse_connected` timestamp), `_monitor_sse_health()` task with constants `SSE_STALE_THRESHOLD_SECONDS = 300` and `SSE_HEALTH_CHECK_INTERVAL = 60`.
- `__init__.py`: monitor task created and cleaned up in `start_background_tasks` / `cleanup_tasks`.
