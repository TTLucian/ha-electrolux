"""The microwave power control must not exist on an oven that has no microwave.

`Appliance.setup()` creates entities for every catalog key carrying
`capability_info`, even when the API never declared it as a capability (that is
how `targetDuration` and friends exist regardless). The same behaviour gives plain
steam ovens a `targetMicrowavePower` number entity, which the cloud backs with a
not-applicable sentinel (65535) and no capability at all. Enabled, it renders
with min == max == 0 - a slider that cannot move.

#193 already suppressed the control on combi-microwaves whose MICROWAVE_*
programs are all remotely disabled. It did not cover an oven with no microwave at
all. The discriminator is whether the appliance *advertises* the capability, not
how many microwave programs it lists: `GT3_PS1_Ca` advertises it with zero.

The suppression happens at *creation* time (CAPABILITY_REQUIRED_CATALOG_KEYS in
models.py), not via `entity_registry_enabled_default`. Home Assistant consults
that property only when a registry entry is first created - for an entry that
already exists `async_get_or_create` returns it untouched, so a default of False
could never have reached users who already had the phantom entity registered.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.electrolux.api import ElectroluxLibraryEntity
from custom_components.electrolux.entity import ElectroluxEntity
from custom_components.electrolux.const import CONF_API_KEY
from custom_components.electrolux.models import (
    CAPABILITY_REQUIRED_CATALOG_KEYS,
    Appliance,
    _has_nested_key,
)

SAMPLES = Path(__file__).parent.parent / "samples"

# (sample) -> (advertises targetMicrowavePower, all MICROWAVE_* disabled, entity created)
# Read off each file in samples/, not assumed.
EXPECTED = {
    "OV-944066813_02.json": (True, True, True),  # GT3_CMW combi-microwave (#193)
    "OV-944188304_02.json": (True, False, True),  # GT3_PS1_Ca: capability, no MW programs
    "OV-944188772_00.json": (False, False, False),  # plain steam oven, reported 65535
    "OV-940321501_00.json": (False, False, False),  # plain steam oven, reported 65535
    "SO-944005079_00.json": (True, False, True),  # structured oven, capability nested under upperOven
    "SO-944035035_01.json": (False, False, False),  # structured oven, no capability
}


def _first_dict(obj, key):
    """Depth-first search for ``key``, mirroring how diagnostics nest it."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = _first_dict(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _first_dict(item, key)
            if found is not None:
                return found
    return None


def _sample_files():
    return sorted(p for p in SAMPLES.glob("*.json") if p.name[:2] in {"OV", "SO"})


def _build_appliance(capabilities: dict | None, reported: dict | None = None, appliance_type: str = "OV") -> Appliance:
    """Build an Appliance wired to a stub coordinator, as setup() requires one."""
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "test_entry"
    coordinator.config_entry.data = {CONF_API_KEY: "test_api_key"}

    state = {
        "properties": {
            "reported": {
                "applianceInfo": {"applianceType": "OV"},
                "applianceState": "IDLE",
                "connectivityState": "connected",
                **(reported if reported is not None else {}),
            }
        }
    }

    appliance = Appliance(
        coordinator=coordinator,
        name="oven",
        pnc_id="pnc",
        brand="Electrolux",
        model="944188772",
        state=state,
        appliance_type=appliance_type,
    )
    appliance.data = ElectroluxLibraryEntity(
        name="oven",
        status="connected",
        state=state,
        appliance_info={},
        capabilities=capabilities if capabilities is not None else {},
    )
    return appliance


class _Probe(ElectroluxEntity):
    """Minimal ElectroluxEntity exposing only what the #193 predicate reads.

    Bypasses __init__ (which needs a live coordinator) and the entity factory;
    the #193 guard only touches entity_attr, entity_source, _catalog_entry and
    get_appliance().data.capabilities.
    """

    def __init__(self, capabilities: dict, entity_attr: str) -> None:
        self._appliance = _build_appliance(capabilities)
        self.entity_attr = entity_attr
        self.entity_source = None
        self._catalog_entry = None

    @property
    def get_appliance(self) -> Appliance:
        return self._appliance


def _microwave_entity_attrs(capabilities: dict | None, reported: dict | None = None) -> set[str]:
    """Leaf names of the microwave power controls produced by setup().

    A namespaced catalog entry such as ``upperOven/targetMicrowavePower`` is
    emitted with ``entity_attr`` set to the *leaf* name; the full path survives
    only in the unique_id. So creation is asserted on the leaf.
    """
    appliance = _build_appliance(capabilities, reported)
    appliance.setup(appliance.data)
    return {str(e.entity_attr).rsplit("/", 1)[-1] for e in appliance.entities if "icrowave" in str(e.entity_attr)}


def _all_entity_attrs(capabilities: dict | None, reported: dict | None = None) -> set[str]:
    appliance = _build_appliance(capabilities, reported)
    appliance.setup(appliance.data)
    return {str(e.entity_attr) for e in appliance.entities}


