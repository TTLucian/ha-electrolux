"""Tests for the Electrolux PUREi9 map image entity."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.const import IMAGE
from custom_components.electrolux.image import ElectroluxMapImage, async_setup_entry

MAPS: list[dict[str, Any]] = [
    {
        "id": "map-1",
        "name": "Ground floor",
        "zones": [
            {
                "id": "kitchen",
                "name": "Kitchen",
                "zoneType": "clean",
                "vertices": [{"x": 0, "y": 0}, {"x": 2, "y": 0}, {"x": 2, "y": 2}, {"x": 0, "y": 2}],
            }
        ],
    }
]


def _make_image(maps: Any = None) -> ElectroluxMapImage:
    coordinator = MagicMock()
    coordinator.api.get_interactive_maps = AsyncMock(return_value=MAPS if maps is None else maps)
    hass = MagicMock()
    with patch("homeassistant.components.image.entity.get_async_client"):
        entity = ElectroluxMapImage(
            hass,
            coordinator=coordinator,
            name="Robot",
            config_entry=MagicMock(),
            pnc_id="RVC_PNC",
            entity_type=IMAGE,
            entity_name="map",
            entity_attr="map",
            entity_source=None,
            capability={},
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:map",
        )
    entity.hass = hass
    return entity


class TestMapImage:
    def test_basics(self):
        entity = _make_image()
        assert entity.entity_domain == IMAGE
        assert entity.translation_key == "map"
        assert entity.content_type == "image/svg+xml"

    @pytest.mark.asyncio
    async def test_refresh_renders_svg_and_marks_update(self):
        entity = _make_image()
        entity.entity_id = "image.robot_map"
        with patch.object(ElectroluxMapImage, "async_write_ha_state") as write_state:
            await entity._async_refresh_map()
            image = await entity.async_image()
            assert image is not None
            assert image.startswith(b"<svg")
            assert entity.image_last_updated is not None
            write_state.assert_called_once()

            # Same maps again: no new state written
            await entity._async_refresh_map()
            write_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_zones_gives_no_image(self):
        entity = _make_image([{"id": "m", "zones": None}])
        await entity._async_refresh_map()
        assert await entity.async_image() is None
        assert entity.image_last_updated is None

    @pytest.mark.asyncio
    async def test_api_error_keeps_previous_image(self):
        entity = _make_image()
        await entity._async_refresh_map()
        before = await entity.async_image()
        entity.api.get_interactive_maps = AsyncMock(side_effect=HomeAssistantError("down"))
        await entity._async_refresh_map()
        assert await entity.async_image() == before

    @pytest.mark.asyncio
    async def test_added_to_hass_schedules_refresh(self):
        entity = _make_image()
        with (
            patch("custom_components.electrolux.image.async_track_time_interval") as track,
            patch("custom_components.electrolux.entity.ElectroluxEntity.async_added_to_hass", new=AsyncMock()),
        ):
            entity.async_on_remove = MagicMock()  # type: ignore[method-assign]
            await entity.async_added_to_hass()
        track.assert_called_once()
        assert await entity.async_image() is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(("appliance_type", "expected"), [("PUREi9", 1), ("700series", 0)])
async def test_setup_adds_map_for_purei9_only(appliance_type, expected):
    appliance = MagicMock(appliance_type=appliance_type, pnc_id="RVC_PNC")
    appliance.name = "Robot"
    coordinator = MagicMock()
    coordinator.data = {"appliances": MagicMock()}
    coordinator.data["appliances"].appliances = {"RVC_PNC": appliance}
    entry = MagicMock(runtime_data=coordinator)
    add_entities = MagicMock()
    with patch("homeassistant.components.image.entity.get_async_client"):
        await async_setup_entry(MagicMock(), entry, add_entities)
    assert len(add_entities.call_args.args[0]) == expected
