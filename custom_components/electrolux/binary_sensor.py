"""Binary sensor platform for Electrolux."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BINARY_SENSOR, DOMAIN
from .entity import ElectroluxEntity
from .util import get_capability, string_to_boolean

_LOGGER: logging.Logger = logging.getLogger(__package__)


def infer_boolean_from_enum(value: str) -> bool:
    """Infer boolean state from appliance-specific enum values.

    This handles binary sensor values that aren't covered by the generic
    string_to_boolean() function. Uses common patterns in appliance enums.

    Args:
        value: The string value to interpret

    Returns:
        True for "positive" states, False for "negative" states

    Examples:
        "INSERTED" → True, "NOT_INSERTED" → False
        "STEAM_TANK_FULL" → True, "STEAM_TANK_EMPTY" → False
        "CONNECTED" → True, "DISCONNECTED" → False
    """
    normalized = value.upper().replace("_", " ")

    # Negative patterns (False states)
    negative_patterns = [
        "NOT ",
        "NO ",
        " EMPTY",
        "DISCONNECTED",
        "DISABLED",
        "UNAVAILABLE",
    ]

    for pattern in negative_patterns:
        if pattern in normalized:
            return False

    # Positive patterns (True states)
    positive_patterns = [
        "INSERT",  # Matches INSERTED, INSERTION, etc.
        "INSTALL",  # Matches INSTALLED, INSTALLATION, etc.
        "FULL",
        "CONNECT",  # Matches CONNECTED, CONNECTION, etc.
        "ENABLE",  # Matches ENABLED, etc.
        "AVAILABLE",
        "DETECT",  # Matches DETECTED, DETECTION, etc.
    ]

    for pattern in positive_patterns:
        if pattern in normalized:
            return True

    # Default: treat as True if no pattern matches (safer for binary sensors)
    return True


FRIENDLY_NAMES = {
    "ovwater_tank_empty": "Water Tank Status",
    "foodProbeInsertionState": "Food Probe",
    "ovcleaning_ended": "Cleaning Status",
    "ovfood_probe_end_of_cooking": "Probe End of Cooking",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [
                entity
                for entity in appliance.entities
                if entity.entity_type == BINARY_SENSOR
            ]
            _LOGGER.debug(
                "Electrolux add %d BINARY_SENSOR entities to registry for appliance %s",
                len(entities),
                appliance_id,
            )
            async_add_entities(entities)
    return


class ElectroluxBinarySensor(ElectroluxEntity, BinarySensorEntity):
    """Electrolux binary_sensor class."""

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        # Check for friendly name first using entity_name
        friendly_name = FRIENDLY_NAMES.get(self.entity_name)
        if friendly_name:
            return friendly_name
        # Fall back to catalog entry friendly name
        if self.catalog_entry and self.catalog_entry.friendly_name:
            return self.catalog_entry.friendly_name.capitalize()
        return self._name

    @property
    def entity_domain(self):
        """Entity domain for the entry. Used for consistent entity_id."""
        return BINARY_SENSOR

    @property
    def invert(self) -> bool:
        """Determine if the value returned for the entity needs to be reversed."""
        if self.catalog_entry:
            return self.catalog_entry.state_invert
        return False

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        value = self.extract_value()

        # Special handling for cleaning and probe end sensors
        if self.entity_name in ["ovcleaning_ended", "ovfood_probe_end_of_cooking"]:
            # Check processPhase - return On if STOPPED (process completed)
            process_phase = self.reported_state.get("processPhase")
            if process_phase == "STOPPED":
                value = True  # On when process has stopped/completed
            else:
                value = False  # Off otherwise

        if get_capability(self.capability, "access") == "constant":
            default_value = get_capability(self.capability, "default")
            # Type narrow: only assign if it's not a dict
            if default_value is not None and not isinstance(default_value, dict):
                value = default_value
        if isinstance(value, str):
            # Try generic string-to-boolean conversion first
            # When fallback=True (default), unrecognized strings return the original value
            converted = string_to_boolean(value, fallback=True)
            if isinstance(converted, bool):
                # string_to_boolean recognized it - use the result
                value = converted
            else:
                # string_to_boolean returned the fallback value (original string)
                # Try appliance-specific enum inference
                value = infer_boolean_from_enum(value)
        if value is None:
            if self.catalog_entry and self.catalog_entry.state_mapping:
                mapping = self.catalog_entry.state_mapping
                value = self.get_state_attr(mapping)

        # If we still don't have a value, return False
        if value is None:
            return False if not self.invert else True

        return bool(not value if self.invert else value)
