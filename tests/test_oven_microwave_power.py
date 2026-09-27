"""The microwave power control must only be enabled where the oven has one.

`Appliance.setup()` creates entities for every catalog key carrying
`capability_info`, even when the API never declared it as a capability (that is
how `targetDuration` and friends exist regardless). The same behaviour gives plain
steam ovens a `targetMicrowavePower` number entity, which the cloud backs with a
not-applicable sentinel (65535) and no capability at all. Enabled, it renders
with min == max == 0 — a slider that cannot move.

#193 already suppressed the control on combi-microwaves whose MICROWAVE_*
programs are all remotely disabled. It did not cover an oven with no microwave at
all. The discriminator is whether the appliance *advertises* the capability, not
how many microwave programs it lists: `GT3_PS1_Ca` advertises it with zero.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.electrolux.api import ElectroluxLibraryEntity
from custom_components.electrolux.entity import ElectroluxEntity
from custom_components.electrolux.models import Appliance, _has_nested_key

SAMPLES = Path(__file__).parent.parent / "samples"

# (sample) -> (advertises targetMicrowavePower, all MICROWAVE_* disabled, enabled by default)
# Read off each file in samples/, not assumed.
EXPECTED = {
    "OV-944066813_02.json": (True, True, False),  # GT3_CMW combi-microwave (#193)
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


class _Probe(ElectroluxEntity):
    """Minimal ElectroluxEntity exposing only what the predicate reads.

    Bypasses __init__ (which needs a live coordinator) and the entity factory;
    the microwave guard only touches entity_attr, entity_source,
    _catalog_entry and get_appliance().data.capabilities.
    """

    def __init__(self, capabilities: dict, entity_attr: str) -> None:
        state = {"properties": {"reported": {}}}
        self._appliance = Appliance(
            coordinator=None,
            name="oven",
            pnc_id="pnc",
            brand="Electrolux",
            model="model",
            state=state,
            appliance_type="OV",
        )
        self._appliance.data = ElectroluxLibraryEntity(
            name="oven",
            status="connected",
            state=state,
            appliance_info={},
            capabilities=capabilities,
        )
        self.entity_attr = entity_attr
        self.entity_source = None
        self._catalog_entry = None

    @property
    def get_appliance(self) -> Appliance:  # type: ignore[override]
        # Must stay a property: the guards read ``self.get_appliance`` without
        # calling it, matching the base class contract.
        return self._appliance


def _sample_files() -> list[Path]:
    if not SAMPLES.exists():
        return []
    return sorted(p for p in SAMPLES.iterdir() if p.suffix == ".json" and p.name.upper()[:2] in ("OV", "SO"))


class TestAgainstCollectedSamples:
    """Run the real predicate over every oven diagnostic in the repository."""

    @pytest.mark.parametrize("sample", sorted(EXPECTED))
    def test_expected_default_state(self, sample):
        path = SAMPLES / sample
        if not path.exists():
            pytest.skip(f"{sample} not present (samples/ is gitignored)")

        capabilities = _first_dict(json.loads(path.read_text(encoding="utf-8")), "capabilities") or {}
        programs = (capabilities.get("program") or {}).get("values") or {}
        microwave = [v for k, v in programs.items() if k.upper().startswith("MICROWAVE_")]

        declared, all_disabled, enabled = EXPECTED[sample]
        attr = "upperOven/targetMicrowavePower" if sample.startswith("SO-") else "targetMicrowavePower"

        # Guard the fixture: if a sample changes shape, fail loudly rather than
        # silently testing the wrong expectation. The path is nested for SO, so a
        # flat membership check would wrongly report "absent".
        assert _has_nested_key(capabilities, attr) is declared, f"{sample}: capability presence at {attr}"
        assert (bool(microwave) and all(v.get("disabled") for v in microwave)) is all_disabled, (
            f"{sample}: microwave programs"
        )
        assert _Probe(capabilities, attr).entity_registry_enabled_default is enabled

    def test_every_collected_oven_sample_is_classified(self):
        found = {p.name for p in _sample_files()}
        if not found:
            pytest.skip("samples/ not present (gitignored)")
        assert found == set(EXPECTED), f"unclassified oven samples: {found ^ set(EXPECTED)}"


class TestPredicate:
    def test_namespaced_attr_is_recognised(self):
        assert _Probe({}, "upperOven/targetMicrowavePower")._is_microwave_power_attr() is True

    def test_plain_attr_is_recognised(self):
        assert _Probe({}, "targetMicrowavePower")._is_microwave_power_attr() is True

    def test_unrelated_attr_is_not_microwave(self):
        assert _Probe({}, "targetTemperatureC")._is_microwave_power_attr() is False

    def test_absent_capability_is_not_advertised(self):
        assert _Probe({}, "targetMicrowavePower")._microwave_control_advertised() is False

    def test_present_capability_is_advertised(self):
        caps = {"targetMicrowavePower": {"access": "readwrite", "type": "number"}}
        assert _Probe(caps, "targetMicrowavePower")._microwave_control_advertised() is True

    def test_nested_capability_is_found(self):
        caps = {"upperOven": {"targetMicrowavePower": {"access": "readwrite", "type": "number"}}}
        probe = _Probe(caps, "upperOven/targetMicrowavePower")
        assert probe._microwave_control_advertised() is True

    def test_capability_must_match_the_entity_path(self):
        """A flat capability must not satisfy a namespaced entity, or vice versa."""
        caps = {"targetMicrowavePower": {"access": "readwrite", "type": "number"}}
        assert _Probe(caps, "upperOven/targetMicrowavePower")._microwave_control_advertised() is False

    def test_unrelated_entities_keep_their_default(self):
        caps = {"targetTemperatureC": {"access": "readwrite", "type": "temperature"}}
        assert _Probe(caps, "targetTemperatureC").entity_registry_enabled_default is True

    def test_malformed_capabilities_do_not_raise(self):
        probe = _Probe({}, "targetMicrowavePower")
        probe._appliance.data = None
        assert probe._microwave_control_advertised() is False

    def test_malformed_programs_do_not_raise(self):
        probe = _Probe({"program": "not-a-dict"}, "targetMicrowavePower")
        assert probe._microwave_programs_all_disabled() is False
