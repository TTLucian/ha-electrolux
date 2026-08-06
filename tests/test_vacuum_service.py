"""Tests for the vacuum zone cleaning service registration."""

from __future__ import annotations

import pytest
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from custom_components.electrolux.vacuum import SERVICE_START_ZONE_CLEANING_SCHEMA


def test_zone_cleaning_schema_is_an_entity_service_schema():
    """Entity services must use an entity service schema.

    A bare vol.Schema is rejected by async_register_entity_service, which aborts
    setup of the whole vacuum platform.
    """
    assert cv.is_entity_service_schema(SERVICE_START_ZONE_CLEANING_SCHEMA)


def test_zone_cleaning_schema_accepts_a_target():
    """The schema must accept the entity target the service is called with."""
    data = SERVICE_START_ZONE_CLEANING_SCHEMA(
        {
            "entity_id": "vacuum.robot",
            "persistent_map_id": "map-1",
            "zones": [{"zone_id": "zone-1", "power_mode": 2}],
        }
    )
    assert data["persistent_map_id"] == "map-1"
    assert data["zones"][0]["zone_id"] == "zone-1"


def test_zone_cleaning_schema_still_validates_payload():
    """Payload validation is unchanged: zones are required and non empty."""
    with pytest.raises(vol.Invalid):
        SERVICE_START_ZONE_CLEANING_SCHEMA(
            {"entity_id": "vacuum.robot", "persistent_map_id": "map-1", "zones": []}
        )
