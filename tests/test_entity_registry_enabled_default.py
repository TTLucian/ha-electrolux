"""Tests for OV targetMicrowavePower catalog entry & registry-enabled-default suppression on combi-microwave models.

Covers:
- catalog_ov.py entry for targetMicrowavePower (icon, no device class/unit)
- _microwave_programs_all_disabled() detection logic (all / some / no MICROWAVE_*)
- entity_registry_enabled_default suppression on ElectroluxNumber
- number bounds fallback for the min/max-less capability
"""

from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import MagicMock

from homeassistant.const import Platform

from custom_components.electrolux.catalogs.catalog_ov import CATALOG_OV
from custom_components.electrolux.const import NUMBER
from custom_components.electrolux.number import ElectroluxNumber


def make_number(entity_attr="targetMicrowavePower", capabilities=None, catalog_entry=None):
    """Build an ElectroluxNumber with optional appliance capabilities."""
    coordinator = MagicMock()
    coordinator.hass = MagicMock()
    coordinator.hass.loop = MagicMock()
    coordinator.hass.loop.time.return_value = 1_000_000.0
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.data = {"api_key": "test_api_key_1234567890abcdef"}
    coordinator._last_update_times = {}

    mock_appliance = MagicMock()
    mock_appliance.state = {"properties": {"reported": {}}, "connectionState": "connected"}
    if capabilities is not None:
        # Only these attributes are accessed by the suppression helper
        mock_appliance.data = SimpleNamespace(capabilities=capabilities)
    mock_appliances = MagicMock()
    mock_appliances.get_appliance.return_value = mock_appliance
    coordinator.data = {"appliances": mock_appliances}

    entity = ElectroluxNumber(
        coordinator=coordinator,
        name="Target Microwave Power",
        config_entry=coordinator.config_entry,
        pnc_id="944066813_02",
        entity_type=Platform.NUMBER,
        entity_name="targetMicrowavePower",
        entity_attr=entity_attr,
        entity_source=None,
        capability={"access": "readwrite", "type": "number"},
        unit=None,
        device_class=None,
        entity_category=None,
        icon="mdi:microwave",
        catalog_entry=catalog_entry,
    )
    entity.hass = coordinator.hass
    return entity


def microwave_program_values(disabled: bool, extra_values: dict | None = None) -> dict:
    """Build a program capability like the API schema of combi-microwave ovens."""
    microwave_names = [
        "MICROWAVE_CONVENTIONAL_COOKING",
        "MICROWAVE_DEFROST",
        "MICROWAVE_FULL",
        "MICROWAVE_GRILL",
        "MICROWAVE_LIQUID",
        "MICROWAVE_REHEAT",
        "MICROWAVE_TRUE_FAN",
    ]
    values = {name: {"disabled": disabled} for name in microwave_names}
    values.update(extra_values or {})
    return values


# ---SECTION-BREAK---


class TestCatalogEntry:
    """catalog_ov.py entry for targetMicrowavePower."""

    def test_entry_exists(self):
        assert "targetMicrowavePower" in CATALOG_OV

    def test_capability_info(self):
        entry = CATALOG_OV["targetMicrowavePower"]
        assert entry.capability_info["access"] == "readwrite"
        assert entry.capability_info["type"] == "number"

    def test_no_device_class_or_unit(self):
        """The API provides no unit or range — no guesses."""
        entry = CATALOG_OV["targetMicrowavePower"]
        assert entry.device_class is None
        assert entry.unit is None

    def test_icon(self):
        assert CATALOG_OV["targetMicrowavePower"].entity_icon == "mdi:microwave"


