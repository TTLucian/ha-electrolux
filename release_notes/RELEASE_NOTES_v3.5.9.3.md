# Release Notes v3.5.9.3

## Bug Fixes

### Oven: fPPN push-notification entities no longer leak through as dead sensors

`fPPN_OVWaterTankEmpty` and similar fPPN entities whose name carries an
appliance-type prefix (e.g. `OV`, `DW`) were not being correctly matched against
their base entity counterpart. The deduplication filter stripped the `fPPN_OV` part
but the remaining string (`watertankempty`) still didn't match the two-character
prefix that the API inserts (`ovwatertankempty` vs `watertankempty`).

The fix now tries stripping 2-, 3-, and 4-character appliance-type prefixes from the
left of the base attribute name before comparing, so `fPPN_OVWaterTankEmpty` is
correctly suppressed when `waterTankEmpty` already exists as a binary sensor.

### `hideExecuteCommand` and `keyModel` no longer appear as HA sensors

Both attributes are internal API constants with no user-facing meaning:

- `hideExecuteCommand` — a trigger-routing flag that gates the visibility of the
  `executeCommand` button via capability triggers; its value is always `0` or `1`.
- `keyModel` — a hardware identity string (e.g. `PUX_AEG_AP_PS2`); constant across
  the lifetime of an appliance.

Both are now blocked by `ATTRIBUTES_BLACKLIST` and will not create HA entities on
any appliance type.

### `applianceState` and `connectivityState` no longer registered twice on startup

Both attributes appear in `STATIC_ATTRIBUTES`, in the base catalog **and** in the
appliance's API capabilities — causing the static loop to register them first,
followed by the catalog loop and the capabilities loop, triggering two
"Skipping duplicate entity" debug log messages on every HA restart.

The static attributes loop now skips any attribute that is already covered by the
catalog or by the appliance's own capability list. The deduplication safety-net at
the end of model setup is still present but is no longer triggered for these
attributes.

### Air Purifier (Muju): Work Mode select showed dict-valued options such as `{'Workmode': 'PowerOff'}`

`_send_command` in `fan.py` was calling `_apply_optimistic_update` with
`entity_source="Workmode"` (the fan entity's catalog key is `Workmode/fan`).
`_apply_optimistic_update` interprets the `entity_source` as a nesting level and,
finding that `reported["Workmode"]` was a plain string, replaced it with an empty
dict before writing the new value into it.  The result was that
`reported["Workmode"]` became `{"Workmode": "PowerOff"}` after a Workmode command,
and `{"Workmode": "PowerOff", "Fanspeed": 3}` after a speed command.  The Work
Mode *select* entity then read that dict back, formatted it with `str()`, and added
it to the options list — making it appear as a selectable (but broken) option.
Choosing it sent the literal string `"{'Workmode': 'PowerOff'}"` to the API,
returning a 406 error.

The fix removes the generic `_apply_optimistic_update` call from `_send_command`
and replaces it with two targeted helpers, `_apply_workmode_state` and
`_apply_fanspeed_state`, that write directly to the correct top-level keys in
`reported` without any nesting side-effects.

### Air Purifier (Muju): Preset Mode did not reflect the selected mode until the next SSE update

After sending a Workmode command (Auto / Manual / Quiet) the fan entity performed
no optimistic state update, so the `preset_mode` property kept returning the old
value until the server's SSE event arrived.  The new `_apply_workmode_state` helper
is now called immediately after the API command succeeds, updating `reported` and
calling `async_write_ha_state()` so the UI reflects the change instantly.

### Hardening: `_apply_triggered_updates` skips non-scalar trigger defaults

Trigger actions in capability metadata occasionally carry `dict` or `list` values
for property defaults (e.g. nested constraint objects).  Writing such a value
directly into `reported` would corrupt the state in the same way as the bug above.
`_apply_triggered_updates` now skips any triggered default that is not a scalar
(string, number, bool) and logs a debug message instead.
