"""Tests for ``ElectroluxEntity._is_program_level_key`` (#232).

The helper decides whether a ``userSelections`` write has to be bundled with
``programUID``. Program options are listed inside each program's constraint dict
and must keep ``programUID``; appliance-level keys (e.g. ``autoDoorOpener``) are
listed by no program and are silently rejected by the cloud when bundled with
one, so they must be written on their own.

The expectations below are taken from a real dishwasher dump — see
``tests/fixtures/dw_user_selections.json`` (verbatim excerpt of
``samples/DW-911473025_00.json``), where program constraint dicts key their
entries **namespaced** (``userSelections/glassCareOption``).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.electrolux.const import SELECT, SWITCH
from custom_components.electrolux.select import ElectroluxSelect
from custom_components.electrolux.switch import ElectroluxSwitch

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "dw_user_selections.json").read_text())
DW_CAPS: dict = FIXTURE["capabilities"]

# Options the dishwasher programs do list (namespaced inside the program dicts)
PROGRAM_OPTIONS = (
    "glassCareOption",
    "sanitizeOption",
    "extraPowerOption",
    "extraSilentOption",
    "oneRackOption",
    "sprayZoneOption",
    "xtraDryOption",
    "zoneCleanOption",
)
# Read-only program entries (ecoScore/energyScore/waterScore are listed too)
PROGRAM_SCORES = ("ecoScore", "energyScore", "waterScore")
# Appliance-level keys: no program lists them (issue #232 autoDoorOpener)
APPLIANCE_LEVEL_KEYS = ("autoDoorOpener", "programsOrder")


def _make_coordinator(caps: object):
    """Coordinator whose appliance exposes ``caps`` through get_appliance()."""
    coordinator = MagicMock()
    coordinator.hass = MagicMock()
    coordinator.hass.loop = MagicMock()
    coordinator.hass.loop.time.return_value = 1_000_000.0
    coordinator.config_entry = MagicMock()
    coordinator._last_update_times = {}

    mock_appliance = MagicMock()
    mock_appliance.data = MagicMock()
    mock_appliance.data.capabilities = caps
    mock_appliances = MagicMock()
    mock_appliances.get_appliance.return_value = mock_appliance
    coordinator.data = {"appliances": mock_appliances}
    return coordinator


def _entity(entity_attr: str, entity_source: str | None = "userSelections", caps: object = DW_CAPS) -> ElectroluxSwitch:
    """Build a switch entity backed by ``caps`` (mirrors other test helpers)."""
    coordinator = _make_coordinator(caps)
    return ElectroluxSwitch(
        coordinator=coordinator,
        capability={"access": "readwrite", "type": "boolean"},
        name="Test Switch",
        config_entry=coordinator.config_entry,
        pnc_id="911473025_00",
        entity_type=SWITCH,
        entity_name="test_switch",
        entity_attr=entity_attr,
        entity_source=entity_source,
        unit=None,
        device_class=None,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:test",
    )


class TestProgramLevelKeyClassification:
    """Program constraints are keyed namespaced in real device data."""

    @pytest.mark.parametrize("entity_attr", PROGRAM_OPTIONS)
    def test_program_options_need_program_uid(self, entity_attr):
        """Options listed by a program must keep programUID (regression guard).

        The namespaced form (``userSelections/glassCareOption``) is what the API
        actually uses for dishwashers/washers; matching only the bare attribute
        name would classify every real option as appliance-level and silently
        break program writes (regression of the pre-0e674b4 programUID bundling,
        issue #30).
        """
        assert _entity(entity_attr)._is_program_level_key() is True

    @pytest.mark.parametrize("entity_attr", PROGRAM_SCORES)
    def test_program_scores_need_program_uid(self, entity_attr):
        """Read-only program entries (ecoScore, …) are also program-scoped."""
        assert _entity(entity_attr)._is_program_level_key() is True

    @pytest.mark.parametrize("entity_attr", APPLIANCE_LEVEL_KEYS)
    def test_appliance_level_keys_do_not_need_program_uid(self, entity_attr):
        """Keys no program lists must be written without programUID (#232)."""
        assert _entity(entity_attr)._is_program_level_key() is False

    def test_bare_key_layout_is_matched(self):
        """Oven layout: ``program.values[<program>][<attr>]`` with bare keys."""
        caps = {"program": {"access": "readwrite", "values": {"COOK": {"targetDuration": {"min": 0, "max": 86400}}}}}
        assert _entity("targetDuration", entity_source=None, caps=caps)._is_program_level_key() is True

    def test_cycle_personalization_layout_is_matched(self):
        """Alternative layout: constraints under ``cyclePersonalization/programUID``."""
        caps = {
            "cyclePersonalization/programUID": {
                "access": "readwrite",
                "values": {"COTTON": {"userSelections/refresh": {"access": "readwrite"}}},
            }
        }
        assert _entity("refresh", caps=caps)._is_program_level_key() is True

    def test_no_program_metadata_keeps_bundling(self):
        """Without program evidence the previous behaviour (bundle) is kept.

        Dropping programUID for a genuine program option fails silently in the
        cloud, so an appliance that reports no program constraints must not be
        reclassified.
        """
        caps = {"userSelections/autoDoorOpener": {"access": "readwrite", "type": "boolean"}}
        assert _entity("autoDoorOpener", caps=caps)._is_program_level_key() is True

    def test_empty_program_values_keeps_bundling(self):
        """``programUID`` without values is no program evidence either."""
        caps = {"userSelections/programUID": {"access": "readwrite", "values": {}}}
        assert _entity("autoDoorOpener", caps=caps)._is_program_level_key() is True

    def test_unusable_capabilities_keep_bundling(self):
        """Non-dict capabilities (or a missing appliance) are not evidence."""
        assert _entity("autoDoorOpener", caps=MagicMock())._is_program_level_key() is True
        assert _entity("autoDoorOpener", caps=None)._is_program_level_key() is True

    def test_select_entity_shares_the_classification(self):
        """The helper lives on the shared entity base, so selects behave alike."""
        coordinator = _make_coordinator(DW_CAPS)
        select = ElectroluxSelect(
            coordinator=coordinator,
            capability={"access": "readwrite", "type": "boolean"},
            name="Test Select",
            config_entry=coordinator.config_entry,
            pnc_id="911473025_00",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="extraRinseNumber",
            entity_source="userSelections",
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        # Not part of the dishwasher's programs → appliance-level (#218 family)
        assert select._is_program_level_key() is False


class TestRealSampleClassification:
    """Cross-check the classification against every local appliance dump.

    ``samples/`` is gitignored, so this is skipped when the dumps are not
    present (same approach as tests/test_button.py).  It guards the assumption
    the fix rests on: every real dishwasher lists its options (namespaced)
    inside a program's constraint dict, and never lists ``autoDoorOpener``.
    """

    def test_real_dumps_classify_as_expected(self):
        files = sorted((Path(__file__).resolve().parents[1] / "samples").glob("**/*.json"))
        if not files:
            pytest.skip("samples/ not present (gitignored)")

        checked = 0
        for path in files:
            try:
                dump = json.loads(path.read_text())
            except (ValueError, OSError):
                continue
            detail = (dump.get("data") or {}).get("appliances_detail") or {}
            for node in detail.values():
                caps = (node or {}).get("capabilities") or {}
                if not isinstance(caps, dict) or "userSelections/autoDoorOpener" not in caps:
                    continue
                if not any(
                    isinstance((caps.get(cs) or {}).get("values"), dict) and caps[cs]["values"]
                    for cs in ("program", "userSelections/programUID", "cyclePersonalization/programUID")
                ):
                    continue
                assert _entity("autoDoorOpener", caps=caps)._is_program_level_key() is False, (
                    f"{path.name}: autoDoorOpener must be appliance-level (#232)"
                )
                for option in PROGRAM_OPTIONS:
                    if f"userSelections/{option}" not in caps:
                        continue
                    if not any(
                        option in (cons or {}) or f"userSelections/{option}" in (cons or {})
                        for cs in ("program", "userSelections/programUID", "cyclePersonalization/programUID")
                        for cons in (caps.get(cs) or {}).get("values", {}).values()
                        if isinstance(cons, dict)
                    ):
                        continue
                    assert _entity(option, caps=caps)._is_program_level_key() is True, (
                        f"{path.name}: userSelections/{option} must stay program-level (#30)"
                    )
                    checked += 1

        if checked == 0:
            pytest.skip("no local dump with autoDoorOpener plus program-listed options")