class TestMicrowaveProgramsAllDisabled:
    """_microwave_programs_all_disabled() detection logic."""

    def test_all_disabled_true(self):
        caps = {"program": {"values": microwave_program_values(disabled=True)}}
        entity = make_number(capabilities=caps)
        assert entity._microwave_programs_all_disabled() is True

    def test_some_enabled_false(self):
        caps = {
            "program": {
                "values": microwave_program_values(
                    disabled=True,
                    extra_values={"MICROWAVE_FULL": {"disabled": False}, "TRUE_FAN": {}},
                )
            }
        }
        entity = make_number(capabilities=caps)
        assert entity._microwave_programs_all_disabled() is False

    def test_no_microwave_values_false(self):
        """Regular ovens without MICROWAVE_* programs are unaffected."""
        caps = {"program": {"values": {"TRUE_FAN": {}, "GRILL": {}}}}
        entity = make_number(capabilities=caps)
        assert entity._microwave_programs_all_disabled() is False

    def test_no_program_capability_false(self):
        entity = make_number(capabilities={"applianceState": {"values": {}}})
        assert entity._microwave_programs_all_disabled() is False

    def test_no_capabilities_false(self):
        entity = make_number(capabilities=None)
        assert entity._microwave_programs_all_disabled() is False


class TestEntityRegistryEnabledDefault:
    """Suppression flows through ElectroluxNumber.entity_registry_enabled_default."""

    def test_suppressed_when_all_microwave_disabled(self):
        caps = {"program": {"values": microwave_program_values(disabled=True)}}
        entity = make_number(capabilities=caps)
        assert entity.entity_registry_enabled_default is False

    def test_enabled_when_microwave_programs_allowed(self):
        caps = {
            "program": {
                "values": microwave_program_values(
                    disabled=True,
                    extra_values={"MICROWAVE_FULL": {"disabled": False}},
                )
            }
        }
        entity = make_number(capabilities=caps)
        assert entity.entity_registry_enabled_default is True

    def test_enabled_for_oven_without_microwave_programs(self):
        caps = {"program": {"values": {"TRUE_FAN": {}, "GRILL": {}}}}
        entity = make_number(capabilities=caps)
        assert entity.entity_registry_enabled_default is True

    def test_other_attributes_not_suppressed(self):
        """Only targetMicrowavePower is subject to the suppression rule."""
        caps = {"program": {"values": microwave_program_values(disabled=True)}}
        entity = make_number(entity_attr="targetTemperatureC", capabilities=caps)
        assert entity.entity_registry_enabled_default is True

    def test_catalog_override_still_respected(self):
        """A catalog entry disabling an entity by default still wins (non-microwave attrs)."""
        caps = {"program": {"values": microwave_program_values(disabled=True)}}
        catalog = MagicMock()
        catalog.entity_registry_enabled_default = False
        entity = make_number(entity_attr="targetTemperatureC", capabilities=caps, catalog_entry=catalog)
        assert entity.entity_registry_enabled_default is False


class TestNumberBoundsFallback:
    """The capability has no min/max/step — number.py defaults must kick in."""

    def test_entity_type_resolution(self):
        """readwrite number capability resolves to NUMBER."""
        entity = make_number()
        assert entity.entity_type == NUMBER

    def test_min_max_fallback(self):
        entity = make_number()
        assert entity.native_min_value is not None
        assert entity.native_max_value is not None
        assert entity.native_step is not None


class TestIssueSample:
    """Smoke test using the program schema from the issue #193 diagnostics.

    (samples/ is gitignored in this repo, so the excerpt is inlined.)
    """

    ISSUE_PROGRAM_VALUES: ClassVar[dict] = {
        "AUGRATIN": {},
        "BOTTOM": {},
        "MICROWAVE_CONVENTIONAL_COOKING": {"disabled": True},
        "MICROWAVE_DEFROST": {"disabled": True},
        "MICROWAVE_FULL": {"disabled": True},
        "MICROWAVE_GRILL": {"disabled": True},
        "MICROWAVE_GRILL_FAN": {"disabled": True},
        "MICROWAVE_LIQUID": {"disabled": True},
        "MICROWAVE_REHEAT": {"disabled": True},
        "MICROWAVE_TRUE_FAN": {"disabled": True},
        "PIZZA": {},
        "TRUE_FAN": {},
    }

    def test_issue_schema_all_microwave_disabled(self):
        program_values = self.ISSUE_PROGRAM_VALUES
        microwave = {k: v for k, v in program_values.items() if k.startswith("MICROWAVE_")}
        assert microwave, "schema must contain MICROWAVE_* program values"
        assert all(v.get("disabled") for v in microwave.values())

        caps = {"program": {"values": program_values}}
        entity = make_number(capabilities=caps)
        assert entity._microwave_programs_all_disabled() is True
        assert entity.entity_registry_enabled_default is False
