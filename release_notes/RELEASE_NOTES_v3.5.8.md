# Release Notes v3.5.8

## Bug Fixes

### Air purifier fan reverts from Auto to Manual mode when controlled via HomeKit

**Affected appliance types:** Air purifiers with a `Workmode` capability that uses
`triggers` to mark `Fanspeed` as `disabled: true` for Auto, Quiet, and PowerOff modes
(e.g. Muju / 956006959323006505087076).

**Symptom:** Switching the fan to **Auto** mode in Home Assistant or via the HomeKit
Bridge caused the appliance to immediately revert to **Manual** mode.  The mode flip
happened within seconds of the switch, so the entity toggled back and forth visibly in
the UI and physical appliance.

**Root cause — HomeKit Bridge reads percentage and then re-applies it**

When you switch to Auto mode the integration correctly sends `{"Workmode": "Auto"}` to
the appliance.  However, the HomeKit Bridge then reads the `percentage` property (which
still reported a speed value such as 20 %) and, to keep its internal model consistent,
immediately calls `set_percentage(20)`.  The integration translated that into
`{"Fanspeed": 1}`.

The Muju appliance firmware interprets a `Fanspeed` command as implicit confirmation that
the user wants manual speed control; it therefore reverts `Workmode` to `Manual`.  The
appliance capability document encodes this behaviour via `Workmode` triggers:

```json
{
  "Workmode": {
    "triggers": [
      {
        "condition": { "operator": "eq", "operand_1": "value", "operand_2": "Auto" },
        "action":    { "Fanspeed": { "disabled": true } }
      },
      {
        "condition": { "operator": "eq", "operand_1": "value", "operand_2": "Quiet" },
        "action":    { "Fanspeed": { "disabled": true } }
      }
    ]
  }
}
```

The integration was not reading these triggers, so it did not know that `Fanspeed` was
off-limits in Auto/Quiet mode.

**Fix — three-level guard in `fan.py`**

1. **`_is_fanspeed_disabled()` helper** — inspects the `Workmode` capability's `triggers`
   list for the current mode.  Returns `True` when any trigger marks `Fanspeed` as
   `disabled: true` for the current `Workmode` value.

2. **`percentage` returns `None` when disabled** — when `_is_fanspeed_disabled()` is
   `True` the `percentage` property returns `None` instead of the raw speed value.
   `None` tells Home Assistant (and the HomeKit Bridge) that speed is not
   user-controllable in the current mode, preventing the bridge from issuing a
   `set_percentage` call at all.

3. **`async_set_percentage` switches to Manual first** — if a `set_percentage` call does
   arrive while `Fanspeed` is disabled (e.g. from a UI slider or a non-HomeKit
   client), the integration now switches `Workmode` to `Manual` before sending the
   `Fanspeed` command.  This is semantically correct: the user is explicitly requesting
   speed control, so switching to Manual is the right behaviour.

> **⚠ Testing required:** This change affects air purifiers and any other fan entities
> where the appliance's capability document uses `Workmode` triggers to disable `Fanspeed`
> in certain modes.  After upgrading, please verify:
> - Switching to **Auto** (or **Quiet**) mode stays in that mode — it no longer reverts
>   to Manual.
> - Adjusting speed from the HA UI or a shortcut while in Auto mode switches the
>   appliance to Manual and then applies the requested speed (expected behaviour).
> - Manual mode speed control continues to work as before.
> - Appliances without `triggers` in their `Workmode` capability are unaffected.
> If you observe regressions, please report them with the integration log at DEBUG level.
