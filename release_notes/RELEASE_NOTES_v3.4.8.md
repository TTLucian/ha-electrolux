# Release Notes v3.4.8

## Bug Fixes

### Critical: Commands Fail with "Capability Not Found" on Appliances with Nested Capabilities

Appliances that expose their capabilities under a namespace (e.g. ovens with an `upperOven/` prefix) had all write commands silently broken. When the integration discovered a capability like `upperOven/executeCommand`, it correctly stored `entity_source = "upperOven"` and `entity_attr = "executeCommand"`. However, the command-sending logic in `button.py`, `fan.py`, `text.py`, and `climate.py` ignored `entity_source` for legacy (non-DAM) appliances and always sent a flat `{"executeCommand": "START"}` payload. The API rejected this with `COMMAND_VALIDATION_ERROR: Capability not found` because `executeCommand` is not a top-level capability — it must be nested as `{"upperOven": {"executeCommand": "START"}}`.

The other platforms (`switch.py`, `select.py`, `number.py`) already had the correct `entity_source`-aware logic. Fixed all four affected platforms to match.

---

## Files Changed

- `custom_components/electrolux/button.py` — respect `entity_source` in legacy-appliance command path
- `custom_components/electrolux/fan.py` — respect `entity_source` in legacy-appliance command path
- `custom_components/electrolux/text.py` — respect `entity_source` in legacy-appliance command path
- `custom_components/electrolux/climate.py` — respect `entity_source` in legacy-appliance command path
