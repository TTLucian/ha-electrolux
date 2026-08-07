"""Centralized state-availability rules for executeCommand buttons.

Each dict maps a button value (the string sent to the API) to the list of
``applianceState`` values in which that command is accepted by the cloud.
When a ``None`` is assigned, no restriction is imposed — the button is always
available as long as the appliance is connected.

These constants are imported by catalog files via ``available_when_states=`` and
consumed by :class:`~custom_components.electrolux.button.ElectroluxButton`.
Keeping them here means the rules for every appliance type live in one place and
are easy to extend when new API samples become available.

They are a fallback. An appliance that publishes ``applianceState`` triggers
describes its own state machine, and :func:`execute_states_from_capabilities`
reads that instead, so a model whose rules differ from its type's table gets the
right buttons without a new constant.

Sources (all from ``samples/*.json`` → ``applianceState`` → ``triggers``)
-------
* OV-944188772_00.json      → OVEN_EXECUTE_STATES
* SO-944035035_01.json      → STRUCTURED_OVEN_EXECUTE_STATES
* WM-914915144_00.json      → WASHER_EXECUTE_STATES
* WD-914611500_00.json,
  WD-914611000_01.json      → WASHER_EXECUTE_STATES (identical state machine)
* TD-916098401_00.json,
  TD-916098618_00.json,
  TD-916099949_00.json,
  TD-916099971_01.json      → DRYER_EXECUTE_STATES (adds ANTICREASE + IDLE)
* DW-911434654_02.json,
  DW-911434834_01.json      → DISHWASHER_EXECUTE_STATES (STOPRESET for
                              DELAYED_START; PAUSE only in RUNNING; START in IDLE)
* AC / ice maker: no state-gating triggers found in available samples;
  no constant defined — ``available_when_states`` defaults to ``None``.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Oven (OV) — OV-944188772_00.json
# ---------------------------------------------------------------------------
# applianceState  → accepted executeCommand values
# RUNNING         → STOPRESET
# PAUSED          → STOPRESET
# DELAYED_START   → STOPRESET
# READY_TO_START  → START
# END_OF_CYCLE    → START  (re-start after cycle ends)
OVEN_EXECUTE_STATES: dict[str, list[str]] = {
    "STOPRESET": ["RUNNING", "PAUSED", "DELAYED_START"],
    "START": ["READY_TO_START", "END_OF_CYCLE"],
}

# ---------------------------------------------------------------------------
# Structured Oven (SO / upperOven) — SO-944035035_01.json
# ---------------------------------------------------------------------------
# The structured oven has only three applianceState values: ALARM, OFF, RUNNING.
# There are NO conditional triggers in the sample — no PAUSED, DELAYED_START,
# READY_TO_START, or END_OF_CYCLE states exist for this appliance type.
# Using OVEN_EXECUTE_STATES here would make START permanently invisible because
# it requires READY_TO_START / END_OF_CYCLE which never occur on a structured oven.
# applianceState  → accepted executeCommand values
# OFF             → START   (oven is idle/ready)
# RUNNING         → STOPRESET
STRUCTURED_OVEN_EXECUTE_STATES: dict[str, list[str]] = {
    "START": ["OFF"],
    "STOPRESET": ["RUNNING"],
}

# ---------------------------------------------------------------------------
# Washer (WM) — WM-914915144_00.json
# ---------------------------------------------------------------------------
# applianceState  → accepted executeCommand values
# RUNNING         → PAUSE
# DELAYED_START   → PAUSE
# PAUSED          → RESUME, STOPRESET
# END_OF_CYCLE    → STOPRESET
# READY_TO_START  → START
WASHER_EXECUTE_STATES: dict[str, list[str]] = {
    "STOPRESET": ["PAUSED", "END_OF_CYCLE"],
    "START": ["READY_TO_START"],
    "PAUSE": ["RUNNING", "DELAYED_START"],
    "RESUME": ["PAUSED"],
}

# ---------------------------------------------------------------------------
# Washer Dryer (WD) — WD-914611500_00.json, WD-914611000_01.json
# ---------------------------------------------------------------------------
# Same executeCommand state machine as a plain washer.
# (WD also has IDLE→ON in the applianceState triggers, but that ON command is
# not part of the executeCommand capability exposed in the catalog.)
# applianceState  → accepted executeCommand values
# RUNNING         → PAUSE
# DELAYED_START   → PAUSE
# PAUSED          → RESUME, STOPRESET
# END_OF_CYCLE    → STOPRESET
# READY_TO_START  → START
WASHER_DRYER_EXECUTE_STATES: dict[str, list[str]] = {
    "STOPRESET": ["PAUSED", "END_OF_CYCLE"],
    "START": ["READY_TO_START"],
    "PAUSE": ["RUNNING", "DELAYED_START"],
    "RESUME": ["PAUSED"],
}

# ---------------------------------------------------------------------------
# Dryer (TD) — TD-916098401_00.json (confirmed across all 4 TD samples)
# ---------------------------------------------------------------------------
# Dryers have two extra applianceState values vs washers:
#   ANTICREASE — post-cycle anti-crease tumbling phase; STOPRESET is valid
#   IDLE       — machine on but no program selected; START is valid
# applianceState  → accepted executeCommand values
# RUNNING         → PAUSE
# DELAYED_START   → PAUSE
# PAUSED          → RESUME, STOPRESET
# END_OF_CYCLE    → STOPRESET
# ANTICREASE      → STOPRESET    ← dryer-specific
# READY_TO_START  → START
# IDLE            → START        ← dryer-specific
DRYER_EXECUTE_STATES: dict[str, list[str]] = {
    "STOPRESET": ["PAUSED", "END_OF_CYCLE", "ANTICREASE"],
    "START": ["READY_TO_START", "IDLE"],
    "PAUSE": ["RUNNING", "DELAYED_START"],
    "RESUME": ["PAUSED"],
}

# ---------------------------------------------------------------------------
# Dishwasher (DW) — DW-911434654_02.json + DW-911434834_01.json
# ---------------------------------------------------------------------------
# Key differences from WASHER_EXECUTE_STATES:
#   • PAUSE is only valid in RUNNING  (washers also allow PAUSE in DELAYED_START)
#   • STOPRESET is valid in DELAYED_START  (washers do NOT allow this)
#   • START is also valid in IDLE  (dishwasher powers on in IDLE before READY)
# applianceState  → accepted executeCommand values
# RUNNING         → PAUSE
# PAUSED          → RESUME, STOPRESET
# END_OF_CYCLE    → STOPRESET
# DELAYED_START   → STOPRESET    ← dishwasher-specific (not PAUSE)
# READY_TO_START  → START
# IDLE            → START        ← dishwasher-specific
DISHWASHER_EXECUTE_STATES: dict[str, list[str]] = {
    "STOPRESET": ["PAUSED", "END_OF_CYCLE", "DELAYED_START"],
    "START": ["READY_TO_START", "IDLE"],
    "PAUSE": ["RUNNING"],
    "RESUME": ["PAUSED"],
}

# Air Conditioner (AC) and Refrigerator ice maker have no state-gating in
# available samples. Do NOT add None constants here — omitting
# ``available_when_states`` from the catalog entry achieves the same result
# using the field's default value.


def execute_states_from_capabilities(
    capabilities: dict[str, Any] | None,
    *,
    entity_source: str | None = None,
) -> dict[str, list[str]] | None:
    """Derive the executeCommand rules from an appliance's own capabilities.

    The tables above were transcribed from ``applianceState`` → ``triggers`` in
    sample files, so the appliance already ships the same information. Reading
    it at runtime keeps a model that deviates from its type's table working.

    Returns a ``{command: [applianceState, ...]}`` mapping in the same shape as
    the constants, or ``None`` when the appliance publishes no usable triggers,
    in which case the caller should fall back to the catalog entry.

    Only ``{operand_1: "value", operand_2: X, operator: "eq"}`` conditions are
    read, matching the trigger handling in ``entity.py``. Compound conditions
    (a dict operand) and ``disabled`` actions carry no command list and are
    skipped.
    """
    if not isinstance(capabilities, dict):
        return None

    appliance_state: Any | None = None

    if entity_source:
        appliance_state = capabilities.get(f"{entity_source}/applianceState")

    if appliance_state is None:
        appliance_state = capabilities.get("applianceState")

    if not isinstance(appliance_state, dict):
        return None

    states: dict[str, list[str]] = {}
    for trigger in appliance_state.get("triggers", []):
        if not isinstance(trigger, dict):
            continue

        condition = trigger.get("condition", {})
        if not isinstance(condition, dict):
            continue
        if condition.get("operator") != "eq" or condition.get("operand_1") != "value":
            continue
        state = condition.get("operand_2")
        if not isinstance(state, str):
            continue

        action = trigger.get("action", {})
        if not isinstance(action, dict):
            continue
        execute_command = action.get("executeCommand")
        if not isinstance(execute_command, dict):
            continue
        values = execute_command.get("values")
        if not isinstance(values, dict):
            continue

        for command in values:
            if state not in states.setdefault(command, []):
                states[command].append(state)

    return states or None
