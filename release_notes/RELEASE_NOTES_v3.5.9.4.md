# Release Notes v3.5.9.4

## Bug Fixes

### Air Purifier (Muju): Adjusting fan speed in Auto or Quiet mode now shows a clear error instead of silently switching modes

Previously, dragging the fan speed slider while the appliance was in Auto or Quiet
mode caused the integration to automatically send `Workmode: Manual` behind the
scenes before setting the requested speed.  This was confusing: the user never
asked to leave Auto/Quiet mode, yet the preset mode changed unexpectedly.  In some
front-end clients (including the native Lovelace fan card and HomeKit) this appeared
as an error notification or an unexpected state change.

The fix removes the silent mode-switch entirely.  When `Fanspeed` is declared
`disabled: true` by the Workmode capability triggers (Auto and Quiet modes on the
Muju), attempting to set the fan speed now raises a clear `HomeAssistantError`:

> *Fan speed cannot be adjusted in Auto mode.  Switch to Manual mode first to
> control fan speed.*

HomeKit compatibility from v3.5.8 is fully preserved: the fan entity still returns
`None` for `percentage` in Auto/Quiet mode, so the HomeKit Bridge correctly treats
speed as non-controllable and will not call `set_percentage` in the first place.

### Air Purifier (Muju): `number.fanspeed` entity now blocks commands when Fanspeed is disabled by mode

The separate `Fan speed` (`number.*_fanspeed`) entity — visible in the HA entity
list alongside the fan card — sent raw `{"Fanspeed": X}` commands directly to the
API without checking whether the current Workmode permits fan speed changes.  In
Auto or Quiet mode this command either silently reverted on the appliance side or
produced an API validation error.

A new generic helper `_is_disabled_by_trigger()` in `entity.py` walks the
appliance's capability triggers and checks whether the current reported state
activates a `disabled: true` override for the entity's attribute.  This helper is
now called at the start of `async_set_native_value` in the number entity, raising
`HomeAssistantError` when the capability is dynamically disabled:

> *'Fanspeed' cannot be adjusted in the current mode.*

The same helper is available to all entity types and will automatically protect
any future capability that uses the same trigger pattern.
