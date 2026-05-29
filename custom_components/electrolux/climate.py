"""Climate platform for Electrolux."""

import contextlib
import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CLIMATE
from .entity import ElectroluxEntity
from .util import execute_command_with_error_handling, format_command_for_appliance

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure climate platform."""
    coordinator = entry.runtime_data
    if appliances := coordinator.data.get("appliances", None):
        entities = []
        for appliance_id, appliance in appliances.appliances.items():
            if appliance.appliance_type in (
                "AC",
                "CA",
                "Azul",
                "Panther",
                "Bogong",
                "Telica",
            ):
                capabilities_dict = {}
                if appliance.data and hasattr(appliance.data, "capabilities"):
                    all_caps = appliance.data.capabilities or {}
                    climate_attrs = [
                        "mode",
                        "fanSpeedSetting",
                        "fanMode",
                        "verticalSwing",
                        "horizontalSwing",
                        "swingMode",
                        "targetTemperatureC",
                        "targetTemperatureF",
                        "executeCommand",
                    ]
                    for attr in climate_attrs:
                        if attr in all_caps:
                            capabilities_dict[attr] = all_caps[attr]

                climate_entity = ElectroluxClimate(
                    coordinator=coordinator,
                    name=appliance.name,
                    config_entry=entry,
                    pnc_id=appliance.pnc_id,
                    entity_type=CLIMATE,
                    entity_name="climate",
                    entity_attr="climate",
                    entity_source=None,
                    capability=capabilities_dict,
                    unit=None,
                    device_class=None,
                    entity_category=None,
                    icon="mdi:air-conditioner",
                    catalog_entry=None,
                )
                entities.append(climate_entity)
                _LOGGER.debug(
                    "Electrolux created CLIMATE entity for appliance %s with capabilities: %s",
                    appliance_id,
                    list(capabilities_dict.keys()),
                )
        async_add_entities(entities)
    return


class ElectroluxClimate(ElectroluxEntity, ClimateEntity, RestoreEntity):
    """Electrolux climate class."""

    def __init__(
        self,
        coordinator,
        name: str,
        config_entry,
        pnc_id: str,
        entity_type,
        entity_name,
        entity_attr: str,
        entity_source,
        capability: dict,
        unit: str | None,
        device_class,
        entity_category,
        icon: str,
        catalog_entry=None,
    ):
        """Initialize the climate entity."""
        super().__init__(
            coordinator=coordinator,
            name=name,
            config_entry=config_entry,
            pnc_id=pnc_id,
            entity_type=entity_type,
            entity_name=entity_name,
            entity_attr=entity_attr,
            entity_source=entity_source,
            capability=capability,
            unit=unit,
            device_class=device_class,
            entity_category=entity_category,
            icon=icon,
            catalog_entry=catalog_entry,
        )
        self._enable_turn_on_off_backwards_compatibility = False
        self._last_user_temperature: float | None = None

        # Determine temperature unit once from capabilities (static — never changes at runtime).
        # Prefer Celsius; fall back to Fahrenheit if only F is in capabilities.
        if "targetTemperatureC" in capability:
            self._attr_temperature_unit = UnitOfTemperature.CELSIUS
            self._temp_suffix = "C"
        elif "targetTemperatureF" in capability:
            self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
            self._temp_suffix = "F"
        else:
            # No explicit temperature capability found — default to Celsius
            self._attr_temperature_unit = UnitOfTemperature.CELSIUS
            self._temp_suffix = "C"

    async def async_added_to_hass(self) -> None:
        """Restore last user temperature from prior HA state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            if (temp := last_state.attributes.get("last_user_temperature")) is not None:
                with contextlib.suppress(ValueError, TypeError):
                    self._last_user_temperature = float(temp)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Persist last user temperature so RestoreEntity can recover it."""
        attrs: dict[str, Any] = {}
        if self._last_user_temperature is not None:
            attrs["last_user_temperature"] = self._last_user_temperature
        return attrs

    @property
    def entity_domain(self):
        """Entity domain for the entry. Used for consistent entity_id."""
        return CLIMATE

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Climate entity becomes unavailable when disconnected because hvac_mode
        cannot return None (HA platform requirement), and we cannot determine
        the actual mode without connectivity.
        """
        if not self.is_connected():
            return False
        return super().available

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.SWING_MODE
        )
        if "horizontalSwing" in self.capability:
            features |= ClimateEntityFeature.SWING_HORIZONTAL_MODE
        return features

    @property
    def swing_horizontal_mode(self) -> str | None:
        """Return the horizontal swing setting."""
        value = self.get_state_attr("horizontalSwing")
        if value:
            return str(value).lower()
        return None

    @property
    def swing_horizontal_modes(self) -> list[str] | None:
        """Return the list of available horizontal swing modes."""
        swing_capability = self.capability.get("horizontalSwing", {})
        values = swing_capability.get("values", {})
        if values:
            return [str(mode).lower() for mode in values.keys()]
        return None

    async def async_set_swing_horizontal_mode(self, swing_mode: str) -> None:
        """Set new target horizontal swing mode."""
        await self._send_command("horizontalSwing", swing_mode.upper())

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement.

        Determined once at init from capabilities — C if targetTemperatureC is
        present, F if only targetTemperatureF is present. Never changes at runtime
        so HA conversion is always clean and correct regardless of the
        temperatureRepresentation select entity value.
        """
        return self._attr_temperature_unit

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        value = self.get_state_attr(f"ambientTemperature{self._temp_suffix}")
        if value is not None:
            return round(float(value))
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        value = self.get_state_attr(f"targetTemperature{self._temp_suffix}")
        if value is not None:
            return round(float(value))
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
        """Return current HVAC mode.

        applianceState=Off reliably means the unit is powered off (confirmed via
        live testing: physical remote off → applianceState=Off; all active modes
        including fan_only keep applianceState=Running). When the physical remote
        powers off the unit, the device does NOT update `mode` to OFF — it retains
        the last active mode. Checking applianceState first handles that case.
        """
        appliance_state = self.get_state_attr("applianceState")
        if appliance_state and str(appliance_state).upper() == "OFF":
            return HVACMode.OFF

        mode_value = self.get_state_attr("mode")
        if not mode_value:
            return HVACMode.OFF

        mode_str = str(mode_value).upper()

        if mode_str == "OFF":
            return HVACMode.OFF

        mode_mapping = {
            "AUTO": HVACMode.AUTO,
            "COOL": HVACMode.COOL,
            "HEAT": HVACMode.HEAT,
            "DRY": HVACMode.DRY,
            "FANONLY": HVACMode.FAN_ONLY,
        }

        return mode_mapping.get(mode_str, HVACMode.AUTO)

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
        temp_capability = self.capability.get(
            f"targetTemperature{self._temp_suffix}", {}
        )
        min_val = temp_capability.get("min")
        if min_val is not None:
            return float(min_val)
        return 60.0 if self._temp_suffix == "F" else 16.0

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        temp_capability = self.capability.get(
            f"targetTemperature{self._temp_suffix}", {}
        )
        max_val = temp_capability.get("max")
        if max_val is not None:
            return float(max_val)
        return 86.0 if self._temp_suffix == "F" else 30.0

    @property
    def target_temperature_step(self) -> float:
        """Return the supported step of target temperature."""
        temp_capability = self.capability.get(
            f"targetTemperature{self._temp_suffix}", {}
        )
        step = temp_capability.get("step")
        if step is not None:
            return float(step)
        return 1.0  # Default to 1 degree steps (not 0.5 which HA default)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature.

        Guard for off-state: the Electrolux API returns HTTP 500 when a
        combined power-on + set-temperature command is sent in a single call.
        If the appliance is currently off, split into sequential commands
        (power on via set_hvac_mode, which re-applies the cached temperature)
        or refuse if no hvac_mode was supplied.

        ``_last_user_temperature`` is only updated after the underlying command
        succeeds — a failed API call must not pollute the cache that #48's
        re-apply path reads back.
        """
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        hvac_mode = kwargs.get("hvac_mode")
        new_temp = float(temperature)

        if self.hvac_mode == HVACMode.OFF:
            if hvac_mode is None:
                raise HomeAssistantError(
                    "Cannot set temperature while appliance is off"
                )
            # async_set_hvac_mode reads _last_user_temperature mid-call and
            # re-applies it after powering on, so the new value must be in
            # place before we await. The pre-write/rollback is asymmetric with
            # the on-path below (which writes after success); it exists solely
            # to make the cache atomic with that internal read. Note that
            # rollback only restores cache coherence — it cannot undo any
            # partial hardware state if async_set_hvac_mode fails mid-sequence.
            cached_temp = self._last_user_temperature
            self._last_user_temperature = new_temp
            try:
                await self.async_set_hvac_mode(hvac_mode)
            except Exception:
                self._last_user_temperature = cached_temp
                raise
            return

        await self._send_command(f"targetTemperature{self._temp_suffix}", new_temp)
        self._last_user_temperature = new_temp

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""

        # OFF → send OFF command
        if hvac_mode == HVACMode.OFF:
            await self._send_command("executeCommand", "OFF")
            self._apply_optimistic_update("mode", "OFF")
            return

        # Turn on first
        await self._send_command("executeCommand", "ON")

        mode_mapping = {
            HVACMode.AUTO: "AUTO",
            HVACMode.COOL: "COOL",
            HVACMode.HEAT: "HEAT",
            HVACMode.DRY: "DRY",
            HVACMode.FAN_ONLY: "FANONLY",
        }

        if hvac_mode in mode_mapping:
            mode_str = mode_mapping[hvac_mode]
            await self._send_command("mode", mode_str)
            self._apply_optimistic_update("mode", mode_str)

        # Re-apply last user temperature — device resets to min on power-off.
        if self._last_user_temperature is not None:
            temp_attr = f"targetTemperature{self._temp_suffix}"
            await self._send_command(temp_attr, self._last_user_temperature)
            self._apply_optimistic_update(temp_attr, self._last_user_temperature)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        await self._send_command("fanSpeedSetting", fan_mode.upper())

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing mode."""
        await self._send_command("verticalSwing", swing_mode.upper())

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
            # Legacy appliances: send as top-level property, but respect entity_source
            # when the capability key has a slash.
            if self.entity_source:
                command = {self.entity_source: {attr: command_value}}
            else:
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

            # Optimistically update local state using base class helper method
            self._apply_optimistic_update(attr, command_value)

        except Exception as ex:
            _LOGGER.error("Electrolux climate command failed for %s: %s", attr, ex)
            raise
