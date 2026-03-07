# Release Notes v3.4.9

## Bug Fixes

### Critical: SSE Real-Time Updates Ignored for Appliances with Nested Capabilities

Appliances that expose capabilities under a namespace (e.g. `upperOven/doorState`, `fridge/sensorTemperatureC`, `freezer/targetTemperatureC`) were not updating in real time via SSE pushes. Manually triggering a refresh showed the correct values, because the full-state poll path worked correctly.

The SSE incremental update path (`_process_incremental_update`) had two bugs when `property` contained a `/`:

1. **Duplicate detection** called `reported_state.get("fridge/sensorTemperatureC")` — a flat dictionary lookup that always returns `None` for nested state. This meant every SSE push for a nested property was treated as a change, but the next bug prevented it from being stored correctly.

2. **State write** called `update_reported_data({"fridge/sensorTemperatureC": 4.0})`. The key contained a slash but lacked the `"property"`/`"value"` envelope that triggers the nested-write branch. This caused the value to be stored as a flat key `"fridge/sensorTemperatureC"` in `reported_state` instead of `reported_state["fridge"]["sensorTemperatureC"]`. Entities read from the nested path and therefore never saw SSE values.

Fixed by:
- Using `appliance.get_state(property_path)` for the duplicate check, which already handles slash-separated paths.
- Wrapping the write as `{"property": property_path, "value": value}` so `update_reported_data` routes it through its existing nested-write logic.

**Affected appliance types (from available diagnostic samples):**

| Appliance | Affected namespaces | Impact |
|---|---|---|
| Structured Oven (SO) | `upperOven/` | **Severe** — all real-time state: door, temperatures, run time, timeToEnd, applianceState, food probe, etc. |
| Refrigerator (CR) | `fridge/`, `freezer/`, `extraCavity/`, `iceMaker/` | **Severe** — door state, temperatures, fast mode, applianceState |
| All others (WM, WD, TD, DW, OV, AC) | `networkInterface/` only | Negligible — OTA diagnostics; `command`/`startUpCommand` are blacklisted |

---

### Bug Fix: Air Purifier Fan Commands Double-Nested (Regression from v3.4.8)

The v3.4.8 fix for oven command routing introduced a regression for **air purifier fan entities**. When controlling an air purifier (turn on/off, set preset mode, set speed), the integration sent a double-nested command:

```json
{ "Workmode": { "Workmode": "Manual" } }
```

instead of the correct flat command:

```json
{ "Workmode": "Manual" }
```

This silently broke all interactive fan controls on Electrolux/AEG air purifiers (PUREA9, Muju, and similar models).

**Root cause:** The `Workmode/fan` catalog entry uses the slash notation to create a HA `fan` platform entity with `entity_source="Workmode"`. The v3.4.8 wrapping logic treated every non-empty `entity_source` as an API namespace and wrapped the command under it — but `Workmode` is a flat top-level capability, not a namespace.

**Fix:** `fan.py` `_send_command` now checks whether `attr_name` is itself a top-level capability in the appliance's capabilities dict:
- **Yes** (e.g. `Workmode`, `Fanspeed`) → send flat: `{attr_name: value}`
- **No** (e.g. `executeCommand` inside `upperOven`) → wrap: `{entity_source: {attr_name: value}}`

| Appliance | Impact |
|---|---|
| PUREA9 / Muju air purifiers | **Fixed** — turn on/off, preset modes, fan speed now work |
| Structured Oven (SO) | No change — oven namespace wrapping is still correct |
| All other appliances | No change |

---

## Files Changed

- `custom_components/electrolux/coordinator.py` — fix duplicate check and state write for nested SSE property paths
- `custom_components/electrolux/fan.py` — fix air purifier fan commands not double-wrapping flat capabilities

