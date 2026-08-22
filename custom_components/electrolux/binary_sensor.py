"""Binary sensor platform for Electrolux."""

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BINARY_SENSOR, DOMAIN
from .coordinator import ElectroluxCoordinator
from .entity import ElectroluxEntity
from .util import get_capability, string_to_boolean

_LOGGER: logging.Logger = logging.getLogger(__package__)
PARALLEL_UPDATES = 0


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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure binary sensor platform."""
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        ElectroluxCloudApiBinarySensor(
            coordinator=coordinator,
            config_entry=entry,
        ),
        ElectroluxSseStreamBinarySensor(
            coordinator=coordinator,
            config_entry=entry,
        ),
    ]

    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            appliance_entities = [entity for entity in appliance.entities if entity.entity_type == BINARY_SENSOR]
            _LOGGER.debug(
                "Electrolux add %d BINARY_SENSOR entities to registry for appliance %s",
                len(appliance_entities),
                appliance_id,
            )
            entities.extend(appliance_entities)

    async_add_entities(entities)


class ElectroluxBinarySensor(ElectroluxEntity, BinarySensorEntity):
    """Electrolux binary_sensor class."""

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
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        # When offline, return None to show "unknown" (avoid showing stale data)
        if self.entity_attr != "connectivityState" and not self.is_connected():
            return None

        value = self.extract_value()

        # foodProbeSupported: infer from whether foodProbeInsertionState is reported.
        # The API never puts this constant key in the reported state; hardware support
        # is indicated by the presence of the foodProbeInsertionState sensor itself.
        if self.entity_attr == "foodProbeSupported":
            return "foodProbeInsertionState" in self.reported_state

        # Special handling for water tank empty sensor
        # Only handle the actual live waterTankEmpty sensor, not the fPPN notification ID
        if self.entity_key == "watertankempty":
            live_value = self.reported_state.get("waterTankEmpty")
            if live_value is not None:
                # For binary sensor, convert to boolean: empty when NOT full
                value = live_value != "STEAM_TANK_FULL"
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
            return bool(self.invert)

        return bool(not value if self.invert else value)


class _ElectroluxCloudDiagnosticBinarySensor(CoordinatorEntity[ElectroluxCoordinator], BinarySensorEntity):
    """Base class for Electrolux cloud diagnostic binary sensors."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ElectroluxCoordinator,
        config_entry: ConfigEntry,
        name: str,
        unique_suffix: str,
    ) -> None:
        """Initialize the diagnostic binary sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name="Electrolux Cloud",
            manufacturer="Electrolux",
            model="Developer Cloud API",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://developer.electrolux.one",
        )


class ElectroluxCloudApiBinarySensor(_ElectroluxCloudDiagnosticBinarySensor):
    """Binary sensor for Electrolux REST API gateway connectivity."""

    def __init__(
        self,
        coordinator: ElectroluxCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the API connectivity binary sensor."""
        super().__init__(coordinator, config_entry, name="API", unique_suffix="cloud_api")

    @property
    def is_on(self) -> bool:
        """Return True if REST API is connected."""
        return self.coordinator.api_connected

    @property
    def icon(self) -> str:
        """Return dynamic icon based on state."""
        return "mdi:cloud-check" if self.is_on else "mdi:cloud-alert"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic state attributes."""
        attrs: dict[str, Any] = {
            "endpoint": "api.developer.electrolux.one",
            "last_status_code": self.coordinator.last_api_status_code,
        }
        if self.coordinator.last_api_success_time > 0:
            attrs["last_success_time"] = datetime.fromtimestamp(
                self.coordinator.last_api_success_time, tz=UTC
            ).isoformat()
        if self.coordinator.last_api_error:
            attrs["last_error"] = self.coordinator.last_api_error
        return attrs


class ElectroluxSseStreamBinarySensor(_ElectroluxCloudDiagnosticBinarySensor):
    """Binary sensor for Electrolux live SSE event stream connectivity."""

    def __init__(
        self,
        coordinator: ElectroluxCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the SSE stream connectivity binary sensor."""
        super().__init__(coordinator, config_entry, name="Live Stream", unique_suffix="sse_stream")

    @property
    def is_on(self) -> bool:
        """Return True if SSE stream is connected."""
        return self.coordinator.sse_connected

    @property
    def icon(self) -> str:
        """Return dynamic icon based on state."""
        return "mdi:broadcast" if self.is_on else "mdi:broadcast-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic state attributes."""
        attrs: dict[str, Any] = {
            "endpoint": "live.eu.developer.electrolux.one",
            "connection_state": self.coordinator.sse_connection_state,
            "consecutive_drops": self.coordinator.consecutive_sse_drops,
            "backoff_seconds": self.coordinator.current_sse_backoff_seconds,
        }
        if self.coordinator.last_sse_event_time > 0:
            attrs["last_event_time"] = datetime.fromtimestamp(self.coordinator.last_sse_event_time, tz=UTC).isoformat()
        if self.coordinator.last_sse_disconnect_reason:
            attrs["disconnect_reason"] = self.coordinator.last_sse_disconnect_reason
        return attrs
