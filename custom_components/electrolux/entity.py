"""Entity platform for Electrolux."""

import asyncio
import hashlib
import logging
import time
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_API_KEY, DOMAIN
from .coordinator import ElectroluxCoordinator
from .model import ElectroluxDevice
from .models import Appliance, Appliances, ApplianceState
from .util import ElectroluxApiClient

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure entity platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [
                entity
                for entity in appliance.entities
                if entity.entity_type == "entity"
            ]

            # Filter out fPPN_ prefixed entities if a matching non-prefixed entity exists
            filtered_entities = []
            entity_attrs = {entity.entity_attr for entity in entities}

            for entity in entities:
                entity_attr_lower = entity.entity_attr.lower()
                # Skip fPPN prefixed entities if a matching non-prefixed entity exists
                if entity_attr_lower.startswith("fppn"):
                    base_attr = (
                        entity_attr_lower.replace("fppn_", "")
                        .replace("fppn", "")
                        .strip("_")
                    )
                    # Check if any non-fPPN version exists
                    has_matching_base = any(
                        other_attr.lower()
                        .replace("fppn_", "")
                        .replace("fppn", "")
                        .strip("_")
                        == base_attr
                        for other_attr in entity_attrs
                        if not other_attr.lower().startswith("fppn")
                    )
                    if has_matching_base:
                        _LOGGER.debug(
                            "Skipping duplicate fPPN entity %s for appliance %s (base entity exists)",
                            entity.entity_attr,
                            appliance_id,
                        )
                        continue

                filtered_entities.append(entity)

            entities = filtered_entities
            _LOGGER.debug(
                "Electrolux add %d entities to registry for appliance %s",
                len(entities),
                appliance_id,
            )
            # Register suggested object_ids so new installs get clean, slugified ids
            # while existing entities tracked by the entity registry (via unique_id)
            # are preserved.
            try:
                registry = er.async_get(hass)
                for entity in entities:
                    try:
                        brand = getattr(appliance, "brand", "") or ""
                        name = getattr(appliance, "name", "") or ""
                        source = entity.entity_source or ""
                        attr = entity.entity_attr or ""
                        object_id = "_".join(
                            part for part in [brand, name, source, attr] if part
                        )
                        object_id = slugify(object_id)
                        if not object_id:
                            fallback_parts = [entity.pnc_id]
                            if attr:
                                fallback_parts.append(str(attr))
                            object_id = (
                                slugify("_".join(fallback_parts)) or "electrolux_entity"
                            )
                        registry.async_get_or_create(
                            entity.entity_domain,
                            DOMAIN,
                            entity.unique_id,
                            suggested_object_id=object_id,
                            config_entry=entry,
                        )
                    except (
                        Exception
                    ):  # defensive: ensure entity creation still proceeds
                        _LOGGER.debug(
                            "Could not register suggested id for entity %s", entity
                        )
            except Exception:
                _LOGGER.debug(
                    "Entity registry unavailable, skipping suggested id registration"
                )

            async_add_entities(entities)


