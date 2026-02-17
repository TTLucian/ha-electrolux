"""Select platform for Electrolux."""

import contextlib
import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SELECT
from .coordinator import ElectroluxCoordinator
from .entity import ElectroluxEntity
from .model import ElectroluxDevice
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
    """Configure select platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [
                entity for entity in appliance.entities if entity.entity_type == SELECT
            ]
            _LOGGER.debug(
                "Electrolux add %d SELECT entities to registry for appliance %s",
                len(entities),
                appliance_id,
            )
            async_add_entities(entities)
    return


class ElectroluxSelect(ElectroluxEntity, SelectEntity):
    """Electrolux Select class."""

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
        unit,
        device_class: str,
        entity_category: EntityCategory,
        icon: str,
        catalog_entry: ElectroluxDevice | None = None,
    ) -> None:
        """Initialize the Select entity."""
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
        values_dict: dict[str, Any] | None = self.capability.get("values", None)
        self.options_list: dict[str, str] = {}
        if values_dict:
            for value in values_dict:
                entry: dict[str, Any] | None = values_dict.get(value)
                if entry and "disabled" in entry:
                    continue

                label = entry.get("label") if entry else self.format_label(value)
                if label is None:
                    label = self.format_label(value)
                if label is not None:
                    self.options_list[label] = value

    @property
    def entity_domain(self):
        """Entity domain for the entry. Used for consistent entity_id."""
        return SELECT

    @property
    def available(self) -> bool:
        """Check if the entity is available."""
        if not super().available:
            return False

        # All select entities are always available regardless of program support
        return True

    def format_label(self, value: str | int | float | bool | None) -> str | None:
        """Convert input to label string value."""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.replace("_", " ").title()
        if self.unit == UnitOfTemperature.CELSIUS:
            value = f"{value} °C"
        elif self.unit == UnitOfTemperature.FAHRENHEIT:
            value = f"{value} °F"
        return str(value)

    @property
    def current_option(self) -> str:
        """Return the current option."""
        # If not supported by current program, show no selection
        if not self._is_supported_by_program():
            return ""

        value = self.extract_value()

        if value is None:
            return ""

        if self.catalog_entry and self.catalog_entry.value_mapping:
            mapping = self.catalog_entry.value_mapping
            _LOGGER.debug("Mapping %s: %s to %s", self.json_path, value, mapping)
            if value in mapping:
                value = mapping.get(value, value)

        label = None
        try:
            if value is not None:
                str_value = str(value)
                label = list(self.options_list.keys())[
                    list(self.options_list.values()).index(str_value)
                ]
        except (ValueError, IndexError) as ex:
            _LOGGER.info(
                "Electrolux error value %s does not exist in the list %s. %s",
                value,
                self.options_list.values(),
                ex,
            )
        # When value not in the catalog -> add the value to the list then
        if label is None:
            label = self.format_label(value)
            if label is not None and value is not None:
                self.options_list[label] = str(value)

        return str(label or "")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Check if supported by current program
        if not self._is_supported_by_program():
            _LOGGER.warning(
                "Cannot select option %s for appliance %s: not supported by current program",
                option,
                self.pnc_id,
            )
            raise HomeAssistantError(
                f"Cannot change '{self.entity_attr}': not supported by current program '{self.reported_state.get('program', 'unknown')}'"
            )

        # Check if appliance is connected before sending command
        if not self.is_connected():
            connectivity_state = self.reported_state.get("connectivityState", "unknown")
            _LOGGER.warning(
                "Appliance %s is not connected (state: %s), cannot select option %s",
                self.pnc_id,
                connectivity_state,
                option,
            )
            raise HomeAssistantError(
                f"Appliance is offline (current state: {connectivity_state}). "
                "Please check that the appliance is plugged in and has network connectivity."
            )

        # Remote control validation removed - API handles this with precise appliance-specific rules.
        # Different appliances have different states (ENABLED, NOT_SAFETY_RELEVANT_ENABLED, persistentRemoteControl)
        # that only the API can accurately validate. Error handling in util.py displays friendly messages.

        value: Any = self.options_list.get(option, None)
        if value is None:
            raise HomeAssistantError("Invalid option")

        # Rate limit commands
        await self._rate_limit_command()

        if (
            isinstance(self.unit, UnitOfTemperature)
            or self.entity_attr.startswith("targetTemperature")
            or self.entity_name.startswith("targetTemperature")
        ):
            # Attempt to convert the option to a float
            with contextlib.suppress(ValueError):
                value = float(value)

        # Format the value according to appliance capabilities
        formatted_value = format_command_for_appliance(
            self.capability, self.entity_attr, value
        )

        _LOGGER.debug(
            "Electrolux select option before reported status %s",
            (
                self.appliance_status.get("properties", {}).get("reported", {})
                if self.appliance_status
                else {}
            ),
        )

        client: ElectroluxApiClient = self.api
        command: dict[str, Any] = {}
        if not self.is_dam_appliance:
            # Legacy appliances: always send as simple top-level property
            command = {self.entity_attr: formatted_value}
        elif self.entity_source:
            if self.entity_source == "userSelections":
                # Safer access to avoid KeyError if userSelections is missing
                reported = (
                    self.appliance_status.get("properties", {}).get("reported", {})
                    if self.appliance_status
                    else {}
                )
                program_uid = reported.get("userSelections", {}).get("programUID")

                # Validate programUID
                if not program_uid:
                    _LOGGER.error(
                        "Cannot send command: programUID missing for appliance %s",
                        self.pnc_id,
                    )
                    raise HomeAssistantError(
                        "Cannot change setting: appliance state is incomplete. "
                        "Please wait for the appliance to initialize."
                    )

                command = {
                    self.entity_source: {
                        "programUID": program_uid,
                        self.entity_attr: formatted_value,
                    },
                }
            else:
                command = {self.entity_source: {self.entity_attr: formatted_value}}
        else:
            if self.entity_attr == "program":
                # For program changes, include programUID from userSelections
                reported = (
                    self.appliance_status.get("properties", {}).get("reported", {})
                    if self.appliance_status
                    else {}
                )
                program_uid = reported.get("userSelections", {}).get("programUID")
                if program_uid:
                    command = {
                        "userSelections": {
                            "programUID": program_uid,
                            "program": formatted_value,
                        }
                    }
                else:
                    command = {self.entity_attr: formatted_value}
            else:
                command = {self.entity_attr: formatted_value}

        # Wrap DAM commands in the required format
        if self.is_dam_appliance:
            command = {"commands": [command]}

        _LOGGER.debug("Electrolux select option %s", command)
        try:
            result = await execute_command_with_error_handling(
                client, self.pnc_id, command, self.entity_attr, _LOGGER, self.capability
            )
        except AuthenticationError as auth_ex:
            # Handle authentication errors by triggering reauthentication
            coordinator: ElectroluxCoordinator = self.coordinator  # type: ignore[assignment]
            await coordinator.handle_authentication_error(auth_ex)
            return  # Explicit return (unreachable but clear)
        except Exception:
            # Re-raise any errors from execute_command_with_error_handling
            raise
        _LOGGER.debug("Electrolux select option result %s", result)

        # State will be updated via SSE streaming
        # Note: targetTemperatureC is automatically updated by the Electrolux API when program changes
        # We do NOT need to manually send a temperature command - it creates cache conflicts

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        This method updates the appliance status from coordinator data and
        immediately writes the new state to Home Assistant. Select entities
        rely on the base class's cache management to ensure reported_state
        is always current for option filtering.
        """
        # Call parent to update caches and detect program changes
        super()._handle_coordinator_update()

    @property
    def options(self) -> list[str]:
        """Return a set of selectable options filtered by program constraints.

        This method dynamically filters available options based on the current
        appliance program. When a program specifies allowed values, only those
        options are presented to prevent invalid selections.

        The filtering process:
        1. Start with all configured options from the catalog
        2. Check for program-specific value constraints
        3. Filter options to only include program-allowed values
        4. Fall back to all options if no program constraints exist

        Returns:
            list[str]: Filtered list of selectable option labels
        """
        # Start with all available options
        all_options = list(self.options_list.keys())

        # Check for program-specific value constraints
        program_values = self._get_program_constraint("values")
        if program_values is not None:
            if isinstance(program_values, list):
                # Filter options to only include those allowed by the program
                allowed_values = set(str(v) for v in program_values)
                filtered_options = []
                for label, value in self.options_list.items():
                    if str(value) in allowed_values:
                        filtered_options.append(label)
                return filtered_options

        # No program constraints, return all options
        return all_options
