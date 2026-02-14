"""Number platform for Electrolux."""

import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NUMBER
from .coordinator import ElectroluxCoordinator
from .entity import ElectroluxEntity
from .util import (
    AuthenticationError,
    ElectroluxApiClient,
    execute_command_with_error_handling,
    format_command_for_appliance,
    time_minutes_to_seconds,
    time_seconds_to_minutes,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure number platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [
                entity for entity in appliance.entities if entity.entity_type == NUMBER
            ]
            _LOGGER.debug(
                "Electrolux add %d NUMBER entities to registry for appliance %s",
                len(entities),
                appliance_id,
            )
            async_add_entities(entities)


class ElectroluxNumber(ElectroluxEntity, NumberEntity):
    """Electrolux number class.

    TIME ENTITY HANDLING:
    - The Electrolux API works exclusively in SECONDS for all time-based values
    - For user-friendliness, this integration displays and accepts time in MINUTES
    - Conversion happens automatically in two places:
      1. native_value: Converts API response (seconds) → UI display (minutes)
      2. async_set_native_value: Converts UI input (minutes) → API command (seconds)
    - All time entities are identified by their unit (UnitOfTime) rather than hardcoded names
    - This ensures consistent conversion for all current and future time-based entities
    """

    @property
    def entity_domain(self) -> str:
        """Entity domain for the entry. Used for consistent entity_id."""
        return NUMBER

    @property
    def mode(self) -> NumberMode:
        """Return the mode for the number entity."""
        # Use box input for time-based entities to allow free minute input
        if self.entity_attr in ["startTime", "targetDuration"]:
            return NumberMode.BOX
        # Use slider for other controls with step constraints
        return NumberMode.SLIDER

    @property
    def device_class(self) -> NumberDeviceClass | None:
        """Return the device class for the number entity."""
        # For NUMBER entities, we should only return NumberDeviceClass values
        # The catalog might have SensorDeviceClass for temperature entities, but
        # since they're NUMBER entities, we need to map them appropriately
        if self._catalog_entry and hasattr(self._catalog_entry, "device_class"):
            catalog_device_class = self._catalog_entry.device_class
            # Map temperature sensor device classes to number device classes
            if catalog_device_class == "temperature":  # Handle string values
                return NumberDeviceClass.TEMPERATURE
            # Only return NumberDeviceClass values for NUMBER entities
            if isinstance(catalog_device_class, NumberDeviceClass):
                return catalog_device_class

        # For entities without proper catalog device_class, check the base device_class
        # but only return NumberDeviceClass values
        base_device_class = self._device_class
        if isinstance(base_device_class, NumberDeviceClass):
            return base_device_class
        # Handle string values for backward compatibility
        if base_device_class == "temperature":
            return NumberDeviceClass.TEMPERATURE

        # Check capability type for automatic device class mapping
        capability_type = self.capability.get("type")
        if capability_type == "temperature":
            return NumberDeviceClass.TEMPERATURE

        # Default to None if no valid NumberDeviceClass is found
        return None

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""
        # Return cached value for immediate UI feedback
        if self._cached_value is not None:
            return self._cached_value

        value = self.extract_value()

        # Special handling for targetFoodProbeTemperatureC
        if self.entity_attr == "targetFoodProbeTemperatureC":
            # Return 0 if food probe is not inserted
            food_probe_state = self.reported_state.get("foodProbeInsertionState")
            if food_probe_state == "NOT_INSERTED":
                return 0.0
            # Return min value if not supported by current program
            if not self._is_supported_by_program():
                min_val = self.native_min_value
                return min_val if min_val is not None else 0.0

        # Special handling for targetTemperatureC
        if self.entity_attr == "targetTemperatureC":
            # Return minimum value if not supported by current program and no valid value reported
            if not value and not self._is_supported_by_program():
                min_val = self.native_min_value
                return min_val if min_val is not None else 0.0

        # For non-global entities, return minimum value if not supported by current program
        if (
            self.entity_attr
            not in ["targetDuration", "startTime", "targetFoodProbeTemperatureC"]
            and not self._is_supported_by_program()
        ):
            # Return minimum value when not supported by program
            min_val = self.native_min_value
            return min_val if min_val is not None else 0.0

        if self.entity_attr == "startTime" and value == -1:
            return None

        if not value:
            # First try program-specific default for temperature controls
            if self.entity_attr in [
                "targetTemperatureC",
                "targetFoodProbeTemperatureC",
            ]:
                program_default = self._get_program_constraint("default")
                if program_default is not None:
                    value = program_default
                    _LOGGER.debug(
                        "Using program default for %s: %s", self.entity_attr, value
                    )
                elif self.entity_attr == "targetTemperatureC":
                    value = self.capability.get("default", 0.0)
            # Fall back to base capability default
            if value is None:
                value = self.capability.get("default", None)
                if value == "INVALID_OR_NOT_SET_TIME":
                    value = self.capability.get("min", None)
                if not value and self.entity_attr == "targetDuration":
                    value = 0
        if not value:
            return self._cached_value
        if isinstance(self.unit, UnitOfTemperature):
            value = round(value, 2)

        original_value = value  # Store for logging

        # Convert to native units (minutes for time entities)
        if self.unit == UnitOfTime.SECONDS:
            # Convert seconds from API to minutes for UI
            value = time_seconds_to_minutes(value) or 0
            _LOGGER.debug(
                "Electrolux time entity %s: converted API value %s seconds to %s minutes for UI",
                self.entity_attr,
                original_value,
                value,
            )

        # Clamp value to current program-specific min/max range
        min_val = self.native_min_value
        max_val = self.native_max_value
        if min_val is not None and value < min_val:
            value = min_val
        if max_val is not None and value > max_val:
            value = max_val

        self._cached_value = value
        return value

    @property
    def native_max_value(self) -> float:
        """Return max value: Catalog (Seconds) -> Program -> Appliance API, converted to minutes for UI."""
        return self._get_converted_constraint("max")

    @property
    def native_min_value(self) -> float:
        """Return min value: Catalog (Seconds) -> Program -> Appliance API, converted to minutes for UI."""
        return self._get_converted_constraint("min")

    @property
    def native_step(self) -> float:
        """Return step value: Catalog (Seconds) -> Program -> Safe Default, converted to minutes for UI."""
        return self._get_converted_constraint("step")

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement, converting seconds to minutes for time entities."""
        if self.unit == UnitOfTime.SECONDS:
            _LOGGER.debug(
                "Electrolux time entity %s: converting unit from %s to minutes",
                self.entity_attr,
                self.unit,
            )
            return UnitOfTime.MINUTES  # Show 'min' instead of 's' for time entities
        return self.unit

    def _get_converted_constraint(self, key: str) -> float:
        """Get a constraint value (min/max/step) with proper time conversion."""
        # Special handling for temperature controls that should always be available
        if self.entity_attr in ["targetTemperatureC", "targetFoodProbeTemperatureC"]:
            if not self._is_supported_by_program():
                return 0.0

        # 1. Catalog is the Source of Truth (already in correct units - seconds)
        if (
            self._catalog_entry
            and (cat_val := self._catalog_entry.capability_info.get(key)) is not None
        ):
            # Convert seconds to minutes for UI display
            if self.unit == UnitOfTime.SECONDS:
                converted_val = time_seconds_to_minutes(cat_val) or 0
                if key == "step":
                    _LOGGER.debug(
                        "Electrolux time entity %s: converted %s from %s seconds to %s minutes",
                        self.entity_attr,
                        key,
                        cat_val,
                        converted_val,
                    )
                return float(converted_val)
            return float(cat_val)

        # 2. Fallback to API/Program logic
        val = self._get_program_constraint(key) or self.capability.get(key)

        # For
        # C and targetFoodProbeTemperatureC, use 0.0 as last resort if no API values
        if (
            self.entity_attr in ["targetTemperatureC", "targetFoodProbeTemperatureC"]
            and val is None
        ):
            val = 0.0

        # 3. Convert only if coming from API (seconds) and entity is time-based
        if self.unit == UnitOfTime.SECONDS and val is not None:
            converted_val = time_seconds_to_minutes(val) or 0
            if key == "step":
                _LOGGER.debug(
                    "Electrolux time entity %s: converted %s from %s seconds to %s minutes",
                    self.entity_attr,
                    key,
                    val,
                    converted_val,
                )
            return float(converted_val)

        # Defaults
        if key == "max":
            return float(val or 100.0)
        elif key == "min":
            return float(val or 0.0)
        elif key == "step":
            return float(val or 1.0)
        return float(val or 1.0)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        # Special handling for targetFoodProbeTemperatureC
        if self.entity_attr == "targetFoodProbeTemperatureC":
            # Check if food probe is not inserted
            food_probe_state = self.reported_state.get("foodProbeInsertionState")
            if food_probe_state == "NOT_INSERTED":
                _LOGGER.warning(
                    "Food probe not inserted for appliance %s, %s not available",
                    self.pnc_id,
                    self.entity_attr,
                )
                # Show user-friendly message
                raise HomeAssistantError(
                    "Food probe must be inserted to set target temperature."
                )

            # Check if not supported by current program - prevent modification
            if not self._is_supported_by_program():
                _LOGGER.warning(
                    "Cannot set %s for appliance %s: not supported by current program",
                    self.entity_attr,
                    self.pnc_id,
                )
                raise HomeAssistantError(
                    f"Target food probe temperature control not supported by current program '{self.reported_state.get('program', 'unknown')}'"
                )

        # Prevent setting values for unsupported programs
        if not self._is_supported_by_program():
            _LOGGER.warning(
                "Cannot set %s for appliance %s: not supported by current program",
                self.entity_attr,
                self.pnc_id,
            )
            raise HomeAssistantError(
                f"Control '{self.entity_attr}' not supported by current program '{self.reported_state.get('program', 'unknown')}'"
            )

        # ADD RANGE VALIDATION HERE
        min_val = self.native_min_value
        max_val = self.native_max_value

        if min_val is not None and value < min_val:
            raise HomeAssistantError(
                f"Value {value} is below minimum {min_val} for {self.entity_attr}"
            )
        if max_val is not None and value > max_val:
            raise HomeAssistantError(
                f"Value {value} is above maximum {max_val} for {self.entity_attr}"
            )

        _LOGGER.debug(
            "Electrolux set %s to %s (min: %s, max: %s)",
            self.entity_attr,
            value,
            min_val,
            max_val,
        )

        _LOGGER.debug(
            "Electrolux number entity %s setting value: raw=%s, unit=%s, current_cached=%s",
            self.entity_attr,
            value,
            self.unit,
            self._cached_value,
        )

        # Rate limit commands
        await self._rate_limit_command()

        # Check if appliance is connected before sending command
        if not self.is_connected():
            connectivity_state = self.reported_state.get("connectivityState", "unknown")
            _LOGGER.warning(
                "Appliance %s is not connected (state: %s), cannot set %s",
                self.pnc_id,
                connectivity_state,
                self.entity_attr,
            )
            raise HomeAssistantError(
                f"Appliance is offline (current state: {connectivity_state}). "
                "Please check that the appliance is plugged in and has network connectivity."
            )

        # Check if remote control is enabled
        remote_control = (
            self.appliance_status.get("properties", {})
            .get("reported", {})
            .get("remoteControl")
            if self.appliance_status
            else None
        )
        _LOGGER.debug(
            "Number control remote control check for %s: status=%s",
            self.entity_attr,
            remote_control,
        )
        # Check for disabled states
        if remote_control is not None and (
            "ENABLED" not in str(remote_control) or "DISABLED" in str(remote_control)
        ):
            _LOGGER.warning(
                "Cannot set %s for appliance %s: remote control is %s",
                self.entity_attr,
                self.pnc_id,
                remote_control,
            )
            raise HomeAssistantError(
                f"Remote control is disabled (status: {remote_control})"
            )

        # Convert UI minutes back to seconds for time entities
        command_value: int | float  # Add explicit type annotation
        if self.unit == UnitOfTime.SECONDS:
            # If user sets '1' (minute), send '60' (seconds) to the API
            command_value = time_minutes_to_seconds(value) or 0
            _LOGGER.debug(
                "Electrolux time entity %s: converting UI value %s minutes to %s seconds for API",
                self.entity_attr,
                value,
                command_value,
            )
        else:
            command_value = value
            _LOGGER.debug(
                "Electrolux non-time entity %s: using value %s directly",
                self.entity_attr,
                command_value,
            )

        if self.capability.get("step", 1) == 1:
            command_value = int(command_value)

        client: ElectroluxApiClient = self.api

        # Format the value according to appliance capabilities
        formatted_value = format_command_for_appliance(
            self.capability, self.entity_attr, command_value
        )

        # Save old value for rollback BEFORE optimistic update
        old_cached_value = self._cached_value

        # Optimistically update the UI immediately
        if self.unit == UnitOfTime.SECONDS:
            # API receives seconds, but UI shows minutes
            self._cached_value = time_seconds_to_minutes(formatted_value) or 0
        else:
            self._cached_value = formatted_value
        self.async_write_ha_state()

        # Build the command. For legacy appliances, send simple top-level properties.
        # For DAM appliances, use appropriate wrapping.
        if not self.is_dam_appliance:
            # Legacy appliances: always send as simple top-level property
            command = {self.entity_attr: formatted_value}
        elif self.entity_attr in ["targetDuration", "startTime"]:
            # DAM appliances: time settings wrapped in appliance type
            appliance_type = getattr(
                self.get_appliance, "appliance_type", "oven"
            ).lower()
            command = {appliance_type: {self.entity_attr: formatted_value}}
        elif self.entity_source == "latamUserSelections":
            _LOGGER.debug(
                "Electrolux: Detected latamUserSelections, building full command."
            )
            # Get the current state of all latam selections
            current_selections = (
                self.appliance_status.get("properties", {})
                .get("reported", {})
                .get("latamUserSelections", {})
                if self.appliance_status
                else {}
            )
            if not current_selections:
                _LOGGER.error(
                    "Could not retrieve current latamUserSelections to build command."
                )
                return

            # Create a copy to modify
            new_selections = current_selections.copy()
            # Update only the value we want to change
            new_selections[self.entity_attr] = formatted_value
            # Assemble the final command with the entire block
            command = {"latamUserSelections": new_selections}
        elif self.entity_source == "userSelections":
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
        elif self.entity_source:
            command = {self.entity_source: {self.entity_attr: formatted_value}}
        else:
            command = {self.entity_attr: formatted_value}

        # Wrap DAM commands in the required format
        if self.is_dam_appliance:
            command = {"commands": [command]}

        _LOGGER.debug("Electrolux set value %s", command)
        _LOGGER.debug(
            "Electrolux sending command to appliance %s: %s", self.pnc_id, command
        )
        try:
            result = await execute_command_with_error_handling(
                client, self.pnc_id, command, self.entity_attr, _LOGGER, self.capability
            )
            _LOGGER.debug(
                "Electrolux command successful for %s: result=%s",
                self.entity_attr,
                result,
            )
        except AuthenticationError as auth_ex:
            _LOGGER.error(
                "Electrolux authentication error setting %s, rolling back from %s to %s",
                self.entity_attr,
                value,
                old_cached_value,
            )
            # Rollback on authentication error
            self._cached_value = old_cached_value
            self.async_write_ha_state()
            # Handle authentication errors by triggering reauthentication
            coordinator: ElectroluxCoordinator = self.coordinator  # type: ignore[assignment]
            await coordinator.handle_authentication_error(auth_ex)
            return
        except Exception as ex:
            # Rollback on any error
            _LOGGER.error(
                "Electrolux command error setting %s to %s (command_value=%s), rolling back: %s",
                self.entity_attr,
                value,
                command_value,
                ex,
            )
            self._cached_value = old_cached_value
            self.async_write_ha_state()
            # Re-raise the error
            raise
        # State will be updated via websocket streaming

    @property
    def available(self) -> bool:
        """Check if the entity is supported and not fixed (step 0)."""
        if not super().available:
            return False

        # All number entities must remain available regardless of program support
        # to prevent UI rendering issues (per Entity Availability Rules)
        return True

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        # Always enable entities by default - availability is controlled by the available property
        return True
        """Return if the entity should be enabled when first added to the entity registry."""
        # Always enable entities by default - availability is controlled by the available property
        return True
