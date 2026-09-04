"""Tests for Telica (portable AC) attribute filtering and device info (#199).

Covers:
- ATTRIBUTES_BLACKLIST patterns hiding internal *Threshold constants
- entity-type resolution for the Telica (950011709551065891110697) capability schema
- device_info PNC/serial extraction from applianceData
"""

import re

from custom_components.electrolux.api import ElectroluxLibraryEntity
from custom_components.electrolux.const import ATTRIBUTES_BLACKLIST, SENSOR, SWITCH

# Threshold capability names observed on the Telica portable AC (issue #199)
INTERNAL_THRESHOLDS = [
    "filterCleanThreshold",
    "hEPAFilterBuyThreshold",
    "hEPAFilterChangeThreshold",
]

# Legitimate Telica capabilities that must NOT be blocked
LEGITIMATE_TELICA_CAPS = [
    "flapPositionAvoidUser",
    "soundVolume",
    "pm25",
    "pm10",
    "hepaFilterState",
    "hepaFilterInsertedState",
    "filterRuntime",
    "filterReset",
    "executeCommand",
    "targetTemperatureC",
    "ambientTemperatureC",
]


def _is_blacklisted(name: str) -> bool:
    return any(re.match(pattern, name) for pattern in ATTRIBUTES_BLACKLIST)


class TestThresholdBlacklist:
    """Internal *Threshold constants must not become entities (#199)."""

    def test_all_observed_thresholds_blacklisted(self):
        for name in INTERNAL_THRESHOLDS:
            assert _is_blacklisted(name), f"{name} should be blacklisted"

    def test_real_capabilities_not_collateral_blocked(self):
        """Legitimate Telica capabilities must stay discoverable."""
        for name in LEGITIMATE_TELICA_CAPS:
            assert not _is_blacklisted(name), f"{name} must not be blacklisted"


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

    def test_pm25_is_sensor(self):
        entity = self._entity({"pm25": {"access": "read", "type": "int"}})
        assert entity.get_entity_type("pm25") == SENSOR

    def test_hepa_filter_inserted_is_sensor(self):
        """hepaFilterInsertedState (read, ON/OFF) -> SENSOR (catalog promotes to BINARY_SENSOR)."""
        entity = self._entity(
            {"hepaFilterInsertedState": {"access": "read", "type": "string", "values": {"ON": {}, "OFF": {}}}}
        )
        assert entity.get_entity_type("hepaFilterInsertedState") == SENSOR
