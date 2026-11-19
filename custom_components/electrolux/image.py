"""Image platform for Electrolux: PUREi9 interactive map (zones) as an image."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import IMAGE
from .entity import ElectroluxEntity
from .map_render import render_maps_svg

_LOGGER: logging.Logger = logging.getLogger(__package__)
PARALLEL_UPDATES = 0

# Maps change only when the robot is remapped or zones are edited in the app
MAP_REFRESH_INTERVAL = timedelta(minutes=30)
_PUREI9_TYPES = {"PUREi9"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure the image platform."""
    coordinator = entry.runtime_data
    if appliances := coordinator.data.get("appliances", None):
        entities = [
            ElectroluxMapImage(
                hass,
                coordinator=coordinator,
                name=appliance.name,
                config_entry=entry,
                pnc_id=appliance.pnc_id,
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
            for appliance in appliances.appliances.values()
            if appliance.appliance_type in _PUREI9_TYPES
        ]
        async_add_entities(entities)


class ElectroluxMapImage(ElectroluxEntity, ImageEntity):
    """The zones of a PUREi9's interactive maps, drawn as an SVG."""

    _attr_content_type = "image/svg+xml"

    def __init__(self, hass: HomeAssistant, **kwargs) -> None:
        """Initialize the map image."""
        ElectroluxEntity.__init__(self, **kwargs)
        ImageEntity.__init__(self, hass)
        self._svg: str | None = None

    @property
    def entity_domain(self) -> str:
        """Entity domain for the entry. Used for consistent entity_id."""
        return IMAGE

    async def async_added_to_hass(self) -> None:
        """Load the map and refresh it periodically."""
        await super().async_added_to_hass()
        self.async_on_remove(async_track_time_interval(self.hass, self._async_refresh_map, MAP_REFRESH_INTERVAL))
        await self._async_refresh_map()

    async def _async_refresh_map(self, _now: datetime | None = None) -> None:
        """Fetch the interactive maps and redraw when they changed."""
        try:
            maps = await self.api.get_interactive_maps(self.pnc_id)
        except HomeAssistantError as ex:
            _LOGGER.debug("Electrolux map refresh failed for %s: %s", self.pnc_id, ex)
            return
        svg = render_maps_svg(maps)
        if svg == self._svg:
            return
        self._svg = svg
        self._attr_image_last_updated = dt_util.utcnow() if svg else None
        if self.hass is not None and self.entity_id:
            self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        """Return the map as SVG bytes."""
        return self._svg.encode() if self._svg else None
