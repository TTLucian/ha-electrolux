"""Fan platform for Electrolux air purifiers.

This fan entity combines Workmode and Fanspeed control into a unified Home Assistant
fan interface. The entity dynamically adapts to different air purifier models:

Model-Specific Capabilities:
- A9 (PUREA9):
  * Fanspeed: 1-9 (9 speed levels)
  * Workmode: Manual, Auto, PowerOff
  * Preset modes: Manual, Auto
  * Speed percentage: 1=11%, 5=56%, 9=100%

- Muju (UltimateHome 500):
  * Fanspeed: 1-5 (5 speed levels)
  * Workmode: Auto, Manual, Quiet, PowerOff
  * Preset modes: Auto, Manual, Quiet
  * Speed percentage: 1=20%, 3=60%, 5=100%

Dynamic Adaptation:
The fan entity reads capabilities directly from the appliance API, not from the
catalog. This ensures correct behavior for each model:
- Speed range detected from Fanspeed capability (min/max attributes)
- Preset modes extracted from Workmode capability (values excluding PowerOff)
- Percentage conversion uses Home Assistant's ordered_list_item helpers

Features:
- TURN_ON/TURN_OFF: Controls PowerOff mode vs active modes
- SET_SPEED: Percentage-based speed control (0-100%)
- PRESET_MODE: Quick access to operation modes (Manual, Auto, Quiet)
"""

