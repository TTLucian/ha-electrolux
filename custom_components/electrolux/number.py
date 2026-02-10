"""Number platform for Electrolux."""

import logging
from typing import Any

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NUMBER
from .entity import ElectroluxEntity
from .util import (
    AuthenticationError,
    ElectroluxApiClient,
    format_command_for_appliance,
    map_command_error_to_home_assistant_error,
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
            # Return 0 if not supported by current program
            if not self._is_supported_by_program():
                return 0.0

        # Special handling for targetTemperatureC
        if self.entity_attr == "targetTemperatureC":
            # Return 0 if not supported by current program
            if not self._is_supported_by_program():
                return 0.0

        # For non-global entities, return None if not supported by current program
        if (
            self.entity_attr not in ["targetDuration", "startTime"]
            and not self._is_supported_by_program()
        ):
            return None

        if self.entity_attr == "startTime" and value == -1:
            return None

        if not value:
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

            # Check if not supported by current program - clamp to 0 instead of error
            if not self._is_supported_by_program():
                _LOGGER.debug(
                    "Control %s not supported by current program for appliance %s, clamping to 0",
                    self.entity_attr,
                    self.pnc_id,
                )
                # Silently ignore - value stays at 0
                return

        # Special handling for targetTemperatureC
        if self.entity_attr == "targetTemperatureC":
            # Check if not supported by current program - clamp to 0 instead of error
            if not self._is_supported_by_program():
                _LOGGER.debug(
                    "Control %s not supported by current program for appliance %s, clamping to 0",
                    self.entity_attr,
                    self.pnc_id,
                )
                # Silently ignore - value stays at 0
                return

        # Prevent setting values for other unsupported programs
        if not self._is_supported_by_program():
            _LOGGER.warning(
                "Cannot set %s for appliance %s: not supported by current program",
                self.entity_attr,
                self.pnc_id,
            )
            raise HomeAssistantError(
                f"Control '{self.entity_attr}' is not supported by the current program"
            )

        # ADD RANGE VALIDATION HERE
        min_val = self.native_min_value
        max_val = self.native_max_value

        if min_val is not None and value < min_val:
            raise ValueError(
                f"Value {value} is below minimum {min_val} for {self.entity_attr}"
            )
        if max_val is not None and value > max_val:
            raise ValueError(
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
                f"Remote control disabled (status: {remote_control})"
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

        # Optimistically update the UI immediately
        if self.unit == UnitOfTime.SECONDS:
            # API receives seconds, but UI shows minutes
            self._cached_value = time_seconds_to_minutes(formatted_value) or 0
        else:
            self._cached_value = formatted_value
        self.async_write_ha_state()

        # Save old value for rollback
        old_cached_value = self._cached_value

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
            result = await client.execute_appliance_command(self.pnc_id, command)
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
            await self.coordinator.handle_authentication_error(auth_ex)
            return
        except Exception as ex:
            _LOGGER.error(
                "Electrolux error setting %s to %s (command_value=%s), rolling back: %s",
                self.entity_attr,
                value,
                command_value,
                ex,
            )
            # Rollback on any error
            self._cached_value = old_cached_value
            self.async_write_ha_state()
            # Use shared error mapping for all errors
            raise map_command_error_to_home_assistant_error(
                ex, self.entity_attr, _LOGGER, self.capability
            ) from ex
        # State will be updated via websocket streaming

    @property
    def available(self) -> bool:
        """Check if the entity is supported and not fixed (step 0)."""
        if not super().available:
            return False

        # Special case: oven temperature controls should always be available
        # but clamped to 0 if not supported by program
        if self.entity_attr in ["targetTemperatureC", "targetFoodProbeTemperatureC"]:
            return True

        if not self._is_supported_by_program():
            return False

        # If the appliance says step is 0, the control is fixed/unavailable
        if self._get_program_constraint("step") == 0:
            return False

        return True

    def _is_supported_by_program(self) -> bool:
        """Check if the entity is supported by the current program."""
        # Global entities are always supported by the appliance regardless of program
        if self.entity_attr in [
            "targetDuration",
            "startTime",
            "targetTemperature",
            "targetTemperatureC",
        ]:
            return True
        current_program = self.reported_state.get("program")
        if not current_program:
            return True  # If no program, assume supported

        # Check if the appliance has program-specific capabilities
        if not (hasattr(self.get_appliance, "data") and self.get_appliance.data):
            return True

        appliance_data = self.get_appliance.data
        if not (
            hasattr(appliance_data, "capabilities") and appliance_data.capabilities
        ):
            return True

        program_caps = (
            appliance_data.capabilities.get("program", {})
            .get("values", {})
            .get(current_program, {})
        )

        # If the entity is not in the program capabilities, it's not supported
        if self.entity_attr not in program_caps:
            # Special check for targetDuration: always available regardless of program
            if self.entity_attr == "targetDuration":
                return True
            return False

        # Start with the base disabled state from program capabilities
        entity_cap = program_caps[self.entity_attr]
        disabled = False
        if isinstance(entity_cap, dict):
            disabled = entity_cap.get("disabled", False)

        # Process triggers that affect this entity
        all_capabilities = appliance_data.capabilities
        for cap_name, cap_def in all_capabilities.items():
            if isinstance(cap_def, dict) and "triggers" in cap_def:
                for trigger in cap_def["triggers"]:
                    if isinstance(trigger, dict) and "action" in trigger:
                        action = trigger["action"]
                        # Check if this trigger affects our entity
                        if self.entity_attr in action:
                            # Check if the condition is met
                            if self._evaluate_trigger_condition(
                                trigger.get("condition", {}), cap_name
                            ):
                                # Apply the action
                                entity_action = action[self.entity_attr]
                                if (
                                    isinstance(entity_action, dict)
                                    and "disabled" in entity_action
                                ):
                                    disabled = entity_action["disabled"]
                                    _LOGGER.debug(
                                        "Trigger applied to %s: disabled=%s (trigger from %s)",
                                        self.entity_attr,
                                        disabled,
                                        cap_name,
                                    )

        # If disabled by triggers or program settings, not supported
        if disabled:
            return False

        # Special check for food probe temperature: only available if probe is inserted
        if self.entity_attr == "targetFoodProbeTemperatureC":
            food_probe_state = self.reported_state.get("foodProbeInsertionState")
            if food_probe_state == "NOT_INSERTED":
                return False

        # targetDuration is always available regardless of program
        if self.entity_attr == "targetDuration":
            return True

        return True

    def _get_program_constraint(self, key: str) -> Any | None:
        """Get a specific constraint (min/max/step) for the current program."""
        current_program = self.reported_state.get("program")
        if not current_program or not self.get_appliance.data:
            return None
        try:
            return (
                self.get_appliance.data.capabilities.get("program", {})
                .get("values", {})
                .get(current_program, {})
                .get(self.entity_attr, {})
                .get(key)
            )
        except (AttributeError, KeyError):
            return None

    def _evaluate_trigger_condition(
        self, condition: dict, trigger_cap_name: str
    ) -> bool:
        """Evaluate a trigger condition."""
        if not condition:
            return True

        operator = condition.get("operator", "eq")
        operand1 = condition.get("operand_1")
        operand2 = condition.get("operand_2")

        # Handle nested operands
        if isinstance(operand1, dict):
            operand1 = self._evaluate_operand(operand1, trigger_cap_name)
        if isinstance(operand2, dict):
            operand2 = self._evaluate_operand(operand2, trigger_cap_name)

        # Evaluate based on operator
        if operator == "eq":
            return operand1 == operand2
        elif operator == "and":
            return bool(operand1) and bool(operand2)
        elif operator == "or":
            return bool(operand1) or bool(operand2)

        return False

    def _evaluate_operand(self, operand: dict, trigger_cap_name: str) -> Any:
        """Evaluate a trigger operand."""
        if "operand_1" in operand and "operand_2" in operand:
            # This is a nested condition
            return self._evaluate_trigger_condition(operand, trigger_cap_name)
        elif "operand_1" in operand:
            # Reference to another capability
            cap_name = operand["operand_1"]
            if cap_name == "value":
                # Special case: refers to the capability that has the trigger
                return self.reported_state.get(trigger_cap_name)
            else:
                # Get the value from reported state
                return self.reported_state.get(cap_name)
        else:
            # Literal value
            return operand.get("value")

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        # Always enable entities by default - availability is controlled by the available property
        return True
