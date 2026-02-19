"""Switch platform for Electrolux."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SWITCH
from .coordinator import ElectroluxCoordinator
from .entity import ElectroluxEntity
from .util import (
    AuthenticationError,
    ElectroluxApiClient,
    execute_command_with_error_handling,
    format_command_for_appliance,
    string_to_boolean,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure switch platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [
                entity for entity in appliance.entities if entity.entity_type == SWITCH
            ]
            _LOGGER.debug(
                "Electrolux add %d SENSOR entities to registry for appliance %s",
                len(entities),
                appliance_id,
            )
            async_add_entities(entities)
    return


class ElectroluxSwitch(ElectroluxEntity, SwitchEntity):
    """Electrolux switch class."""

    @property
    def entity_domain(self):
        """Entity domain for the entry. Used for consistent entity_id."""
        return SWITCH

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        value = self.extract_value()

        if value is None:
            if self.catalog_entry and self.catalog_entry.state_mapping:
                mapping = self.catalog_entry.state_mapping
                value = self.get_state_attr(mapping)

        if value is None:
            return False

        # Handle boolean values
        if isinstance(value, bool):
            return value

        # Handle string values like "ON"/"OFF"
        if isinstance(value, str):
            result = string_to_boolean(value, fallback=False)
            if isinstance(result, bool):
                return result
            return False

        # For other types, try to convert to boolean
        return bool(value)

    async def switch(self, value: bool) -> None:
        """Control switch state."""
        # Check if appliance is connected before sending command
        if not self.is_connected():
            connectivity_state = self.reported_state.get("connectivityState", "unknown")
            _LOGGER.warning(
                "Appliance %s is not connected (state: %s), cannot set %s",
                self.pnc_id,
                connectivity_state,
                self.entity_attr,
            )
            raise HomeAssistantError(
                f"Appliance is offline (current state: {connectivity_state}). "
                "Please check that the appliance is plugged in and has network connectivity."
            )

        # Remote control validation removed - API handles this with precise appliance-specific rules.
        # Different appliances have different states (ENABLED, NOT_SAFETY_RELEVANT_ENABLED, persistentRemoteControl)
        # that only the API can accurately validate. Error handling in util.py displays friendly messages.

        client: ElectroluxApiClient = self.api
        # Use dynamic capability-based value formatting
        command_value = format_command_for_appliance(
            self.capability, self.entity_attr, value
        )

        command: dict[str, Any]
        if not self.is_dam_appliance:
            # Legacy appliances: always send as simple top-level property
            command = {self.entity_attr: command_value}
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
                        self.entity_attr: command_value,
                    },
                }
            else:
                command = {self.entity_source: {self.entity_attr: command_value}}
        else:
            command = {self.entity_attr: command_value}

        # Wrap DAM commands in the required format
        if self.is_dam_appliance:
            command = {"commands": [command]}

        _LOGGER.debug("Electrolux set value")
        try:
            await execute_command_with_error_handling(
                client, self.pnc_id, command, self.entity_attr, _LOGGER, self.capability
            )
        except AuthenticationError as auth_ex:
            # Handle authentication errors by triggering reauthentication
            coordinator: ElectroluxCoordinator = self.coordinator  # type: ignore[assignment]
            await coordinator.handle_authentication_error(auth_ex)
            raise
        except Exception:
            # Re-raise any errors from execute_command_with_error_handling
            raise
        _LOGGER.debug("Electrolux set value completed")
        # State will be updated via SSE streaming

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.switch(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.switch(False)