import logging
from typing import Any, cast

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import DOMAIN, FAN
from .coordinator import ElectroluxCoordinator
from .entity import ElectroluxEntity
from .util import (
    AuthenticationError,
    ElectroluxApiClient,
    execute_command_with_error_handling,
    format_command_for_appliance,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure fan platform."""
    coordinator = entry.runtime_data
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [
                entity for entity in appliance.entities if entity.entity_type == FAN
            ]
            _LOGGER.debug(
                "Electrolux add %d FAN entities to registry for appliance %s",
                len(entities),
                appliance_id,
            )
            async_add_entities(entities)
    return


class ElectroluxFan(ElectroluxEntity, FanEntity):
    """Electrolux Fan entity for air purifiers."""

    def __init__(
        self,
        coordinator: Any,
        name: str,
        config_entry,
        pnc_id: str,
        entity_type,
        entity_name,
        entity_attr,
        entity_source,
        capability: dict[str, Any],
        unit,
        device_class: str,
        entity_category,
        icon: str,
        catalog_entry=None,
    ) -> None:
        """Initialize the Fan entity."""
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
            unit=unit,
            device_class=device_class,
            entity_category=entity_category,
            icon=icon,
            catalog_entry=catalog_entry,
        )

        self._attr_supported_features = (
            FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.SET_SPEED
            | FanEntityFeature.PRESET_MODE
        )

        # Get speed range from Fanspeed capability
        self._speed_range = (1, 9)  # Default
        if fanspeed_cap := self.get_capability("Fanspeed"):
            min_speed = fanspeed_cap.get("min", 1)
            max_speed = fanspeed_cap.get("max", 9)
            self._speed_range = (min_speed, max_speed)

        # Get available preset modes from Workmode capability
        self._preset_modes = []
        if workmode_cap := self.get_capability("Workmode"):
            if values := workmode_cap.get("values", {}):
                # Extract all modes except PowerOff (that's handled by on/off)
                self._preset_modes = [
                    mode for mode in values.keys() if mode.lower() != "poweroff"
                ]

        self._attr_preset_modes = self._preset_modes if self._preset_modes else None
        self._attr_speed_count = self._speed_range[1] - self._speed_range[0] + 1

    def get_capability(self, attr_name: str) -> dict[str, Any] | None:
        """Get capability definition for an attribute from appliance."""
        if not self.appliance_status or not isinstance(self.appliance_status, dict):
            return None

        capabilities = cast(
            dict[str, Any], self.appliance_status.get("capabilities", {})
        )
        return capabilities.get(attr_name)

    @property
    def entity_domain(self):
        """Entity domain for the entry."""
        return FAN

    @property
    def is_on(self) -> bool:
        """Return true if the fan is on."""
        workmode = self.get_state_attr("Workmode")
        if workmode is None:
            return False

        # Fan is off only when Workmode is PowerOff
        return str(workmode).lower() != "poweroff"

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if not self.is_on:
            return 0

        fanspeed = self.get_state_attr("Fanspeed")
        if fanspeed is None:
            return None

        try:
            speed_value = int(fanspeed)
            # Map speed value to percentage (0-100)
            min_speed, max_speed = self._speed_range
            if speed_value < min_speed:
                speed_value = min_speed
            if speed_value > max_speed:
                speed_value = max_speed

            # Create ordered list for percentage conversion
            speed_range = list(range(min_speed, max_speed + 1))
            percentage = ordered_list_item_to_percentage(speed_range, speed_value)
            return percentage

        except (ValueError, TypeError) as ex:
            _LOGGER.warning(
                "Could not convert Fanspeed value %s to percentage: %s", fanspeed, ex
            )
            return None

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        if not self.is_on:
            return None

        workmode = self.get_state_attr("Workmode")
        if workmode is None:
            return None

        # Return current mode if it's not PowerOff
        mode = str(workmode)
        return mode if mode.lower() != "poweroff" else None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        # Check if appliance is connected
        if not self.is_connected():
            connectivity_state = self.reported_state.get("connectivityState", "unknown")
            _LOGGER.warning(
                "Appliance %s is not connected (state: %s), cannot turn on fan",
                self.pnc_id,
                connectivity_state,
            )
            raise HomeAssistantError(
                f"Appliance is offline (current state: {connectivity_state}). "
                "Please check that the appliance is plugged in, has network connectivity and is connected to cloud services.",
                translation_domain=DOMAIN,
                translation_key="appliance_offline",
                translation_placeholders={"state": str(connectivity_state)},
            )

        # Determine target mode
        target_mode = None
        if preset_mode:
            target_mode = preset_mode
        else:
            # Use last known mode or default to Manual
            current_mode = self.get_state_attr("Workmode")
            if current_mode and str(current_mode).lower() != "poweroff":
                target_mode = str(current_mode)
            else:
                target_mode = "Manual"

        # Turn on with the target preset mode
        await self._send_workmode_command(target_mode)

        # Set speed if provided
        if percentage is not None:
            await self._set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        # Check if appliance is connected
        if not self.is_connected():
            connectivity_state = self.reported_state.get("connectivityState", "unknown")
            _LOGGER.warning(
                "Appliance %s is not connected (state: %s), cannot turn off fan",
                self.pnc_id,
                connectivity_state,
            )
            raise HomeAssistantError(
                f"Appliance is offline (current state: {connectivity_state}). "
                "Please check that the appliance is plugged in, has network connectivity and is connected to cloud services.",
                translation_domain=DOMAIN,
                translation_key="appliance_offline",
                translation_placeholders={"state": str(connectivity_state)},
            )

        # Set Workmode to PowerOff
        await self._send_workmode_command("PowerOff")

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        # Check if appliance is connected
        if not self.is_connected():
            connectivity_state = self.reported_state.get("connectivityState", "unknown")
            _LOGGER.warning(
                "Appliance %s is not connected (state: %s), cannot set fan speed",
                self.pnc_id,
                connectivity_state,
            )
            raise HomeAssistantError(
                f"Appliance is offline (current state: {connectivity_state}). "
                "Please check that the appliance is plugged in, has network connectivity and is connected to cloud services.",
                translation_domain=DOMAIN,
                translation_key="appliance_offline",
                translation_placeholders={"state": str(connectivity_state)},
            )

        if percentage == 0:
            await self.async_turn_off()
            return

        # Turn on if currently off
        if not self.is_on:
            # First turn on to Manual mode (or preserve last mode)
            current_mode = self.get_state_attr("Workmode")
            if not current_mode or str(current_mode).lower() == "poweroff":
                await self._send_workmode_command("Manual")

        await self._set_percentage(percentage)

    async def _set_percentage(self, percentage: int) -> None:
        """Internal method to set fan speed percentage."""
        # Convert percentage to speed value
        min_speed, max_speed = self._speed_range
        speed_range = list(range(min_speed, max_speed + 1))

        try:
            speed_value = percentage_to_ordered_list_item(speed_range, percentage)
        except ValueError:
            _LOGGER.warning(
                "Invalid percentage %s for speed range %s", percentage, speed_range
            )
            return

        # Get the Fanspeed capability for the appliance
        fanspeed_cap = self.get_capability("Fanspeed")
        if not fanspeed_cap:
            _LOGGER.error("Fanspeed capability not found for appliance %s", self.pnc_id)
            return

        # Send command to set fan speed
        await self._send_command("Fanspeed", speed_value, fanspeed_cap)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        # Check if appliance is connected
        if not self.is_connected():
            connectivity_state = self.reported_state.get("connectivityState", "unknown")
            _LOGGER.warning(
                "Appliance %s is not connected (state: %s), cannot set preset mode",
                self.pnc_id,
                connectivity_state,
            )
            raise HomeAssistantError(
                f"Appliance is offline (current state: {connectivity_state}). "
                "Please check that the appliance is plugged in, has network connectivity and is connected to cloud services.",
                translation_domain=DOMAIN,
                translation_key="appliance_offline",
                translation_placeholders={"state": str(connectivity_state)},
            )

        if preset_mode not in self._preset_modes:
            _LOGGER.warning(
                "Invalid preset mode %s. Available modes: %s",
                preset_mode,
                self._preset_modes,
            )
            raise HomeAssistantError(
                f"Invalid preset mode '{preset_mode}'. Available modes: {', '.join(self._preset_modes)}",
                translation_domain=DOMAIN,
                translation_key="invalid_preset_mode",
                translation_placeholders={
                    "mode": preset_mode,
                    "modes": ", ".join(self._preset_modes),
                },
            )

        await self._send_workmode_command(preset_mode)

    async def _send_workmode_command(self, mode: str) -> None:
        """Send Workmode command to appliance."""
        workmode_cap = self.get_capability("Workmode")
        if not workmode_cap:
            _LOGGER.error("Workmode capability not found for appliance %s", self.pnc_id)
            return

        await self._send_command("Workmode", mode, workmode_cap)

    async def _send_command(
        self, attr_name: str, value: Any, capability: dict[str, Any]
    ) -> None:
        """Send command to appliance."""
        client: ElectroluxApiClient = self.api

        # Use dynamic capability-based value formatting
        command_value = format_command_for_appliance(capability, attr_name, value)

        command: dict[str, Any]
        if not self.is_dam_appliance:
            # Legacy appliances: only wrap under entity_source when attr_name is NOT
            # itself a top-level capability. This handles namespace sub-keys like
            # "upperOven/executeCommand" (entity_source="upperOven", attr_name not top-level)
            # vs. "Workmode/fan" (entity_source="Workmode" IS a top-level flat capability,
            # so send {"Workmode": mode} instead of {"Workmode": {"Workmode": mode}}).
            if self.entity_source and not self.get_capability(attr_name):
                command = {self.entity_source: {attr_name: command_value}}
            else:
                command = {attr_name: command_value}
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
                        attr_name: command_value,
                    },
                }
            elif not self.get_capability(attr_name):
                command = {self.entity_source: {attr_name: command_value}}
            else:
                command = {attr_name: command_value}
        else:
            command = {attr_name: command_value}

        # Wrap DAM commands in the required format
        if self.is_dam_appliance:
            command = {"commands": [command]}

        _LOGGER.debug(
            "Electrolux fan sending command for %s: %s", attr_name, command_value
        )

        try:
            await execute_command_with_error_handling(
                client, self.pnc_id, command, attr_name, _LOGGER, capability
            )
        except AuthenticationError as auth_ex:
            # Handle authentication errors by triggering reauthentication
            coordinator: ElectroluxCoordinator = self.coordinator  # type: ignore[assignment]
            await coordinator.handle_authentication_error(auth_ex)
            raise
        except Exception:
            # Re-raise any errors from execute_command_with_error_handling
            raise

        # Optimistically update local state
        self._apply_optimistic_update(attr_name, command_value)
