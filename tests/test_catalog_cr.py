"""Tests for the CR (refrigerator) catalog and attribute filtering (#194).

Covers:
- ATTRIBUTES_BLACKLIST patterns hiding internal fPRPN_/fSPN_ flags
- catalog_cr.py applianceUiSwVersion diagnostic entry
- entity-type resolution for the MDR4 (925061028_00) capability schema
"""

import re

from homeassistant.const import EntityCategory

from custom_components.electrolux.api import ElectroluxLibraryEntity
from custom_components.electrolux.catalogs.catalog_cr import CATALOG_CR
from custom_components.electrolux.const import ATTRIBUTES_BLACKLIST, SENSOR

# fPRPN_/fSPN_ capability names observed on real CR appliances
# (issue #194 diagnostics + local CR samples)
INTERNAL_CR_FLAGS = [
    "fPRPN_AirFilterChange",
    "fPRPN_AirFilterOrder",
    "fPRPN_WaterFilterChange",
    "fPRPN_WaterFilterOrder",
    "fSPN_CRConnectionLost",
]


def _is_blacklisted(name: str) -> bool:
    return any(re.match(pattern, name) for pattern in ATTRIBUTES_BLACKLIST)


class TestInternalFlagBlacklist:
    """fPRPN_/fSPN_ internal flags must not become entities."""

    def test_all_observed_flags_blacklisted(self):
        for name in INTERNAL_CR_FLAGS:
            assert _is_blacklisted(name), f"{name} should be blacklisted"

    def test_real_capabilities_not_collateral_blocked(self):
        """Legitimate CR capabilities must stay discoverable."""
        for name in [
            "waterFilterState",
            "airFilterLifeTime",
            "compressorSpeed",
            "reminderTime",
            "uiLockMode",
            "sensorHumidity",
            "fridge/targetTemperatureC",
            "freezer/fastMode",
            "iceMaker/iceDispenserState",
            "extraCavity/doorState",
            "applianceUiSwVersion",
        ]:
            assert not _is_blacklisted(name), f"{name} must not be blacklisted"


class TestCatalogUiSwVersion:
    """catalog_cr.py applianceUiSwVersion diagnostic entry."""

    def test_entry_exists(self):
        assert "applianceUiSwVersion" in CATALOG_CR

    def test_capability_info(self):
        entry = CATALOG_CR["applianceUiSwVersion"]
        assert entry.capability_info["access"] == "read"
        assert entry.capability_info["type"] == "string"

    def test_diagnostic_and_disabled_by_default(self):
        entry = CATALOG_CR["applianceUiSwVersion"]
        assert entry.entity_category == EntityCategory.DIAGNOSTIC
        assert entry.entity_registry_enabled_default is False


class TestMdr4EntityTypes:
    """Entity-type resolution for the issue #194 capability schema."""

    def _entity(self, caps):
        return ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities=caps,
        )

    def test_ui_sw_version_is_sensor(self):
        entity = self._entity({"applianceUiSwVersion": {"type": "string", "access": "read"}})
        assert entity.get_entity_type("applianceUiSwVersion") == SENSOR

    def test_main_board_sw_version_is_sensor(self):
        entity = self._entity({"applianceMainBoardSwVersion": {"type": "string", "access": "read"}})
        assert entity.get_entity_type("applianceMainBoardSwVersion") == SENSOR

    def test_fridge_target_temperature_is_number(self):
        from custom_components.electrolux.const import NUMBER

        entity = self._entity({"fridge": {"targetTemperatureC": {"type": "temperature", "access": "readwrite"}}})
        assert entity.get_entity_type("fridge/targetTemperatureC") == NUMBER

    def test_freezer_fast_mode_readwrite_is_switch(self):
        from custom_components.electrolux.const import SWITCH

        caps = {"freezer": {"fastMode": {"type": "string", "access": "readwrite", "values": {"OFF": {}, "ON": {}}}}}
        entity = self._entity(caps)
        assert entity.get_entity_type("freezer/fastMode") == SWITCH
