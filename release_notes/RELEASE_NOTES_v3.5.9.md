# Release Notes v3.5.9

## Bug Fixes

### Toggling a dishwasher option (ExtraPower, ExtraSilent, etc.) resets all other options

**Affected appliance types:** Dishwashers where `userSelections` options are exposed as
switches (e.g. Electrolux 911438465 / model `DW-911438465_00`).

**Symptom:** Toggling any `userSelections` boolean switch — for example turning
**Extra Power** on or off — would cause all other currently-active options to be
silently reset to `false` on the appliance.  Concretely:

- Toggle **Extra Power** ON → **Sanitize** turns off on the physical panel.
- Toggle **Extra Power** OFF → **Sanitize** turns off on the physical panel.
- The behaviour was identical regardless of which option was toggled or what the
  new state was.
- `timeToEnd` and eco scores changed as a side-effect, confirming the appliance had
  actually received and applied the command.

**Root cause — partial `userSelections` write treated as full replacement**

When a switch was toggled, the integration sent a minimal command containing only
`programUID` plus the single changed field, for example:

```json
{
  "userSelections": {
    "programUID": "ECO",
    "extraPowerOption": true
  }
}
```

This Electrolux dishwasher firmware interprets a partial `userSelections` write as a
**full replacement**: any field absent from the payload is reset to its default value
(`false` for boolean options).  So the command above effectively turned off
`sanitizeOption`, `glassCareOption`, `autoDoorOpener`, and every other option that was
not explicitly listed.

The capability document for this appliance correctly models `userSelections` as a set of
independent boolean fields (`extraPowerOption`, `extraSilentOption`, `glassCareOption`,
`sanitizeOption`, `autoDoorOpener`, …) that are individually `"access": "readwrite"`.
There is no API-level indication that sends partial writes would be destructive, making
this a firmware-level behaviour that must be worked around in the integration.

**Fix — send full `userSelections` payload on every switch toggle**

A new helper `_build_full_user_selections(changed_attr, new_value)` was added to
`entity.py`.  It:

1. Reads **all** fields currently present in the reported `userSelections` dict.
2. Filters out fields whose capability declares `"access": "read"` (read-only computed
   fields like `ecoScore`, `energyScore`, `waterScore`) to avoid API validation errors.
3. Overrides the changed field with the new value (and ensures `programUID` is always
   present).
4. Returns the merged dict as the complete `userSelections` payload.

`switch.py` now calls this helper for both legacy and DAM appliances whenever
`entity_source == "userSelections"`, so the full current option state is always
preserved on every toggle:

```json
{
  "userSelections": {
    "programUID": "ECO",
    "extraPowerOption": true,
    "sanitizeOption": true,
    "glassCareOption": false,
    "extraSilentOption": false,
    "autoDoorOpener": true,
    "oneRackOption": false,
    "zoneCleanOption": false,
    "sprayZoneOption": false,
    "xtraDryOption": false
  }
}
```

> **⚠ Testing required:** This change affects all dishwasher (and other appliance type)
> `userSelections` switch entities.  After upgrading, please verify:
> - Toggling **Extra Power**, **Sanitize**, **Glass Care**, **Extra Silent**, or **Auto
>   Door Opener** no longer resets the other options on the physical panel.
> - The `timeToEnd` and eco scores update to values consistent with only the intended
>   option change.
> - Programme changes via the select entity continue to work as before.
> - Appliances that do not use `userSelections` switches are unaffected.
> If you observe regressions, please report them with the integration log at DEBUG level.
