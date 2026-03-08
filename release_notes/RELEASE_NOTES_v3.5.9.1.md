# Release Notes v3.5.9.1

## Bug Fixes

### Hotfix: toggling a dishwasher option fails with "Capability not found" after v3.5.9

**Affects:** v3.5.9 only. Reverts to the same symptom as before v3.5.9 (command rejected,
options appear to toggle back) but the root cause is different.

**Symptom:** Toggling any `userSelections` switch (Extra Power, Sanitize, Glass Care,
etc.) immediately raised `Command not accepted: Capability not found` and the toggle
snapped back. The HA log showed:

```
Error sending command: 406 — Capability not found
Command failed for extraPowerOption: error_code=COMMAND_VALIDATION_ERROR
```

**Root cause — reported state contains fields unknown to the API**

v3.5.9 fixed the partial-write problem by sending the *full* current `userSelections`
dict. However, the appliance's reported state contains several extra fields that are
**not declared in the capabilities document**:

- `oneRackOption`
- `zoneCleanOption`
- `sprayZoneOption`
- `xtraDryOption`

These fields exist in the reported state (the appliance sends them) but the API does
not accept them in a write command. Sending them causes the API to respond with
`Capability not found` and reject the entire command.

The v3.5.9 filter only stripped `"access": "read"` fields (computed scores).
It did not strip fields with **no capability entry at all**.

**Fix**

`_build_full_user_selections` now only includes a field in the command payload when:

1. A `userSelections/{field}` entry exists in the appliance's capabilities document, **and**
2. That capability is not `"access": "read"`.

`programUID` is always included unconditionally. Fields present in reported state but
absent from the capabilities document are silently dropped. The resulting payload
contains only the writable fields the API recognises:

```json
{
  "userSelections": {
    "programUID": "ECO",
    "extraPowerOption": false,
    "sanitizeOption": true,
    "glassCareOption": false,
    "extraSilentOption": false,
    "autoDoorOpener": true
  }
}
```
