"""Button platform for Electrolux."""

import hashlib
import logging
from typing import Any

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUTTON, CONF_API_KEY, DOMAIN, icon_mapping
from .coordinator import ElectroluxCoordinator
from .entity import ElectroluxEntity
from .model import ElectroluxDevice
from .util import (
    AuthenticationError,
    ElectroluxApiClient,
    execute_command_with_error_handling,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure button platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [
                entity for entity in appliance.entities if entity.entity_type == BUTTON
            ]
            _LOGGER.debug(
                "Electrolux add %d BUTTON entities to registry for appliance %s",
                len(entities),
                appliance_id,
            )
            async_add_entities(entities)


class ElectroluxButton(ElectroluxEntity, ButtonEntity):
    """Electrolux button class."""

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
        val_to_send: str,
    ) -> None:
        """Initialize the Button Entity."""
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
        self.val_to_send = val_to_send

    @property
    def entity_domain(self):
        """Entity domain for the entry. Used for consistent entity_id."""
        return BUTTON

    @property
    def device_class(self) -> ButtonDeviceClass | None:
        """Return the device class for the button entity."""
        if self._catalog_entry and hasattr(self._catalog_entry, "device_class"):
            device_class = self._catalog_entry.device_class
            if isinstance(device_class, ButtonDeviceClass):
                return device_class
        return self._device_class

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        # Use stable unique_id based on API key hash, including val_to_send for button differentiation
        api_key = self.config_entry.data.get(CONF_API_KEY, "")
        api_key_hash = (
            hashlib.sha256(api_key.encode()).hexdigest()[:16] if api_key else "unknown"
        )
        # Normalize entity_attr by removing fPPN prefix for consistent unique_ids
        normalized_attr = self.entity_attr.lower()
        if normalized_attr.startswith("fppn_"):
            normalized_attr = normalized_attr.replace("fppn_", "").strip("_")
        elif normalized_attr.startswith("fppn"):
            normalized_attr = normalized_attr.replace("fppn", "").strip("_")
        else:
            normalized_attr = normalized_attr.strip("_")
        return f"{api_key_hash}-{normalized_attr}-{self.val_to_send}-{self.entity_source or 'root'}-{self.pnc_id}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        name = self._name
        if self.catalog_entry and self.catalog_entry.friendly_name:
            # Get appliance name from coordinator data
            appliances = self.coordinator.data.get("appliances", None)
            if appliances:
                appliance = appliances.get_appliance(self.pnc_id)
                if appliance:
                    name = (
                        f"{appliance.name} {self.catalog_entry.friendly_name.lower()}"
                    )
        # Get the last word from the 'name' variable
        # and compare to the command we are sending duplicate names
        # "air filter state reset reset" for instance
        last_word = name.split()[-1]
        if last_word.lower() == str(self.val_to_send).lower():
            return name
        return f"{name} {self.val_to_send}"

    @property
    def icon(self) -> str | None:
        """Return the icon of the entity."""
        return self._icon or icon_mapping.get(
            self.val_to_send, "mdi:gesture-tap-button"
        )

    async def send_command(self) -> bool:
        """Send a command to the device."""
        # Check if appliance is connected before sending command
        if not self.is_connected():
            connectivity_state = self.reported_state.get("connectivityState", "unknown")
            _LOGGER.warning(
                "Appliance %s is not connected (state: %s), cannot execute command for %s",
                self.pnc_id,
                connectivity_state,
                self.entity_attr,
            )
            raise HomeAssistantError(
                f"Appliance is offline (current state: {connectivity_state}). "
                "Please check that the appliance is plugged in and has network connectivity."
            )

        # Check if remote control is enabled before sending command
        if not self.is_remote_control_enabled():
            _LOGGER.warning(
                "Remote control is disabled for appliance %s, cannot execute command for %s",
                self.pnc_id,
                self.entity_attr,
            )
            raise HomeAssistantError(
                "Remote control is disabled for this appliance. Please check the appliance settings."
            )

        # Validate command based on appliance state for executeCommand
        if self.entity_attr == "executeCommand":
            current_state = None
            if self.appliance_status:
                reported = self.appliance_status.get("properties", {}).get(
                    "reported", {}
                )
                # Check for applianceState first, then executionState for dishwashers
                current_state = reported.get("applianceState") or reported.get(
                    "executionState"
                )
            if self.val_to_send == "STOPRESET":
                if current_state not in ["RUNNING", "PAUSED", "DELAYED_START"]:
                    _LOGGER.warning(
                        "Cannot send STOPRESET command to appliance %s in state %s",
                        self.pnc_id,
                        current_state,
                    )
                    raise HomeAssistantError(
                        f"Cannot stop appliance in current state ({current_state}). Appliance must be running, paused, or have a delayed start."
                    )
            elif self.val_to_send == "START":
                if current_state not in ["READY_TO_START", "END_OF_CYCLE"]:
                    _LOGGER.warning(
                        "Cannot send START command to appliance %s in state %s",
                        self.pnc_id,
                        current_state,
                    )
                    raise HomeAssistantError(
                        f"Cannot start appliance in current state ({current_state}). Appliance must be ready to start or at end of cycle."
                    )

        client: ElectroluxApiClient = self.api
        value = self.val_to_send
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

        # Wrap DAM commands in the required format
        if self.is_dam_appliance:
            command = {"commands": [command]}

        _LOGGER.debug("Electrolux send command %s", command)
        try:
            result = await execute_command_with_error_handling(
                client, self.pnc_id, command, self.entity_attr, _LOGGER
            )
        except AuthenticationError as auth_ex:
            # Handle authentication errors by triggering reauthentication
            coordinator: ElectroluxCoordinator = self.coordinator  # type: ignore[assignment]
            await coordinator.handle_authentication_error(auth_ex)
        except Exception:
            # Re-raise any errors from execute_command_with_error_handling
            raise
        _LOGGER.debug("Electrolux send command result %s", result)
        return True

    async def async_press(self) -> None:
        """Execute a button press."""
        # Special handling for manual sync button
        if self.entity_attr == "manualSync":
            await self._perform_manual_sync()
        else:
            await self.send_command()
        # Coordinator refresh is now handled automatically in execute_command_with_error_handling
        # await self.coordinator.async_request_refresh()
        # await self.hass.async_add_executor_job(self.send_command)
        # if self.entity_attr == "ExecuteCommand":
        #     await self.hass.async_add_executor_job(self.coordinator.api.setHacl, self.get_appliance.pnc_id, "0x0403", self.val_to_send, self.entity_source)

    async def _perform_manual_sync(self) -> None:
        """Perform manual sync operation for all appliances."""
        appliance_name = "Unknown Appliance"
        try:
            # Get appliance name for user feedback
            appliances = self.coordinator.data.get("appliances", None)
            if appliances:
                appliance = appliances.get_appliance(self.pnc_id)
                if appliance:
                    appliance_name = appliance.name

            # Fire progress events for each step
            def fire_progress(step: int, message: str, progress: str):
                self.hass.bus.async_fire(
                    "electrolux_manual_sync_progress",
                    {
                        "appliance_id": self.pnc_id,
                        "appliance_name": appliance_name,
                        "step": step,
                        "message": message,
                        "progress": progress,
                    },
                )

            # Initial warning about sensible usage
            fire_progress(
                0,
                "Manual sync initiated. Please use this feature sensibly to avoid unnecessary API calls.",
                "0%",
            )

            # Progress updates during sync
            fire_progress(1, "Disconnecting real-time data stream...", "25%")
            fire_progress(2, "Refreshing appliance data from cloud...", "50%")
            fire_progress(3, "Starting fresh real-time data stream...", "75%")

            # Use the coordinator's thread-safe manual sync method
            await self.coordinator.perform_manual_sync(self.pnc_id, appliance_name)

            # Complete
            fire_progress(4, "Manual sync completed successfully!", "100%")

        except Exception as ex:
            error_msg = f"Manual sync failed: {ex}"
            self.hass.bus.async_fire(
                "electrolux_manual_sync_progress",
                {
                    "appliance_id": self.pnc_id,
                    "appliance_name": appliance_name,
                    "step": -1,
                    "message": error_msg,
                    "progress": "0%",
                },
            )
            _LOGGER.error(
                "Manual sync failed for appliance %s (%s): %s",
                appliance_name,
                self.pnc_id,
                ex,
            )
            raise HomeAssistantError(error_msg) from ex
