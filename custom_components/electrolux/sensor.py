"""Switch platform for Electrolux."""

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SENSOR
from .entity import ElectroluxEntity
from .util import create_notification, get_capability, time_seconds_to_minutes

_LOGGER: logging.Logger = logging.getLogger(__package__)

FRIENDLY_NAMES = {
    "ovwater_tank_empty": "Water Tank Status",
    "foodProbeSupported": "Food Probe Support",
    "foodProbeInsertionState": "Food Probe",
    "ovcleaning_ended": "Cleaning Status",
    "ovfood_probe_end_of_cooking": "Probe End of Cooking",
    "connectivityState": "Connectivity State",
    "executionState": "Execution State",
    "applianceState": "Appliance State",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [
                entity for entity in appliance.entities if entity.entity_type == SENSOR
            ]
            _LOGGER.debug(
                "Electrolux add %d SENSOR entities to registry for appliance %s",
                len(entities),
                appliance_id,
            )
            async_add_entities(entities)
    return


class ElectroluxSensor(ElectroluxEntity, SensorEntity):

    @property
    def entity_domain(self) -> str:
        """Entity domain for the entry. Used for consistent entity_id."""
        return SENSOR

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        # Check for friendly name first using entity_name
        friendly_name = FRIENDLY_NAMES.get(self.entity_name)
        if friendly_name:
            return friendly_name
        # Fall back to catalog entry friendly name
        if self.catalog_entry and self.catalog_entry.friendly_name:
            return self.catalog_entry.friendly_name.capitalize()
        return self._name

    @property
    def suggested_display_precision(self) -> int | None:
        """Get the display precision."""
        if self.unit == UnitOfTemperature.CELSIUS:
            return 2
        if self.unit == UnitOfTemperature.FAHRENHEIT:
            return 2
        if self.unit == UnitOfVolume.LITERS:
            return 0
        if self.unit == UnitOfTime.SECONDS:
            return 0
        return None

    @property
    def native_value(self) -> datetime | str | int | float | None:
        """Return the state of the sensor."""
        value = self.extract_value()

        # Special handling for timeToEnd sensors: convert to timestamp for countdown display
        if self.entity_attr == "timeToEnd" or self.entity_attr.endswith("TimeToEnd"):
            if value is None or not isinstance(value, (int, float)):
                return None
            if value == -1 or value <= 0:
                return None

            # Check if appliance is in a state where timer is relevant
            # Only show countdown when RUNNING, PAUSED, or DELAYED_START
            appliance_state = self.reported_state.get("applianceState")
            if appliance_state not in ["RUNNING", "PAUSED", "DELAYED_START"]:
                # Appliance is stopped/idle/off - don't show countdown even if API has stale value
                return None

            # API returns seconds, calculate future timestamp for countdown
            return dt_util.now() + timedelta(seconds=value)

        # Special handling for runningTime: elapsed time sensor (counts up from start)
        if self.entity_attr == "runningTime":
            if value is None or not isinstance(value, (int, float)):
                return None
            if value == -1:  # Invalid/not set
                return None

            # Check if appliance is in a state where elapsed time is relevant
            # Only show elapsed time when RUNNING or PAUSED
            appliance_state = self.reported_state.get("applianceState")
            if appliance_state not in ["RUNNING", "PAUSED"]:
                # Appliance is stopped/idle/off - don't show elapsed time
                return None

            # Allow 0 (just started) and return seconds for duration display
            return value if value >= 0 else None

        # Special handling for sensors that should get live data instead of constants
        if self.entity_key in [
            "ovwater_tank_empty",
            "foodProbeSupported",
            "display_food_probe_temperature_c",
        ]:
            if self.entity_key == "ovwater_tank_empty":
                live_value = self.reported_state.get("waterTankEmpty")
                if live_value is not None:
                    # If value is STEAM_TANK_FULL, tank is not empty (Off)
                    value = live_value != "STEAM_TANK_FULL"
            elif self.entity_key == "display_food_probe_temperature_c":
                # Point to targetFoodProbeTemperatureC from reported properties
                live_value = self.reported_state.get("targetFoodProbeTemperatureC")
                if live_value is not None:
                    value = live_value
        elif get_capability(self.capability, "access") == "constant":
            default_value = get_capability(self.capability, "default")
            # Type narrow: only assign if it's not a dict
            if default_value is not None and not isinstance(default_value, dict):
                value = default_value

        # Use default value if no value is available from API
        if value is None:
            default_value = get_capability(self.capability, "default")
            if default_value is not None and not isinstance(default_value, dict):
                value = default_value

        if self.entity_attr == "alerts":
            if isinstance(value, list):
                value = len(value)
            else:
                value = 0
        elif value is not None and self.unit == UnitOfTime.MINUTES:
            # Handle timer/duration sensors
            if isinstance(value, (int, float)):
                # Return None for invalid/unset timers (-1 or 0)
                if value == -1 or value == 0:
                    return None
                # Convert to native units (minutes for time)
                converted = time_seconds_to_minutes(value)
                if converted is None:
                    _LOGGER.error(
                        "Unexpected None from time_seconds_to_minutes for %s", value
                    )
                    return None
                value = float(converted)
            else:
                _LOGGER.warning("Unexpected non-numeric value for time unit: %s", value)

        if self.catalog_entry and self.catalog_entry.value_mapping:
            # Electrolux presents as string but returns an int
            # the mapping entry allows us to correctly display this to the frontend
            mapping = self.catalog_entry.value_mapping
            _LOGGER.debug("Mapping %s: %s to %s", self.json_path, value, mapping)
            if value in mapping:
                value = mapping.get(value, value)
        if isinstance(value, str):
            if "_" in value:
                value = value.replace("_", " ")
            value = value.title()

        # If we still don't have a value, return None
        if value is None:
            return None

        # Ensure return type is str | int | float | None
        if value is not None and not isinstance(value, (str, int, float)):
            value = str(value)

        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return unit of measurement."""
        return self.unit

    @property
    def suggested_unit_of_measurement(self) -> str | None:
        """Return suggested unit of measurement."""
        return self.unit

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        if self.entity_attr == "alerts":
            alert_types = self.capability.get("values", {})
            # default is nullable - set a value for display to user
            alert_types = {key: "OFF" for key in alert_types}
            if current_alerts := self.extract_value():
                if isinstance(current_alerts, list):
                    for alert in current_alerts:
                        if isinstance(alert, dict):
                            name = alert.get("code", "Unknown")
                            severity = alert.get("severity", "Alert")
                            status = alert.get("acknowledgeStatus", "")
                            alert_types[name] = f"{severity}-{status}"
                            create_notification(
                                self.hass,
                                self.config_entry,
                                alert_name=name,
                                alert_severity=severity,
                                alert_status=status,
                                title=self.name,
                            )
            return alert_types
        return {}
