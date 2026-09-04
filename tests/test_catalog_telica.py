"""Tests for Telica (portable AC) catalog entries and entity resolution (#199).

Covers:
- Threshold constants cataloged as diagnostic sensors (disabled by default)
- entity-type resolution for the Telica (950011709551065891110697) capability schema
"""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EntityCategory

from custom_components.electrolux.api import ElectroluxLibraryEntity
from custom_components.electrolux.catalogs.catalog_ac import CATALOG_AC
from custom_components.electrolux.const import SENSOR, SWITCH

# Threshold capability names observed on the Telica portable AC (issue #199)
THRESHOLD_CAPS = [
    "filterCleanThreshold",
    "hEPAFilterBuyThreshold",
    "hEPAFilterChangeThreshold",
]


class TestThresholdCatalogEntries:
    """Threshold constants are diagnostic sensors disabled by default (#199)."""

    def test_all_thresholds_in_catalog(self):
        for name in THRESHOLD_CAPS:
            assert name in CATALOG_AC, f"{name} should be in catalog"

    def test_thresholds_are_duration_sensors(self):
        for name in THRESHOLD_CAPS:
            entry = CATALOG_AC[name]
            assert entry.device_class == SensorDeviceClass.DURATION
            assert entry.unit == "s"

    def test_thresholds_diagnostic_and_disabled(self):
        for name in THRESHOLD_CAPS:
            entry = CATALOG_AC[name]
            assert entry.entity_category == EntityCategory.DIAGNOSTIC
            assert entry.entity_registry_enabled_default is False


class TestTelicaEntityTypes:
    """Entity-type resolution for the issue #194 capability schema."""

    def _entity(self, caps):
        return ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities=caps,
        )

    def test_flap_position_is_switch(self):
        """flapPositionAvoidUser (readwrite, ON/OFF) -> SWITCH."""
        entity = self._entity(
            {"flapPositionAvoidUser": {"access": "readwrite", "type": "string", "values": {"ON": {}, "OFF": {}}}}
        )
        assert entity.get_entity_type("flapPositionAvoidUser") == SWITCH

    def test_sound_volume_is_switch(self):
        """soundVolume (readwrite, boolean) -> SWITCH."""
        entity = self._entity({"soundVolume": {"access": "readwrite", "type": "boolean"}})
        assert entity.get_entity_type("soundVolume") == SWITCH

    def test_sound_volume_catalog_entry_is_switch(self):
        """Catalog soundVolume entry uses SWITCH device_class (#199)."""
        from homeassistant.components.switch import SwitchDeviceClass

        entry = CATALOG_AC["soundVolume"]
        assert entry.device_class == SwitchDeviceClass.SWITCH
        assert entry.entity_category == EntityCategory.CONFIG

    def test_pm25_is_sensor(self):
        entity = self._entity({"pm25": {"access": "read", "type": "int"}})
        assert entity.get_entity_type("pm25") == SENSOR

    def test_hepa_filter_inserted_is_sensor(self):
        """hepaFilterInsertedState (read, ON/OFF) -> SENSOR (catalog promotes to BINARY_SENSOR)."""
        entity = self._entity(
            {"hepaFilterInsertedState": {"access": "read", "type": "string", "values": {"ON": {}, "OFF": {}}}}
        )
        assert entity.get_entity_type("hepaFilterInsertedState") == SENSOR
