"""Text platform for Electrolux."""

# import asyncio
import logging
from typing import Any

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TEXT
from .coordinator import ElectroluxCoordinator
from .entity import ElectroluxEntity
from .model import ElectroluxDevice
from .util import (
    AuthenticationError,
    ElectroluxApiClient,
    map_command_error_to_home_assistant_error,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure text platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [
                entity for entity in appliance.entities if entity.entity_type == TEXT
            ]
            _LOGGER.debug(
                "Electrolux add %d TEXT entities to registry for appliance %s",
                len(entities),
                appliance_id,
            )
            async_add_entities(entities)


class ElectroluxText(ElectroluxEntity, TextEntity):
    """Electrolux Text class."""

    def __init__(
        self,
        coordinator: Any,
        name: str,
        config_entry,
        pnc_id: str,
        entity_type: Platform,
        entity_name,
        entity_attr,
        entity_source,
        capability: dict[str, Any],
        unit: str,
        device_class: str,
        entity_category: EntityCategory,
        icon: str,
        catalog_entry: ElectroluxDevice | None,
    ) -> None:
        """Initialize the Text Entity."""
        super().__init__(
            coordinator=coordinator,
            capability=capability,
            name=name,
            config_entry=config_entry,
            pnc_id=pnc_id,
            entity_type=entity_type,
            entity_name=entity_name,
            entity_attr=entity_attr,
            entity_source=entity_source,
            unit=None,
            device_class=device_class,
            entity_category=entity_category,
            icon=icon,
            catalog_entry=catalog_entry,
        )

    @property
    def entity_domain(self) -> str:
        """Entity domain for the entry. Used for consistent entity_id."""
        return TEXT

    @property
    def native_max_len(self) -> int | None:
        """Return the maximum length of the text."""
        return self.capability.get("maxLength")

    @property
    def native_min_len(self) -> int:
        """Return the minimum length of the text."""
        return 0

    @property
    def native_pattern(self) -> str | None:
        """Return the pattern for the text."""
        return None

    @property
    def native_mode(self) -> str:
        """Return the mode for the text."""
        if self.catalog_entry and self.catalog_entry.mode:
            return self.catalog_entry.mode
        return "text"

    @property
    def native_value(self) -> str | None:
        """Return the current text value."""
        value = self.extract_value()
        if value is None:
            if self.catalog_entry and self.catalog_entry.state_mapping:
                mapping = self.catalog_entry.state_mapping
                value = self.get_state_attr(mapping)
        if value is not None and not isinstance(value, str):
            value = str(value)
        return value

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        client: ElectroluxApiClient = self.api

        command: dict[str, Any]
        if not self.is_dam_appliance:
            # Legacy appliances: always send as simple top-level property
            command = {self.entity_attr: value}
        elif self.entity_source:
            if self.entity_source == "userSelections":
                # Safer access to avoid KeyError if userSelections is missing
                reported = (
                    self.appliance_status.get("properties", {}).get("reported", {})
                    if self.appliance_status
                    else {}
                )
                program_uid = reported.get("userSelections", {}).get("programUID")
                command = {
                    self.entity_source: {
                        "programUID": program_uid,
                        self.entity_attr: value,
                    },
                }
            else:
                command = {self.entity_source: {self.entity_attr: value}}
        else:
            command = {self.entity_attr: value}

        _LOGGER.debug("Electrolux set text value %s", command)
        try:
            result = await client.execute_appliance_command(self.pnc_id, command)
        except AuthenticationError as auth_ex:
            # Handle authentication errors by triggering reauthentication
            coordinator: ElectroluxCoordinator = self.coordinator  # type: ignore[assignment]
            await coordinator.handle_authentication_error(auth_ex)
        except Exception as ex:
            # Use shared error mapping for all errors
            raise map_command_error_to_home_assistant_error(
                ex, self.entity_attr, _LOGGER
            ) from ex
        _LOGGER.debug("Electrolux set text value result %s", result)
        # await asyncio.sleep(2)
        await self.coordinator.async_request_refresh()
