# Release Notes v3.5.7

## Bug Fixes

### Ghost "Child lock" (and other control) entities after a capabilities-fallback startup

**Symptom:** After upgrading or restarting Home Assistant, a switch entity named
**"Child lock"** (or another control entity) appeared on a device that should not have one.
The entity was immediately marked *"This entity is no longer provided by the integration"*
and could not be used.

**Root cause — capabilities fallback mode**

Every time the integration starts it fetches the *capabilities* document for each
appliance from the Electrolux API. This document is the authoritative list of what a
specific physical device actually supports (e.g. `uiLockMode`, `targetTemperatureC`,
`program`, …).

Fetching the capabilities document can fail for several reasons:

- The API is temporarily unavailable or returns a timeout (the capabilities endpoint is
  separate from the appliance-list endpoint and can fail independently).
- Home Assistant starts before the network is fully up.
- A transient DNS or TLS error occurs on first boot.

When the fetch fails, the integration enters **fallback mode**: rather than refusing to
create any entities, it creates them from the built-in catalog for the appliance type
(e.g. all OV-oven entities from `catalog_ov.py`, plus common entities from
`catalog_core.py`). This ensures the appliance shows up in HA with a useful set of
entities rather than being mostly empty.

The bug: every entity in the merged catalog was created unconditionally in fallback mode,
including `readwrite` control entities such as `uiLockMode` (friendly_name "Child lock")
from the core catalog. This control is shared by washing machines, dryers, and dishwashers
— but **not** by ovens, refrigerators, and other appliance types. When the capabilities
API recovered on the next startup, `uiLockMode` was correctly absent from the oven's
capability list and was not recreated, leaving a stale registry entry that HA displays as
a ghost.

**Fix**

In fallback mode, `readwrite` control entities (switches, selects, numbers with write
access) are now only created if they have **already appeared in the appliance's reported
state** at least once. Read-only sensors (`access: read` / `constant`) and write-only
buttons (`access: write`) are still created unconditionally — they are safe to assume for
any appliance of the given type and do not produce ghost entities.

**What to do if you see the ghost entity**

The entity was already written into HA's entity registry before this fix. After upgrading,
navigate to the device card, click the ghost entity, open its settings (⚙), and delete it
manually. The fix prevents new ghost entities from being created on future fallback
startups.

---

### Verbier air purifier — TVOC sensor showing `9.8e-07` instead of a ppb reading

**Symptom:** On Verbier devices the TVOC sensor displayed a tiny dimensionless number
(e.g. `9.8e-07`) rather than the expected integer ppb value (e.g. `1070 ppb`).

**Root cause:** Home Assistant's `volatile_organic_compounds_parts` device class internally
uses `UnitlessRatioConverter`.  When a `native_unit` of `ppb` was supplied, HA divided
the raw appliance integer by 10⁹ to produce a dimensionless ratio — the opposite of what
users expect.  The sensor attributes also lost the `unit_of_measurement` label.

**Fix:** The `device_class` for the TVOC entity is now set to `None`.  Without a device
class HA passes the raw integer straight through, displaying the value exactly as the
appliance reports it (`1070 ppb`).

---

### Verbier air purifier — wrong filter-type names for codes 55 and 194

**Symptom:** The filter-type sensor showed the wrong names for Verbier's filters:
- Filter code `55` was labelled `Air filter` (should be `CLEAN Particle filter`)
- Filter code `194` was labelled `Humidification filter` (should be `FRESH Anti-odor filter`)

**Fix:** The filter-type mappings in the air-purifier catalog (`FilterType`, `FilterType_1`,
`FilterType_2`) have been corrected with the product-accurate names.

---

## Upgrade notes

No configuration changes required. Install the update, restart Home Assistant, and remove
any pre-existing ghost entities from affected device cards.

**Verbier TVOC users:** If the TVOC entity is still showing the old `9.8e-07` state after
upgrading, restart Home Assistant. If it persists, delete the TVOC entity from the device
card (⚙ → Delete entity) and let the integration recreate it — this clears the stale
entity-registry unit preference that was stored as `null`.
