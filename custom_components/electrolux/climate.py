"""Climate platform for Electrolux."""

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CLIMATE, DOMAIN
from .entity import ElectroluxEntity
from .util import execute_command_with_error_handling, format_command_for_appliance

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure climate platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if appliances := coordinator.data.get("appliances", None):
        entities = []
        for appliance_id, appliance in appliances.appliances.items():
            # Create climate entities for air conditioners
            if appliance.appliance_type == "AC":
                climate_entity = ElectroluxClimate(appliance, coordinator)
                entities.append(climate_entity)
                _LOGGER.debug(
                    "Electrolux created CLIMATE entity for appliance %s",
                    appliance_id,
                )
        async_add_entities(entities)
    return


class ElectroluxClimate(ElectroluxEntity, ClimateEntity):
    """Electrolux climate class."""

    def __init__(self, *args, **kwargs):
        """Initialize the climate entity."""
        super().__init__(*args, **kwargs)
        self._enable_turn_on_off_backwards_compatibility = False

    @property
    def entity_domain(self):
        """Entity domain for the entry. Used for consistent entity_id."""
        return CLIMATE

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        # For air conditioners, assume these features are supported
        # In a real implementation, this could check the appliance capabilities
        return (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.SWING_MODE
        )

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        # Check temperature representation setting
        temp_rep = self.get_state_attr("temperatureRepresentation")
        if temp_rep == "FAHRENHEIT":
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        # Try Celsius first
        value = self.get_state_attr("ambientTemperatureC")
        if value is not None:
            return float(value)
        # Try Fahrenheit
        value = self.get_state_attr("ambientTemperatureF")
        if value is not None:
            return float(value)
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        # Try Celsius first
        value = self.get_state_attr("targetTemperatureC")
        if value is not None:
            return float(value)
        # Try Fahrenheit
        value = self.get_state_attr("targetTemperatureF")
        if value is not None:
            return float(value)
        return None

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach."""
        return None

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach."""
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current operation mode."""
        # Check appliance state first
        state_value = self.get_state_attr("applianceState")
        if state_value == "OFF":
            return HVACMode.OFF

        # Check mode
        mode_value = self.get_state_attr("mode")
        if mode_value:
            mode_mapping = {
                "AUTO": HVACMode.AUTO,
                "COOL": HVACMode.COOL,
                "HEAT": HVACMode.HEAT,
                "DRY": HVACMode.DRY,
                "FANONLY": HVACMode.FAN_ONLY,
            }
            return mode_mapping.get(str(mode_value).upper(), HVACMode.AUTO)

        return HVACMode.AUTO

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available operation modes."""
        modes = [HVACMode.OFF]

        # Get available modes from appliance capabilities
        mode_capability = self.capability.get("mode", {})
        values = mode_capability.get("values", {})
        if values:
            mode_mapping = {
                "AUTO": HVACMode.AUTO,
                "COOL": HVACMode.COOL,
                "HEAT": HVACMode.HEAT,
                "DRY": HVACMode.DRY,
                "FANONLY": HVACMode.FAN_ONLY,
            }
            for mode_key in values.keys():
                if mode_key.upper() in mode_mapping:
                    modes.append(mode_mapping[mode_key.upper()])

        return modes

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation."""
        # Check appliance state
        state_value = self.get_state_attr("applianceState")
        if state_value:
            state_str = str(state_value).upper()
            if state_str in ["RUNNING", "COOLING", "HEATING"]:
                return (
                    HVACAction.COOLING
                    if self.hvac_mode == HVACMode.COOL
                    else HVACAction.HEATING
                )
            elif state_str == "IDLE":
                return HVACAction.IDLE
            elif state_str == "OFF":
                return HVACAction.OFF

        return None

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        value = self.get_state_attr("fanSpeedSetting")
        if value:
            return str(value).lower()
        return None

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes."""
        # Get available fan modes from appliance capabilities
        fan_capability = self.capability.get("fanSpeedSetting", {})
        values = fan_capability.get("values", {})
        if values:
            return [str(mode).lower() for mode in values.keys()]
        return None

    @property
    def swing_mode(self) -> str | None:
        """Return the swing setting."""
        value = self.get_state_attr("verticalSwing")
        if value:
            return str(value).lower()
        return None

    @property
    def swing_modes(self) -> list[str] | None:
        """Return the list of available swing modes."""
        # Get available swing modes from appliance capabilities
        swing_capability = self.capability.get("verticalSwing", {})
        values = swing_capability.get("values", {})
        if values:
            return [str(mode).lower() for mode in values.keys()]
        return None

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        # Get temperature limits from appliance capabilities
        temp_capability = self.capability.get("targetTemperatureC", {})
        min_val = temp_capability.get("min")
        if min_val is not None:
            return float(min_val)
        return 16.0  # Default minimum

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        # Get temperature limits from appliance capabilities
        temp_capability = self.capability.get("targetTemperatureC", {})
        max_val = temp_capability.get("max")
        if max_val is not None:
            return float(max_val)
        return 30.0  # Default maximum

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        # Determine which temperature attribute to use
        temp_attr = (
            "targetTemperatureC"
            if self.temperature_unit == UnitOfTemperature.CELSIUS
            else "targetTemperatureF"
        )

        await self._send_command(temp_attr, temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            # Turn off the device using executeCommand
            await self._send_command("executeCommand", "OFF")
            return

        # Turn on if off using executeCommand
        await self._send_command("executeCommand", "ON")

        # Set the mode
        mode_mapping = {
            HVACMode.AUTO: "AUTO",
            HVACMode.COOL: "COOL",
            HVACMode.HEAT: "HEAT",
            HVACMode.DRY: "DRY",
            HVACMode.FAN_ONLY: "FANONLY",
        }

        if hvac_mode in mode_mapping:
            await self._send_command("mode", mode_mapping[hvac_mode])

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        await self._send_command("fanMode", fan_mode.upper())

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing mode."""
        await self._send_command("swingMode", swing_mode.upper())

    async def _send_command(self, attr: str, value: Any) -> None:
        """Send a command to the appliance."""
        # Note: Air conditioners typically don't have remote control enable/disable
        # functionality like ovens, so we skip this check for climate entities
        # if not self.is_remote_control_enabled():
        #     _LOGGER.warning(
        #         "Remote control is disabled for appliance %s, cannot execute command for %s",
        #         self.pnc_id,
        #         attr,
        #     )
        #     raise HomeAssistantError(
        #         "Remote control is disabled for this appliance. Please check the appliance settings."
        #     )

        client = self.api

        # Format the command value
        command_value = format_command_for_appliance(self.capability, attr, value)

        command: dict[str, Any]
        if not self.is_dam_appliance:
            # Legacy appliances: simple top-level property
            command = {attr: command_value}
        else:
            # DAM appliances: wrapped in commands array
            command = {
                "commands": [
                    {self.entity_source or "airConditioner": {attr: command_value}}
                ]
            }

        _LOGGER.debug("Electrolux climate command %s", command)

        try:
            await execute_command_with_error_handling(
                client, self.pnc_id, command, attr, _LOGGER, self.capability
            )
        except Exception as ex:
            _LOGGER.error("Electrolux climate command failed for %s: %s", attr, ex)
            raise
