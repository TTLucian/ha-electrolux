"""Switch platform for Electrolux."""

import logging
from typing import (
    Any,
    cast,
)  # cast: CoordinatorEntity lacks ElectroluxCoordinator type param

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
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure switch platform."""
    coordinator = entry.runtime_data
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [
                entity for entity in appliance.entities if entity.entity_type == SWITCH
            ]

            filtered_switches: list[Any] = []
            reported_data = appliance.reported_state or {}

            for entity in entities:
                # Filter out phantom/ghost capabilities (Issue #55)
                # If a property path or capability key is absent from the reported state,
                # the appliance hardware does not support it (e.g., Pod wash, AutoDose)
                if entity.json_path and entity.json_path not in reported_data:
                    if entity.entity_attr not in reported_data:
                        _LOGGER.debug(
                            "Skipping phantom switch entity %s for appliance %s (not present in reported state)",
                            entity.entity_attr,
                            appliance_id,
                        )
                        continue

                filtered_switches.append(entity)

            _LOGGER.debug(
                "Electrolux add %d SWITCH entities to registry for appliance %s (filtered from %d)",
                len(filtered_switches),
                appliance_id,
                len(entities),
            )

            if filtered_switches:
                async_add_entities(filtered_switches)
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
            return bool(string_to_boolean(value, fallback=False))

        # For other types, try to convert to boolean
        return bool(value)

    async def switch(self, value: bool | str) -> None:
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
                "Please check that the appliance is plugged in, has network connectivity and is connected to cloud services.",
                translation_domain=DOMAIN,
                translation_key="appliance_offline",
                translation_placeholders={"state": str(connectivity_state)},
            )
        # that only the API can accurately validate. Error handling in util.py displays friendly messages.

        client: ElectroluxApiClient = self.api
        # Use dynamic capability-based value formatting
        command_value = format_command_for_appliance(
            self.capability, self.entity_attr, value
        )

        command: dict[str, Any]
        if not self.is_dam_appliance:
            # Legacy appliances: send as top-level property, but respect entity_source
            # when the capability key has a slash.
            if self.entity_source == "userSelections":
                # Build the full current userSelections payload so that appliances
                # which treat partial writes as full replacements (resetting omitted
                # options to defaults) keep their sibling options intact.
                full_selections = self._build_full_user_selections(
                    self.entity_attr, command_value
                )
                if full_selections.get("programUID"):
                    command = {"userSelections": full_selections}
                else:
                    command = {self.entity_source: {self.entity_attr: command_value}}
            elif self.entity_source:
                command = {self.entity_source: {self.entity_attr: command_value}}
            else:
                command = {self.entity_attr: command_value}
        elif self.entity_source:
            if self.entity_source == "userSelections":
                # Build the full current userSelections payload (DAM path).
                full_selections = self._build_full_user_selections(
                    self.entity_attr, command_value
                )
                command = {self.entity_source: full_selections}
            else:
                command = {self.entity_source: {self.entity_attr: command_value}}
        else:
            command = {self.entity_attr: command_value}

        # Wrap DAM commands in the required format
        if self.is_dam_appliance:
            command = {"commands": [command]}  # type: ignore[dict-item]

        _LOGGER.debug("Electrolux set value")
        try:
            await execute_command_with_error_handling(
                client, self.pnc_id, command, self.entity_attr, _LOGGER, self.capability
            )
        except AuthenticationError as auth_ex:
            # Handle authentication errors by triggering reauthentication
            _coordinator: ElectroluxCoordinator = self.coordinator  # type: ignore[assignment]
            await _coordinator.handle_authentication_error(auth_ex)
            raise
        except Exception:  # noqa: BLE001
            # Re-raise any errors from execute_command_with_error_handling
            raise

        # Optimistically update local state using base class helper method
        self._apply_optimistic_update(self.entity_attr, command_value)

        # Schedule a follow-up state refresh — some switch properties are not pushed
        # via SSE by the Electrolux cloud, so the optimistic update is the only way
        # HA learns the state without a follow-up poll.
        cast(ElectroluxCoordinator, self.coordinator)._schedule_state_refresh(
            self.pnc_id
        )

        _LOGGER.debug("Electrolux set value completed")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if self.capability and self.capability.get("type") == "string":
            # String enum toggle (e.g., fastMode)
            await self.switch("ON")
        else:
            # Normal boolean switch
            await self.switch(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if self.capability and self.capability.get("type") == "string":
            await self.switch("OFF")
        else:
            await self.switch(False)
