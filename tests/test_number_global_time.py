"""Tests for global time entities that no programme declares."""

from unittest.mock import MagicMock

import pytest

from custom_components.electrolux.const import NUMBER
from custom_components.electrolux.number import ElectroluxNumber


def _entity(entity_attr):
    """Build a number entity whose programme does not declare it."""
    coordinator = MagicMock()
    coordinator.hass = MagicMock()
    coordinator.config_entry = MagicMock()
    entity = ElectroluxNumber(
        coordinator=coordinator,
        name="Test",
        config_entry=coordinator.config_entry,
        pnc_id="TEST_PNC",
        entity_type=NUMBER,
        entity_name="test",
        entity_attr=entity_attr,
        entity_source=None,
        capability={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 86400,
            "step": 3600,
        },
        unit=None,
        device_class=None,
        entity_category=None,
        icon="mdi:test",
    )
    entity.hass = coordinator.hass
    # No programme declares these keys, so the programme lookup finds nothing.
    entity._get_program_constraint = MagicMock(return_value=None)
    entity._is_supported_by_program = MagicMock(return_value=False)
    return entity


@pytest.mark.parametrize(
    "entity_attr", ["program", "targetDuration", "startTime", "stopTime"]
)
def test_global_time_entities_are_not_locked_by_program(entity_attr):
    """Global entities stay adjustable even though no programme declares them.

    stopTime is the delayed start. Appliances advertise it at the top level as
    readwrite 0..86400, and it appears in no programme capability block, so the
    "not in programme capabilities" rule would otherwise lock it to min=max=0
    and make delayed start unusable from Home Assistant.
    """
    assert _entity(entity_attr)._is_locked_by_program() is False


def test_delay_keeps_its_range_when_no_programme_declares_it():
    """With the lock lifted, the capability range survives."""
    assert _entity("stopTime").native_max_value > 0
