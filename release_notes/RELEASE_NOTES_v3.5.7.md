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

## Upgrade notes

No configuration changes required. Install the update, restart Home Assistant, and remove
any pre-existing ghost entities from affected device cards.
