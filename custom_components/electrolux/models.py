"""Models and types for Electrolux."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from .entity import ElectroluxEntity

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.button import ButtonDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import Platform, UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from .catalog_core import CATALOG_BASE, CATALOG_MODEL
from .const import (
    BINARY_SENSOR,
    BUTTON,
    CLIMATE,
    NUMBER,
    PLATFORMS,
    SELECT,
    SENSOR,
    STATIC_ATTRIBUTES,
    SWITCH,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


def deep_merge_dicts(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merge two dictionaries.
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


class ApplianceState(TypedDict, total=False):
    """TypedDict for appliance state structure."""

    properties: dict[str, Any]


class ApplianceData:
    """Class for appliance data from API."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get_category(self, key: str) -> str | None:
        """Get category for a key."""
        # Implement based on original logic, perhaps return key or something
        return self._data.get("category", {}).get(key)


class Appliance:
    """Define the Appliance Class.

    Note: pnc_id and appliance_id refer to the same thing:
    - pnc_id: Used internally (historical name)
    - appliance_id: Used in API calls (API name)
    Both represent the unique appliance identifier.
    """

    brand: str
    device: str
    entities: list[Any]
    coordinator: Any
    data: Any

    def __init__(
        self,
        coordinator: Any,
        name: str,
        pnc_id: str,
        brand: str,
        model: str,
        state: ApplianceState,
    ) -> None:
        """Initialize the appliance."""
        self.data = None
        self.coordinator = coordinator
        self.model = model
        self.pnc_id = pnc_id
        self.name = name
        self.brand = brand
        self.state: ApplianceState = state
        self.entities: list[Any] = []
        self._catalog_cache: dict[str, Any] | None = None

    @property
    def reported_state(self) -> dict[str, Any]:
        """Return the reported state of the appliance."""
        from typing import cast

        return (
            cast(dict[str, Any], self.state).get("properties", {}).get("reported", {})
        )

    @property
    def appliance_type(self) -> Any:
        """Return the reported type of the appliance.

        OV: Oven
        CR: Refrigerator
        WM: Washing Machine
        """
        from typing import cast

        return (
            cast(dict[str, Any], self.state)
            .get("applianceData", {})
            .get("applianceType")
        )

    def update(self, appliance_status: ApplianceState | dict[str, Any]) -> None:
        """Update appliance status."""
        from typing import cast

        self.state = cast(ApplianceState, appliance_status)
        self.initialize_constant_values()
        for entity in self.entities:
            entity.update(self.state)

    def initialize_constant_values(self) -> None:
        """Initialize constant values from catalog in reported_state."""
        if not self.reported_state:
            return

        # Initialize constant values from catalog
        for key, catalog_item in self.catalog.items():
            if (
                catalog_item.capability_info.get("access") == "constant"
                and catalog_item.capability_info.get("default") is not None
            ):
                # Only set if not already present in reported_state
                if key not in self.reported_state:
                    self.reported_state[key] = catalog_item.capability_info["default"]
                    _LOGGER.debug(
                        "Electrolux initialized constant value for %s: %s",
                        key,
                        catalog_item.capability_info["default"],
                    )

    @property
    def catalog(self) -> dict[str, Any]:
        """Return the defined catalog for the appliance."""
        # Return cached catalog if available
        if self._catalog_cache is not None:
            return self._catalog_cache

        from .catalog_core import CATALOG_BY_TYPE

        # Start with the base catalog
        new_catalog = copy.deepcopy(CATALOG_BASE)

        # Merge with appliance-type specific catalog if available
        appliance_type = self.appliance_type
        if appliance_type in CATALOG_BY_TYPE:
            type_catalog = CATALOG_BY_TYPE[appliance_type]
            for key, device in type_catalog.items():
                new_catalog[key] = device

        # Apply model-specific overrides if available
        if self.model in CATALOG_MODEL:
            model_catalog = CATALOG_MODEL[self.model]
            for key, device in model_catalog.items():
                new_catalog[key] = device

        # Cache and return
        self._catalog_cache = new_catalog
        return new_catalog

    def get_state(self, attr_name: str) -> dict[str, Any] | None:
        """Retrieve the start from self.reported_state using the attribute name.

        May contain slashes for nested keys.
        """

        keys = attr_name.split("/")
        result: dict[str, Any] | None = self.reported_state

        for key in keys:
            if not isinstance(result, dict):
                return None
            result = result.get(key)
            if result is None:
                return None

        return result if isinstance(result, dict) else None

    def update_reported_data(self, reported_data: dict[str, Any]) -> None:
        """Update the reported data."""
        _LOGGER.debug("Electrolux update reported data")
        try:
            # Handle incremental updates with "property" and "value" keys
            if "property" in reported_data and "value" in reported_data:
                property_name = reported_data["property"]
                property_value = reported_data["value"]
                _LOGGER.debug(
                    "Electrolux incremental update for property: %s",
                    property_name,
                )
                # Update the specific property in reported_state

                # HANDLE NESTED PROPERTIES
                if "/" in property_name:
                    # Handle nested path like "userSelections/program"
                    parts = property_name.split("/")
                    target = self.reported_state

                    # Navigate to the parent dictionary
                    for part in parts[:-1]:
                        if part not in target:
                            target[part] = {}
                        elif not isinstance(target[part], dict):
                            _LOGGER.warning(
                                "Cannot update nested property %s: parent %s is not a dict",
                                property_name,
                                part,
                            )
                            return
                        target = target[part]

                    # Set the final value
                    target[parts[-1]] = property_value
                else:
                    # Simple flat property update
                    self.reported_state[property_name] = property_value
            else:
                # Handle full state updates - preserve constant values
                # Store constant values before merge
                constant_values = {}
                for key, catalog_item in self.catalog.items():
                    if (
                        catalog_item.capability_info.get("access") == "constant"
                        and key in self.reported_state
                    ):
                        constant_values[key] = self.reported_state[key]

                # Perform the merge
                self.reported_state.update(
                    deep_merge_dicts(self.reported_state, reported_data)
                )

                # Restore constant values that may have been overwritten
                for key, value in constant_values.items():
                    if (
                        key not in reported_data
                    ):  # Only restore if not explicitly updated
                        self.reported_state[key] = value

            _LOGGER.debug("Electrolux updated reported data")
            for entity in self.entities:
                entity.update(self.state)

        except (KeyError, ValueError, TypeError, AttributeError) as ex:
            _LOGGER.error(
                "Data validation error updating reported data for %s: %s. Data: %s",
                self.pnc_id,
                ex,
                reported_data,
            )
        except Exception:
            _LOGGER.exception(
                "Unexpected error updating reported data for %s. Data: %s",
                self.pnc_id,
                reported_data,
            )

    def get_entity(self, capability: str) -> list[ElectroluxEntity]:
        """Return the entity."""
        entity_type = self.data.get_entity_type(capability)
        entity_name = self.data.get_entity_name(capability)
        entity_attr = self.data.get_entity_attr(capability)
        category = self.data.get_category(capability)
        capability_info = self.data.get_capability(capability)
        device_class = self.data.get_entity_device_class(capability)
        entity_category = None
        entity_icon = None
        unit = self.data.get_entity_unit(capability)
        display_name = self.data.get_sensor_name(capability)

        # get the item definition from the catalog
        catalog_item = self.catalog.get(capability, None)
        if catalog_item:
            # Check if catalog specifies a custom entity_source
            if catalog_item.capability_info.get("entity_source"):
                category = catalog_item.capability_info["entity_source"]
            if capability_info is None:
                capability_info = catalog_item.capability_info
                # For catalog-only entities, determine entity type from capability_info
                if entity_type is None and capability_info:
                    cap_type = capability_info.get("type")
                    access = capability_info.get("access", "read")
                    if cap_type == "climate":
                        entity_type = CLIMATE
                    elif cap_type in ("number", "int") and access in (
                        "readwrite",
                        "write",
                    ):
                        entity_type = NUMBER
                    elif cap_type == "temperature" and access in ("readwrite", "write"):
                        entity_type = NUMBER
                    elif cap_type == "boolean" and access == "readwrite":
                        entity_type = SWITCH
                    elif access == "read":
                        entity_type = SENSOR
            else:
                # Merge catalog capability_info into API capability_info
                capability_info.update(catalog_item.capability_info)

            device_class = catalog_item.device_class
            unit = catalog_item.unit
            entity_category = catalog_item.entity_category
            entity_icon = catalog_item.entity_icon

        # Ensure time entities have correct unit for conversion
        if not unit and entity_attr in ["startTime", "targetDuration"]:
            unit = UnitOfTime.SECONDS

        # override the api determined type by the catalog entity_type
        if isinstance(device_class, BinarySensorDeviceClass):
            entity_type = BINARY_SENSOR
        if isinstance(device_class, ButtonDeviceClass):
            entity_type = BUTTON
        if isinstance(device_class, NumberDeviceClass):
            entity_type = NUMBER
        if isinstance(device_class, SensorDeviceClass):
            entity_type = SENSOR
        if isinstance(device_class, SwitchDeviceClass):
            entity_type = SWITCH

        # override the api determined type by the catalog entity_platform
        if catalog_item and isinstance(catalog_item.entity_platform, Platform):
            entity_type = catalog_item.entity_platform

        _LOGGER.debug(
            "Electrolux get_entity. entity_type: %s entity_name: %s entity_attr: %s entity_source: %s capability: %s device_class: %s unit: %s, catalog: %s",
            entity_type,
            entity_name,
            entity_attr,
            category,
            capability_info,
            device_class,
            unit,
            catalog_item,
        )

        def electrolux_entity_factory(
            name: str,
            entity_type: Platform | None,
            entity_name: str,
            entity_attr: str,
            entity_source: str,
            capability: dict[str, Any] | None,
            unit: str | None,
            entity_category: EntityCategory | None,
            device_class: str | None,
            icon: str | None,
            catalog_entry: Any | None,
            commands: Any | None = None,
        ):
            from .binary_sensor import ElectroluxBinarySensor
            from .button import ElectroluxButton
            from .climate import ElectroluxClimate
            from .number import ElectroluxNumber
            from .select import ElectroluxSelect
            from .sensor import ElectroluxSensor
            from .switch import ElectroluxSwitch

            entity_classes = {
                BINARY_SENSOR: ElectroluxBinarySensor,
                BUTTON: ElectroluxButton,
                CLIMATE: ElectroluxClimate,
                NUMBER: ElectroluxNumber,
                SELECT: ElectroluxSelect,
                SENSOR: ElectroluxSensor,
                SWITCH: ElectroluxSwitch,
            }

            entity_class = entity_classes.get(entity_type) if entity_type else None

            if entity_class is None:
                _LOGGER.debug("Unknown entity type %s for %s", entity_type, name)
                raise ValueError(f"Unknown entity type: {entity_type}")

            entity_params = {
                "coordinator": self.coordinator,
                "config_entry": self.coordinator.config_entry,
                "pnc_id": self.pnc_id,
                "name": name,
                "entity_type": entity_type,
                "entity_name": entity_name,
                "entity_attr": entity_attr,
                "entity_source": entity_source,
                "capability": capability,
                "unit": unit,
                "entity_category": entity_category,
                "device_class": device_class,
                "icon": icon,
                "catalog_entry": catalog_entry,
            }

            if commands is None:
                return [entity_class(**entity_params)]

            entities: list[Any] = []
            # Replace entity name and icons for multi-entities attribute (one value = one entity)
            for command in commands:
                entity = {**entity_params, "val_to_send": command}
                if catalog_item:
                    if catalog_item.entity_value_named:
                        entity["name"] = command
                    if (
                        catalog_item.entity_icons_value_map
                        and catalog_item.entity_icons_value_map.get(command, None)
                    ):
                        entity["icon"] = catalog_item.entity_icons_value_map.get(
                            command
                        )
                # Instanciate the new entity and append it
                entities.append(entity_class(**entity))
            return entities

        if entity_type in PLATFORMS:
            commands = (
                capability_info.get("values", {})
                if entity_type == BUTTON and capability_info
                else None
            )
            return electrolux_entity_factory(
                name=display_name,
                entity_type=entity_type,
                entity_name=entity_name,
                entity_attr=entity_attr,
                entity_source=category,
                capability=capability_info,
                unit=unit,
                entity_category=entity_category,
                device_class=device_class,
                icon=entity_icon,
                catalog_entry=catalog_item,
                commands=commands,
            )

        return []

    def setup(self, data: Any) -> None:
        """Configure the entity."""
        self.data: Any = data
        self.entities: list[Any] = []
        entities: list[Any] = []
        # Extraction of the appliance capabilities & mapping to the known entities of the component
        # [ "applianceState", "autoDosing",..., "userSelections/analogTemperature",...]
        capabilities_names = self.data.sources_list()

        if capabilities_names is None and self.state:
            # No capabilities returned (unstable API)
            # We could rebuild them from catalog but this creates entities that are
            # not required by each device type (fridge, dryer, vacumn etc are all different)
            _LOGGER.warning("Electrolux API returned no capability definition")

        # Add static attribute
        # these are attributes that are not in the capability entry
        # but are returned by the api independantly
        for static_attribute in STATIC_ATTRIBUTES:
            _LOGGER.debug("Electrolux static_attribute %s", static_attribute)
            # attr not found in state, next attr
            attr_in_reported = self.get_state(static_attribute) is not None
            attr_at_top_level = (
                self.state.get(static_attribute) is not None if self.state else False
            )
            if not (attr_in_reported or attr_at_top_level):
                continue
            if catalog_item := self.catalog.get(static_attribute, None):
                if (entity := self.get_entity(static_attribute)) is None:
                    # catalog definition and automatic checks fail to determine type
                    _LOGGER.debug(
                        "Electrolux static_attribute undefined %s", static_attribute
                    )
                    continue
                # add to the capability dict
                keys = static_attribute.split("/")
                capabilities = self.data.capabilities
                for key in keys[:-1]:
                    capabilities = capabilities.setdefault(key, {})
                capabilities[keys[-1]] = catalog_item.capability_info
                _LOGGER.debug("Electrolux adding static_attribute %s", static_attribute)
                entities.extend(entity)

        # Add catalog entities that have capability_info defined, even if not in API capabilities
        # This ensures entities like targetDuration are always created for applicable appliance types
        for catalog_key, catalog_item in self.catalog.items():
            if catalog_item.capability_info and catalog_key not in capabilities_names:
                # Check if this entity should be created for this appliance type
                if entity := self.get_entity(catalog_key):
                    _LOGGER.debug(
                        "Electrolux adding catalog entity %s not in API capabilities",
                        catalog_key,
                    )
                    entities.extend(list(entity))

        # For each capability src
        if capabilities_names:
            for capability in capabilities_names:
                if entity := self.get_entity(capability):
                    entities.extend(list(entity))
                else:
                    _LOGGER.debug(
                        "Could not create entity for capability %s", capability
                    )

        # Setup each found entity
        # Deduplicate entities by unique_id to prevent duplicates
        unique_entities = {}
        for ent in entities:
            unique_id = ent.unique_id
            if unique_id not in unique_entities:
                unique_entities[unique_id] = ent
            else:
                _LOGGER.debug(
                    "Skipping duplicate entity with unique_id %s for appliance %s",
                    unique_id,
                    self.pnc_id,
                )

        self.entities = list(unique_entities.values())
        for ent in self.entities:
            ent.setup(data)


class Appliances:
    """Appliance class definition."""

    def __init__(self, appliances: dict[str, Appliance]) -> None:
        """Initialize the class."""
        self.appliances = appliances

    def get_appliance(self, pnc_id: str) -> Appliance | None:
        """Return the appliance."""
        return self.appliances.get(pnc_id, None)

    def get_appliances(self) -> dict[str, Appliance]:
        """Return all appliances."""
        return self.appliances

    def get_appliance_ids(self) -> list[str]:
        """Return all appliance ids."""
        return list(self.appliances)
