# Release Notes v3.5.9.2

## Bug Fixes

### Dishwasher: Mutually-exclusive options no longer conflict in command payload

When toggling a dishwasher option that has a "turns off competing options" trigger
(e.g. **Extra Silent** turns off Extra Power, Glass Care and Sanitize), the outgoing
command payload now already contains the corrected values before it is sent to the
appliance.

Previously the trigger side-effects were applied only after the API acknowledged the
command (~500 ms too late), so the payload sent to the appliance could contain
conflicting options — for example both `extraSilentOption: true` and
`extraPowerOption: true` at the same time.

The fix evaluates capability triggers inline inside `_build_full_user_selections`,
so the full `userSelections` block written to the API is always self-consistent.

This affects all `userSelections` boolean switches that carry `triggers` in their
capability definition (dishwashers, and potentially future appliance types).
