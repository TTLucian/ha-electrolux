# Release Notes v3.5.7

## Bug Fixes

### Panel / physical control changes now reflected in Home Assistant

**Affected appliance types:** dishwashers, washing machines, washer-dryers, tumble dryers,
ovens, steam ovens — any appliance with a `remoteControl` capability that includes
`TEMPORARY_LOCKED`.

**Symptom:** Changing a setting directly on the appliance's control panel — for example
a dishwasher option (Extra Power, Glass Care, Sanitize), a washing-machine programme
option or spin speed, or an oven target temperature — was not reflected in Home Assistant
until a full restart or a very long time elapsed. The HA entity kept showing its previous
value.

**Root cause — API does not push SSE events for panel-driven option changes**

The Electrolux SSE livestream pushes only a narrow set of property changes as incremental
events (e.g. `userSelections/programUID`, `timeToEnd`, `applianceState`). Many
panel-controlled properties — boolean options, analogue knob positions, target temperature
— are **never sent as SSE events**. Physical panel interactions are instead signalled
through a `remoteControl` state transition:
`→ TEMPORARY_LOCKED` (panel active) followed by `→ ENABLED` or
`→ NOT_SAFETY_RELEVANT_ENABLED` (panel released).

The integration correctly polled for full appliance state on `applianceState` changes, but
it did not treat the `remoteControl` unlock transition as a trigger for a fresh poll.

**Fix:** The coordinator now tracks the last-seen `remoteControl` value per appliance
(appliance-type agnostic). When an SSE event transitions `remoteControl` from
`TEMPORARY_LOCKED` to any other value, a fresh full-state poll is scheduled via a new
`_schedule_state_refresh()` helper. The helper deduplicates: if a previous poll task is
still pending (e.g. from a rapid sequence of panel interactions or from a concurrent
`applianceState` change), the old task is cancelled before the new one is created.
This captures all option changes made on the physical panel within seconds of the user
releasing it — for all affected appliance types.

> **⚠ Testing required:** This change touches the coordinator's SSE event loop for all
> appliance types. After upgrading, please verify that:
> - Panel option changes (dishwasher, washing machine, oven temperature, etc.) appear in HA
>   within ~10 seconds of releasing the panel.
> - Normal HA-initiated commands still work and optimistic state is not disrupted.
> - No unexpected extra API calls or log errors appear.
> - Appliances that do not have physical panels (or whose `remoteControl` field never
>   reaches `TEMPORARY_LOCKED`) continue to behave as before.
> If you observe regressions, please report them with the integration log at DEBUG level.

---

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

**Fix — replaced fallback mode with automatic capability retry**

Fallback mode has been removed entirely. When the capabilities fetch fails at startup the
integration now records which appliances are affected and retries on every subsequent
update cycle — but only when at least one appliance state poll succeeds (proving the API
is reachable). As soon as the capabilities document arrives the integration schedules a
reload so all entities are created correctly.

Benefits of the new approach:
- No ghost entities: entity creation is driven solely by the real capability document.
- Automatic recovery: after a temporary API outage, entities appear on their own without
  any manual restart.
- Cleaner state: appliances affected by the failure show a minimal set of entities
  (static attributes + anything already in reported state) until recovery.

**What to do if you see the ghost entity from a previous startup**

Navigate to the device card, click the ghost entity, open its settings (⚙), and delete it
manually. The new retry logic prevents any recurrence.

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

### `userSelections/*` entity state not updating after app or panel changes

**Symptom:** Entities backed by a `userSelections` sub-property — such as
dishwasher options (Extra Power, Glass Care, Sanitize), washing-machine temperature and
spin speed, dryer programme options, and similar — did not reflect changes made from the
Electrolux app or the appliance's physical control panel. The HA entity kept showing the
last value that was set *from HA* until the next full restart or manual sync.

**Root cause — phantom top-level key left by optimistic update**

When a command is sent from HA, the integration immediately writes an *optimistic* value
so the UI snaps to the new state without waiting for the SSE confirmation event.

The bug: `_apply_optimistic_update` always wrote the value to the **top level** of
`reported_state` — i.e. `reported["extraPowerOption"] = true` — even though the real
state for every `userSelections/*` entity lives one level deeper at
`reported["userSelections"]["extraPowerOption"]`.

Because `extract_value()` checks the top level first, this phantom key shadowed every
subsequent SSE incremental update that correctly targeted the nested path. Changes made
from the app or control panel arrived via SSE and were written to
`reported["userSelections"]["extraPowerOption"]` — but the phantom top-level key was seen
first and always returned the stale HA value.

The same phantom key also prevented the UI from reverting correctly when a command was
rejected by the API (e.g. 406 "remote control disabled"): the incorrect optimistic value
persisted rather than being replaced by the real SSE rollback.

**Affected entities:** all `userSelections/*` sub-properties on dishwashers (GlassCare,
ExtraPower, Sanitize, ProgramUID, …), washing machines, dryers, and any other appliance
type that uses a `userSelections` namespace.

**Fix:** `_apply_optimistic_update` now navigates into the correct nested sub-dict
before writing when `entity_source` is set. Handles standard single-level sources
(`userSelections`, `fridge`, `freezer`, …) and multi-level slash-path sources. No phantom
top-level key is created, so SSE and poll updates are no longer masked.

---

### Sibling switch options now update immediately when one exclusive option is toggled

**Symptom:** On dishwashers (and other appliances with mutually exclusive options),
toggling one switch — for example turning **Extra Power** ON — left a sibling switch such
as **Glass Care** or **Extra Silent** showing as ON in HA even though the appliance had
already reset it to OFF. The two switches appeared to fight each other until the next full
poll synced the state.

**Root cause — capability triggers not applied to sibling entities**

The Electrolux appliance firmware enforces mutual exclusion rules between certain options.
These constraints are declared in the API capabilities document as `triggers`: when one
property changes to a given value, the appliance automatically resets related properties
to their defaults. Examples:

| Option turned ON | Automatically reset to OFF |
|---|---|
| `extraPowerOption` | `glassCareOption`, `extraSilentOption` |
| `glassCareOption` | `extraPowerOption`, `extraSilentOption`, `sanitizeOption` |
| `sanitizeOption` | `glassCareOption`, `extraSilentOption` |
| `extraSilentOption` | `extraPowerOption`, `glassCareOption`, `sanitizeOption` |

Previously the integration's optimistic update path wrote only the primary entity's new
value. It ignored the trigger side-effects entirely, so sibling entities showed stale
values until the next poll.

**Fix:** A new `_apply_triggered_updates()` method reads the capability triggers for the
changed attribute and immediately applies all side-effect `default` values to sibling
entities in the shared reported-state dict. The coordinator is then notified so all
affected switch entities re-render in the same HA state-machine tick — with no poll delay.

---

## Upgrade notes

No configuration changes required. Install the update, restart Home Assistant, and remove
any pre-existing ghost entities from affected device cards.

**Verbier TVOC users:** If the TVOC entity is still showing the old `9.8e-07` state after
upgrading, restart Home Assistant. If it persists, delete the TVOC entity from the device
card (⚙ → Delete entity) and let the integration recreate it — this clears the stale
entity-registry unit preference that was stored as `null`.