class TestCreationGate:
    """The entity must not be created at all when the capability is absent."""

    def test_plain_oven_with_sentinel_does_not_create_entity(self):
        """The reported-state sentinel alone must not resurrect the control."""
        assert _microwave_entity_attrs({}, {"targetMicrowavePower": 65535}) == set()

    def test_advertised_capability_creates_entity(self):
        caps = {"targetMicrowavePower": {"access": "readwrite", "type": "number"}}
        assert _microwave_entity_attrs(caps, {"targetMicrowavePower": 100}) == {"targetMicrowavePower"}

    def test_nested_capability_creates_namespaced_entity(self):
        """Structured ovens carry the control as upperOven/targetMicrowavePower.

        The catalog key is namespaced, so the gate must resolve the capability at
        the nested path rather than testing a flat key. The unique_id is what
        proves the namespaced entry produced the entity.
        """
        caps = {"upperOven": {"targetMicrowavePower": {"access": "readwrite", "type": "number"}}}
        appliance = _build_appliance(caps, appliance_type="SO")
        appliance.setup(appliance.data)

        microwave = [e for e in appliance.entities if "icrowave" in str(e.entity_attr)]
        assert len(microwave) == 1
        assert "upperOven" in microwave[0].unique_id

    def test_namespaced_key_needs_the_nested_capability(self):
        """SO catalog carries upperOven/targetMicrowavePower; no capability -> nothing.

        The reported-state sentinel must not be enough on its own, exactly as for
        the flat catalog.
        """
        appliance = _build_appliance({}, {"upperOven": {"targetMicrowavePower": 65535}}, appliance_type="SO")
        appliance.setup(appliance.data)

        assert [e for e in appliance.entities if "icrowave" in str(e.entity_attr)] == []

    def test_missing_capabilities_creates_nothing(self):
        """A capability-less appliance must not crash the loop or create the entity."""
        assert _microwave_entity_attrs(None) == set()

    def test_gate_is_narrow(self):
        """Only the microwave power control is gated."""
        assert CAPABILITY_REQUIRED_CATALOG_KEYS == frozenset({"targetMicrowavePower"})

    def test_undeclared_catalog_entities_are_still_created(self):
        """targetDuration-style undeclared keys keep the generic behaviour."""
        attrs = _all_entity_attrs({}, {"targetDuration": 30})
        assert "targetDuration" in attrs, "gate must not suppress unrelated catalog keys"
        assert not any(a.rsplit("/", 1)[-1] == "targetMicrowavePower" for a in attrs)


class TestSampleMatrix:
    """Every collected oven sample is classified against its own data."""

    @pytest.mark.parametrize("sample", sorted(EXPECTED))
    def test_expected_creation(self, sample):
        path = SAMPLES / sample
        if not path.exists():
            pytest.skip(f"{sample} not present (samples/ is gitignored)")

        capabilities = _first_dict(json.loads(path.read_text(encoding="utf-8")), "capabilities") or {}
        programs = (capabilities.get("program") or {}).get("values") or {}
        microwave = [v for k, v in programs.items() if k.upper().startswith("MICROWAVE_")]

        declared, all_disabled, created = EXPECTED[sample]
        attr = "upperOven/targetMicrowavePower" if sample.startswith("SO-") else "targetMicrowavePower"

        # Guard the fixture: if a sample changes shape, fail loudly rather than
        # silently testing the wrong expectation. The path is nested for SO, so a
        # flat membership check would wrongly report "absent".
        assert _has_nested_key(capabilities, attr) is declared, f"{sample}: capability presence at {attr}"
        assert (bool(microwave) and all(v.get("disabled") for v in microwave)) is all_disabled, (
            f"{sample}: microwave programs"
        )
        assert bool(_microwave_entity_attrs(capabilities)) is created, f"{sample}: entity creation"

    def test_every_collected_oven_sample_is_classified(self):
        found = {p.name for p in _sample_files()}
        if not found:
            pytest.skip("samples/ not present (gitignored)")
        assert found == set(EXPECTED), f"unclassified oven samples: {found ^ set(EXPECTED)}"


class TestPredicate:
    """The #193 rule still applies once the entity exists."""

    def test_namespaced_attr_is_recognised(self):
        assert _Probe({}, "upperOven/targetMicrowavePower")._is_microwave_power_attr() is True

    def test_plain_attr_is_recognised(self):
        assert _Probe({}, "targetMicrowavePower")._is_microwave_power_attr() is True

    def test_unrelated_attr_is_not_microwave(self):
        assert _Probe({}, "targetTemperatureC")._is_microwave_power_attr() is False

    def test_all_microwave_programs_disabled_still_defaults_disabled(self):
        """#193 behaviour is preserved for an entity that does get created."""
        caps = {
            "targetMicrowavePower": {"access": "readwrite", "type": "number"},
            "program": {"values": {"MICROWAVE_FULL_POWER": {"disabled": True}}},
        }
        assert _Probe(caps, "targetMicrowavePower").entity_registry_enabled_default is False

    def test_unrelated_entities_keep_their_default(self):
        caps = {"targetTemperatureC": {"access": "readwrite", "type": "temperature"}}
        assert _Probe(caps, "targetTemperatureC").entity_registry_enabled_default is True

    def test_malformed_programs_do_not_raise(self):
        probe = _Probe({"program": "not-a-dict"}, "targetMicrowavePower")
        assert probe._microwave_programs_all_disabled() is False
