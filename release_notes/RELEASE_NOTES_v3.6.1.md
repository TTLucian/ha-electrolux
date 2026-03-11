# Release Notes v3.6.1

## Bug Fixes

### Air Purifier: Fan speed slider no longer causes an error popup when switching modes via HomeKit or the Lovelace card

**Symptom:** After switching to **Auto** or **Quiet** mode, an error notification
briefly appeared in the HA frontend / companion app:

> *Fan speed cannot be adjusted in Auto mode. Switch to Manual mode first to
> control fan speed.*

This happened because the Lovelace fan card (and the HomeKit Bridge) issues a
`fan.set_percentage` call immediately after a preset mode change to keep its
internal model consistent — even though the integration had already hidden the
speed slider via dynamic `supported_features`.  The race window is typically 1–2
seconds while the frontend re-renders.

**Fix:** `async_set_percentage` no longer raises `HomeAssistantError` when
`Fanspeed` is disabled by the current Workmode.  It now logs a `WARNING` and
returns silently.  The mode lock is already correctly enforced: the slider is
hidden, and the appliance will not receive any Fanspeed command.

### Air Purifier: `async_turn_on` with both `preset_mode` and `percentage` no longer bypasses the Fanspeed mode lock

**Symptom:** Calling `fan.turn_on(preset_mode="Auto", percentage=50)` (e.g. from
an automation) caused the appliance to immediately revert from **Auto** to
**Manual**.

**Root cause:** `async_turn_on` sent the Workmode command correctly but then
unconditionally called `_set_percentage`, bypassing the `_is_fanspeed_disabled()`
guard.  The appliance firmware treats any `Fanspeed` command as an implicit
request for Manual speed control and reverts Workmode accordingly.

**Fix:** After applying the Workmode command, `async_turn_on` re-checks
`_is_fanspeed_disabled()` using the optimistically-updated state.  If the new
mode disables Fanspeed (Auto, Quiet), the `percentage` argument is silently
ignored — the caller explicitly chose a mode that does not support manual speed
control.

---

## SSE Health Monitor Removed

### Background

Version 3.6.0 introduced a background `_monitor_sse_health` task designed to
detect a scenario where the Electrolux SDK was believed to be stuck retrying a
stale livestream URL indefinitely.  The monitor checked `_last_sse_connected`
every 60 seconds and forced a full SSE restart if no successful connection had
been recorded within 5 minutes.

### Problem discovered by further testing

Further testing revealed that the monitor's core assumption was incorrect:

- **The livestream URL does not expire.**  The Electrolux SDK developers confirmed
  that `get_livestream_config()` returns a stable URL — retrying the same URL
  with a valid token always works.
- **`_last_sse_connected` was only updated on HTTP connection open**, never on
  SSE data arrival.  An idle appliance (e.g. an oven in READY_TO_START state)
  produces zero SSE events.  After the initial connection callback fired (~26 s
  after connect), `_last_sse_connected` never advanced — so the monitor would
  declare the stream stale and force a reconnect every ~6 minutes **even on a
  perfectly healthy, silent stream**.  On an always-busy appliance this is
  harmless, but on quiet appliances it generates a continuous stream of
  unnecessary reconnects.

### Fix

The `_monitor_sse_health` task and all supporting infrastructure have been
removed:

- `_monitor_sse_health()` method removed from `coordinator.py`
- `_on_sse_connected()` callback removed (its only purpose was updating
  `_last_sse_connected`)
- `_sse_monitor_task` and `_last_sse_connected` fields removed
- `SSE_STALE_THRESHOLD_SECONDS` and `SSE_HEALTH_CHECK_INTERVAL` constants removed
- Task creation / cancellation in `__init__.py` removed

The SDK's own retry loop (10 s interval) handles transient disconnections.  The
existing `renew_websocket` task handles scheduled periodic reconnection.  No
additional health monitoring is needed.