class ElectroluxEntity(CoordinatorEntity):
    """Class for Electorolux devices."""

    _attr_has_entity_name = True

    appliance_status: ApplianceState | dict[str, Any] | None

    def __init__(
        self,
        coordinator: ElectroluxCoordinator,
        name: str,
        config_entry,
        pnc_id: str,
        entity_type: Platform | None,
        entity_name,
        entity_attr: str,
        entity_source,
        capability: dict[str, Any],
        unit: str | None,
        device_class: Any,
        entity_category: EntityCategory,
        icon: str,
        catalog_entry: ElectroluxDevice | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.root_attribute = ["properties", "reported"]
        self.data: Appliances | None = None
        self.coordinator = coordinator
        self._cached_value: Any = None
        self._name = name
        self._icon = icon
        self._device_class = device_class
        self._entity_category = entity_category
        self._catalog_entry = catalog_entry
        self.api: ElectroluxApiClient = coordinator.api
        self.entity_name = entity_name
        self.entity_attr = entity_attr
        self.entity_type = entity_type
        self.entity_source = entity_source
        self.config_entry = config_entry
        self.pnc_id = pnc_id
        self.unit = unit
        self.capability = capability
        # Set entity_key for consistent FRIENDLY_NAMES lookup
        # Strip any 'fppn' prefix (with or without underscore) and make case-insensitive for robust matching
        entity_attr_lower = entity_attr.lower()
        if entity_attr_lower.startswith("fppn_"):
            self.entity_key = entity_attr_lower.replace("fppn_", "").strip("_")
        elif entity_attr_lower.startswith("fppn"):
            self.entity_key = entity_attr_lower.replace("fppn", "").strip("_")
        else:
            self.entity_key = entity_attr_lower.strip("_")
        # Do not force `entity_id` here. Home Assistant's entity registry
        # manages stable `entity_id` values based on `unique_id`.
        # Preserving or migrating existing entity_ids should be done
        # via the entity registry APIs during setup, not by assigning
        # `self.entity_id` here which can break users' automations.

        # Rate limiting for commands
        self._last_command_time: float = 0
        self._min_command_interval: float = 1.0  # 1 second minimum between commands

        _LOGGER.debug("Electrolux new entity %s for appliance %s", name, pnc_id)

    def setup(self, data: Appliances) -> None:
        """Initialize setup."""
        self.data = data

    @property
    def entity_domain(self) -> str:
        """Entity domain for the entry."""
        return "sensor"

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        # Use stable unique_id based on API key hash for consistent entity IDs
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
        return f"{api_key_hash}-{normalized_attr}-{self.entity_source or 'root'}-{self.pnc_id}"

    # NOTE: available property is intentionally not implemented
    # Reason: Setting available=False hides the entity value completely,
    # which is undesirable - we want users to see the last known state
    # even when the appliance is disconnected.
    #
    # If we need to show connection status, we should:
    # 1. Add a separate connection_state sensor
    # 2. Use entity attributes to show "Last updated: X minutes ago"
    # 3. Keep the entity available=True to preserve value visibility
    # @property
    # def available(self) -> bool:
    #     if (self._entity_category == EntityCategory.DIAGNOSTIC
    #             or self.entity_attr in ALWAYS_ENABLED_ATTRIBUTES):
    #         return True
    #     connection_state = self.get_connection_state()
    #     if connection_state and connection_state != "disconnected":
    #         return True
    #     return False

    @property
    def should_poll(self) -> bool:
        """Confirm if device should be polled."""
        return False

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # _LOGGER.debug("Electrolux entity got data %s", self.coordinator.data)
        if self.coordinator.data is None:
            return
        appliances = self.coordinator.data.get("appliances", None)
        if appliances is None:
            return
        self.appliance_status = appliances.get_appliance(self.pnc_id).state
        # Only clear cached value if reported value differs from cached value
        reported_value = self.extract_value()
        if self._cached_value is not None:
            if self._cached_value != reported_value:
                self._cached_value = None
        self.async_write_ha_state()

    def get_state_attr(self, path: str) -> str | None:
        """Return value of other appliance attributes.

        Used for the evaluation of state_mapping one property to another.
        """
        if "/" in path:
            if self.reported_state.get(path, None):
                return self.reported_state.get(path)
            source, attr = path.split("/")
            return self.reported_state.get(source, {}).get(attr, None)
        return self.reported_state.get(path, None)

    @property
    def reported_state(self) -> dict[str, Any]:
        """Return reported state of the appliance."""
        if self.appliance_status is None or not isinstance(self.appliance_status, dict):
            return {}

        return self.appliance_status.get("properties", {}).get("reported", {})

    @reported_state.setter
    def reported_state(self, value: dict[str, Any] | None) -> None:
        """Set reported state for testing purposes."""
        if not hasattr(self, "appliance_status") or not self.appliance_status:
            self.appliance_status = {"properties": {"reported": {}}}

        # Ensure properties structure exists
        if not isinstance(self.appliance_status, dict):
            self.appliance_status = {"properties": {"reported": {}}}
        elif "properties" not in self.appliance_status or not isinstance(
            self.appliance_status["properties"], dict
        ):
            self.appliance_status["properties"] = {"reported": {}}
        elif "reported" not in self.appliance_status["properties"] or not isinstance(
            self.appliance_status["properties"]["reported"], dict
        ):
            self.appliance_status["properties"]["reported"] = {}

        if value is None:
            self.appliance_status["properties"]["reported"] = {}
        else:
            self.appliance_status["properties"]["reported"] = value

    @property
    def is_dam_appliance(self) -> bool:
        """Return True if this is a DAM (One Connected Platform) appliance."""
        return self.pnc_id.startswith("1:")

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self.catalog_entry and self.catalog_entry.friendly_name:
            return self.catalog_entry.friendly_name.capitalize()
        return self._name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.is_remote_control_enabled()

    @property
    def icon(self) -> str | None:
        """Return the icon based on current selection."""
        # Check catalog entry first for static icon
        if self._catalog_entry and hasattr(self._catalog_entry, "entity_icon"):
            return self._catalog_entry.entity_icon

        # Check entity_icons_value_map from catalog for value-specific icons
        current_value = self.extract_value()
        if (
            self._catalog_entry
            and hasattr(self._catalog_entry, "entity_icons_value_map")
            and self._catalog_entry.entity_icons_value_map
            and current_value in self._catalog_entry.entity_icons_value_map
        ):
            return self._catalog_entry.entity_icons_value_map[current_value]

        # Check for value-specific icons in capability values
        if current_value is not None and self.capability.get("values"):
            value_data = self.capability["values"].get(str(current_value), {})
            if isinstance(value_data, dict) and "icon" in value_data:
                return value_data["icon"]

        # Default icon fallback
        return self._icon

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        # Use catalog entry value if available, otherwise default to True
        if self._catalog_entry:
            return self._catalog_entry.entity_registry_enabled_default
        return True

    # @property
    # def get_entity(self) -> ApplianceEntity:
    #     return self.get_appliance.get_entity(self.entity_type, self.entity_attr, self.entity_source, None)

    @property
    def get_appliance(self) -> Appliance:
        """Return the appliance device."""
        return self.coordinator.data["appliances"].get_appliance(self.pnc_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return identifiers of the device."""
        appliance = self.get_appliance
        model = appliance.model
        brand = appliance.brand or "Electrolux"
        name = appliance.name

        # Debug logging to see what information we have
        _LOGGER.debug(
            "Device info for appliance %s: name='%s', model='%s', brand='%s', appliance_type='%s'",
            self.pnc_id,
            name,
            model,
            brand,
            appliance.appliance_type,
        )

        # If model is "Unknown" or empty, try to get better info
        if not model or model == "Unknown":
            # Try to get appliance type from state
            appliance_type = appliance.appliance_type
            if appliance_type and appliance_type != "Unknown":
                model = str(appliance_type)
                _LOGGER.debug(
                    "Using appliance_type '%s' as model for %s",
                    appliance_type,
                    self.pnc_id,
                )
            else:
                # Use appliance name as last resort
                model = name or "Unknown Appliance"
                _LOGGER.debug(
                    "Using appliance name '%s' as model for %s", model, self.pnc_id
                )

        device_info: DeviceInfo = {
            "identifiers": {(DOMAIN, self.pnc_id)},
            "name": name or model,
            "model": model,
            "manufacturer": brand,
        }

        _LOGGER.debug("Final device_info for %s: %s", self.pnc_id, device_info)
        return device_info

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return entity category."""
        return self._entity_category

    @property
    def device_class(self) -> Any:
        """Return the device class of the sensor."""
        return self._device_class

    def extract_value(self) -> Any:
        """Return the appliance attributes of the entity."""
        # For constant access, return value from capability metadata
        if self.capability.get("access") == "constant":
            result: Any = self.capability.get("default")
            if result is not None:
                _LOGGER.debug(
                    "Extracted constant value for %s: %s", self.entity_attr, result
                )
                return result
            return None

        # For other access types, get from data
        value: dict[str, Any] | None = None
        if self.entity_source == "applianceInfo":
            if self.appliance_status and isinstance(self.appliance_status, dict):
                appliance_info = self.appliance_status.get("applianceInfo", {})
                if isinstance(appliance_info, dict):
                    value = appliance_info.get(self.entity_attr)
        else:
            # Check reported state first
            value = self.reported_state.get(self.entity_attr)
            if value is None and self.entity_source:
                # Handle nested entity_source in reported
                if "/" in self.entity_source:
                    parts = self.entity_source.split("/")
                    category = self.reported_state
                    for part in parts:
                        category = category.get(part, None)
                        if category is None:
                            break
                    if category and isinstance(category, dict):
                        value = cast(Any, category.get(self.entity_attr))  # type: ignore[assignment]
                else:
                    category = self.reported_state.get(self.entity_source, None)
                    if category and isinstance(category, dict):
                        value = category.get(self.entity_attr)
            if value is None:
                # Check appliance_status
                if self.appliance_status and isinstance(self.appliance_status, dict):
                    value = cast(Any, self.appliance_status.get(self.entity_attr))  # type: ignore[assignment]

        if value is not None:
            _LOGGER.debug("Extracted value for %s: %s", self.entity_attr, value)
        else:
            _LOGGER.debug(
                "No value found for entity %s (attr: %s, source: %s)",
                self.name,
                self.entity_attr,
                self.entity_source,
            )
        return value

    def update(self, appliance_status: ApplianceState | dict[str, Any]) -> None:
        """Update the appliance status."""
        # ApplianceState is a TypedDict that can be assigned to dict[str, Any]
        self.appliance_status = appliance_status
        # if self.hass:
        #     self.async_write_ha_state()

    @property
    def json_path(self) -> str | None:
        """Return the path to the entry."""
        if self.entity_source:
            return f"{self.entity_source}/{self.entity_attr}"
        return self.entity_attr

    def is_remote_control_enabled(self) -> bool:
        """Check if remote control is enabled for this appliance.

        Returns True if remote control status contains 'ENABLED'
        (including 'NOT_SAFETY_RELEVANT_ENABLED') or is None.
        """
        if not hasattr(self, "appliance_status") or not self.appliance_status:
            return False

        # Check for remoteControl in the appliance status
        remote_control_status = self.appliance_status.get("remoteControl")
        if remote_control_status is None:
            # Also check in properties.reported
            reported = self.appliance_status.get("properties", {}).get("reported", {})
            remote_control_status = reported.get("remoteControl")

        _LOGGER.debug(
            "Remote control status for appliance %s: %s",
            self.pnc_id,
            remote_control_status,
        )

        # Allow None as a valid enabled state (some appliances don't report remoteControl)
        if remote_control_status is None:
            return True

        if remote_control_status:
            result = "ENABLED" in str(remote_control_status) and "DISABLED" not in str(
                remote_control_status
            )
            _LOGGER.debug(
                "Remote control enabled check for %s: %s -> %s",
                self.pnc_id,
                remote_control_status,
                result,
            )
            return result

        # If no remote control status found, assume it's enabled
        return True

    @property
    def catalog_entry(self) -> ElectroluxDevice | None:
        """Return matched catalog entry."""
        return self._catalog_entry

    # @property
    # def extra_state_attributes(self) -> dict[str, Any]:
    #     """Return the state attributes of the sensor."""
    #     return {
    #         "Path": self.json_path,
    #         "entity_type": str(self.entity_type),
    #         "entity_category": str(self.entity_category),
    #         "device_class": str(self.device_class),
    #         "capability": str(self.capability),
    #     }

    async def _rate_limit_command(self) -> None:
        """Enforce minimum interval between commands."""
        now = time.time()
        time_since_last = now - self._last_command_time

        if time_since_last < self._min_command_interval:
            wait_time = self._min_command_interval - time_since_last
            _LOGGER.debug(
                "Rate limiting command for %s, waiting %.2fs",
                self.entity_attr,
                wait_time,
            )
            await asyncio.sleep(wait_time)

        self._last_command_time = time.time()
