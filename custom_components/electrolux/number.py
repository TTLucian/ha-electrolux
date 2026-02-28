"""Number platform for Electrolux."""

import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEFAULT_NUMBER_MAX,
    DEFAULT_NUMBER_MIN,
    DEFAULT_NUMBER_STEP,
    DOMAIN,
    FOOD_PROBE_STATE_NOT_INSERTED,
    NUMBER,
    NUMBER_MODE_SLIDER_MAX_STEPS,
    TEMP_OVEN_MAX_C,
    TEMP_OVEN_MAX_F,
    TEMP_OVEN_MIN_C,
    TEMP_OVEN_STEP,
    TEMP_PROBE_MAX_C,
    TEMP_PROBE_MAX_F,
    TIME_INVALID_OR_NOT_SET,
    TIME_INVALID_SENTINEL,
)
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


def _get_capability_constraint(capability: dict, key: str) -> float | None:
    """Extract min/max/step from a capability dict, supporting standard and DAM range formats.

    Standard format (legacy appliances): {"min": 16, "max": 32, "step": 1}
    DAM single-range format: {"range": [min, max, step]}
    DAM multi-range format: {"ranges": [[min, max, step], [min2, max2, step2], ...]}
      - "min": smallest min across all ranges
      - "max": largest max across all ranges
      - "step": smallest non-zero step across all ranges

    Args:
        capability: The capability dict from the API/catalog.
        key: One of "min", "max", or "step".

    Returns:
        The numeric constraint value, or None if not available.
    """
    # Standard format takes precedence (also used by catalog overrides)
    val = capability.get(key)
    if val is not None:
        return float(val)

    index = {"min": 0, "max": 1, "step": 2}.get(key)
    if index is None:
        return None

    # DAM single-range format: range: [min, max, step]
    range_arr = capability.get("range")
    if isinstance(range_arr, list) and len(range_arr) > index:
        raw = range_arr[index]
        if raw is not None:
            return float(raw)

    # DAM multi-range format: ranges: [[min, max, step], ...]
    ranges = capability.get("ranges")
    if isinstance(ranges, list) and ranges:
        valid = [r for r in ranges if isinstance(r, list) and len(r) > index]
        if valid:
            if key == "min":
                return float(min(r[0] for r in valid))
            elif key == "max":
                vals = [r[1] for r in valid if len(r) > 1]
                return float(max(vals)) if vals else None
            elif key == "step":
                steps = [r[2] for r in valid if len(r) > 2 and r[2] > 0]
                return float(min(steps)) if steps else None

    return None


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
    return


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
        """Return the mode for the number entity.

        BOX mode: Best for large ranges where typing is faster (e.g., 1-1440 minutes)
        SLIDER mode: Best for small ranges with visual feedback (e.g., 30-230°C in 5° steps)

        Decision is based on number of possible values:
        - Few values (≤50 steps): SLIDER provides good visual feedback
        - Many values (>50 steps): BOX allows direct input, faster than sliding
        """
        # Calculate the number of possible values based on min/max/step
        min_val = self.native_min_value
        max_val = self.native_max_value
        step_val = self.native_step

        # Safety checks
        if min_val is None or max_val is None or step_val is None or step_val == 0:
            # Default to slider if we can't determine range
            return NumberMode.SLIDER

        # Calculate number of steps: (max - min) / step + 1
        num_steps = ((max_val - min_val) / step_val) + 1

        # Use SLIDER for reasonable number of steps (≤NUMBER_MODE_SLIDER_MAX_STEPS provides good UX)
        # Examples with SLIDER:
        #   - antiCreaseValue: 4 steps (30/60/90/120) → intuitive selection
        #   - dryingTime: 31 steps (0-300 min, 10 min step) → manageable
        #   - oven temp: ~41 steps (30-230°C, 5° step) → natural for temperature
        #   - food probe: 70 steps (30-99°C, 1° step) → natural for temperature
        #   - stopTime: 25 steps (0-24 hours, 1 hour step) → easy to slide
        # Examples with BOX:
        #   - targetDuration: 1440 steps (0-1439 min, 1 min step) → typing is faster
        #   - startTime: 1440 steps (0-1439 min, 1 min step) → typing is faster
        if num_steps <= NUMBER_MODE_SLIDER_MAX_STEPS:
            return NumberMode.SLIDER

        # Use BOX for large ranges where typing is more efficient
        return NumberMode.BOX

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
        # When offline, return None to show "unknown" (avoid showing stale data)
        if self.entity_attr != "connectivityState" and not self.is_connected():
            return None

        # If entity is locked, return the locked value
        if self._is_locked_by_program():
            locked_value = self._get_locked_value()
            # For time entities, convert locked value
            if self.unit == UnitOfTime.SECONDS:
                locked_value = time_seconds_to_minutes(locked_value) or 0
            return locked_value

        value = self.extract_value()

        if self.entity_attr == "startTime" and value == TIME_INVALID_SENTINEL:
            return None

        if value is None:
            # First try program-specific default for temperature controls
            if self.entity_attr in [
                "targetTemperatureC",
                "targetTemperatureF",
                "targetFoodProbeTemperatureC",
            ]:
                program_default = self._get_program_constraint("default")
                if program_default is not None:
                    value = program_default
                    _LOGGER.debug(
                        "Using program default for %s: %s", self.entity_attr, value
                    )
                elif self.entity_attr in ["targetTemperatureC", "targetTemperatureF"]:
                    value = self.capability.get("default", 0.0)
            # Fall back to base capability default
            if value is None:
                value = self.capability.get("default", None)
                if value == TIME_INVALID_OR_NOT_SET:
                    value = self.capability.get("min", None)
                if value is None and self.entity_attr == "targetDuration":
                    value = 0
        if value is None:
            return None

        # Ensure value is numeric before performing numeric operations
        if not isinstance(value, (int, float)):
            _LOGGER.warning(
                "Electrolux entity %s received non-numeric value: %s (type: %s)",
                self.entity_attr,
                value,
                type(value).__name__,
            )
            return None

        if isinstance(self.unit, UnitOfTemperature):
            value = round(value, 2)

        # Temperature controls: Read/write directly to API without conversion
        # If API provides targetTemperatureC, we expose a C control
        # If API provides targetTemperatureF, we expose an F control
        # If API provides both, we expose both - users can choose which to use
        # No automatic conversion or companion entity creation

        # Convert to native units (minutes for time entities)
        if self.unit == UnitOfTime.SECONDS:
            # Convert seconds from API to minutes for UI
            value = time_seconds_to_minutes(value) or 0

        # Clamp value to current program-specific min/max range
        min_val = self.native_min_value
        max_val = self.native_max_value
        if min_val is not None and value < min_val:
            value = min_val
        if max_val is not None and value > max_val:
            value = max_val

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

    def _is_locked_by_program(self) -> bool:
        """Check if this number entity is locked by the current program.

        A number entity is considered locked when:
        - Program has min=max (e.g., DEFROST with targetTemperatureC: min=40, max=40)
        - Program has step=0 (indicating no adjustment allowed)
        - Program doesn't include this entity in its capabilities (not supported)

        Configuration entities (EntityCategory.CONFIG) are NEVER locked - they're appliance
        settings that persist across programs and don't depend on cycle state.

        Returns:
            bool: True if entity should be locked (read-only), False if adjustable
        """
        # Configuration entities are never locked by program state
        # These are appliance settings (rinseAidLevel, waterHardness, etc.) that should
        # always be accessible regardless of what program is running or if appliance is OFF
        if self._entity_category == EntityCategory.CONFIG:
            return False

        # Program and global duration/time entities are never locked
        if self.entity_attr in ["program", "targetDuration", "startTime"]:
            return False

        # Food probe temperature locked when probe not inserted
        if self.entity_attr == "targetFoodProbeTemperatureC":
            food_probe_state = self.reported_state.get("foodProbeInsertionState")
            if food_probe_state == FOOD_PROBE_STATE_NOT_INSERTED:
                return True

        # Get program-specific constraints
        program_min = self._get_program_constraint("min")
        program_max = self._get_program_constraint("max")
        program_step = self._get_program_constraint("step")

        # Check if entity is not in program capabilities at all
        if not self._is_supported_by_program():
            return True

        # Check for locked range (min=max)
        if program_min is not None and program_max is not None:
            if program_min == program_max:
                return True

        # Check for zero step (no adjustment)
        if program_step is not None and program_step == 0:
            return True

        return False

    def _get_locked_value(self) -> float:
        """Get the locked value for this entity when it's locked by the program.

        Priority order:
        1. Program-specific default value
        2. Program-specific min value (when min=max)
        3. Global capability default
        4. Global capability min
        5. 0.0 as last resort

        Returns:
            float: The value to lock the entity at
        """
        # Try program default first
        program_default = self._get_program_constraint("default")
        if program_default is not None and isinstance(program_default, (int, float)):
            return float(program_default)

        # Try program min (useful when min=max)
        program_min = self._get_program_constraint("min")
        if program_min is not None and isinstance(program_min, (int, float)):
            return float(program_min)

        # Fall back to global capability default
        global_default = self.capability.get("default")
        if global_default is not None and isinstance(global_default, (int, float)):
            return float(global_default)

        # Fall back to global capability min (also handles DAM range format)
        global_min = _get_capability_constraint(self.capability, "min")
        if global_min is not None and isinstance(global_min, (int, float)):
            return float(global_min)

        # Last resort: 0.0
        return 0.0

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement, converting seconds to minutes for time entities."""
        if self.unit == UnitOfTime.SECONDS:
            return UnitOfTime.MINUTES  # Show 'min' instead of 's' for time entities
        return self.unit

    def _get_converted_constraint(self, key: str) -> float:
        """Get a constraint value (min/max/step) with proper time conversion.

        This method implements a hierarchical fallback system for constraint values:
        1. Check if entity is locked (min=max or step=0) -> return locked value for all constraints
        2. Catalog definitions (source of truth for entity-specific constraints)
        3. Program-specific API constraints (dynamic based on current program)
        4. Base capability constraints (fallback to entity definition)

        For time-based entities, values are converted from seconds (API) to minutes (UI).
        Special handling ensures temperature controls remain available but locked when
        not supported by the current program.

        Args:
            key: The constraint type ("min", "max", or "step")

        Returns:
            float: The converted constraint value suitable for UI display
        """
        # If entity is locked, return the locked value for both min and max
        # This makes min=max, which causes the UI to grey out the control (standard HA pattern)
        # While this prevents showing custom error messages, it provides clear visual feedback
        # that the control is read-only and prevents confusing "adjustable but blocked" UX
        if self._is_locked_by_program() and key != "step":
            locked_value = self._get_locked_value()
            # For time entities, convert locked value if needed
            if self.unit == UnitOfTime.SECONDS:
                locked_value = time_seconds_to_minutes(locked_value) or 0
            return float(locked_value)

        # For non-locked or step constraint, fall through to normal logic
        # 1. Catalog is the Source of Truth (already in correct units - seconds)
        if (
            self._catalog_entry
            and (cat_val := self._catalog_entry.capability_info.get(key)) is not None
        ):
            # Ensure cat_val is numeric
            if not isinstance(cat_val, (int, float)):
                _LOGGER.warning(
                    "Electrolux entity %s has non-numeric catalog constraint %s: %s (type: %s)",
                    self.entity_attr,
                    key,
                    cat_val,
                    type(cat_val).__name__,
                )
                cat_val = None

            if cat_val is not None:
                # Convert seconds to minutes for UI display
                if self.unit == UnitOfTime.SECONDS:
                    converted_val = time_seconds_to_minutes(cat_val) or 0
                    return float(converted_val)
                return float(cat_val)

        # 2. Fallback to API/Program logic
        val = self._get_program_constraint(key)
        if val is None:
            val = _get_capability_constraint(self.capability, key)

        # Ensure val is numeric or None before proceeding
        if val is not None and not isinstance(val, (int, float)):
            _LOGGER.warning(
                "Electrolux entity %s received non-numeric constraint %s: %s (type: %s)",
                self.entity_attr,
                key,
                val,
                type(val).__name__,
            )
            val = None

        # Final fallback to capability if program constraint was invalid (also handles DAM range)
        if val is None:
            val = _get_capability_constraint(self.capability, key)

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
            return float(converted_val)

        # Defaults
        if key == "max":
            # Temperature entities need proper fallback max values
            if self.entity_attr == "targetTemperatureC":
                return float(val or TEMP_OVEN_MAX_C)
            elif self.entity_attr == "targetTemperatureF":
                return float(val or TEMP_OVEN_MAX_F)
            elif self.entity_attr == "targetFoodProbeTemperatureC":
                return float(val or TEMP_PROBE_MAX_C)
            elif self.entity_attr == "targetFoodProbeTemperatureF":
                return float(val or TEMP_PROBE_MAX_F)
            return float(val or DEFAULT_NUMBER_MAX)
        elif key == "min":
            if self.entity_attr == "targetTemperatureC":
                return float(val or TEMP_OVEN_MIN_C)
            return float(val or DEFAULT_NUMBER_MIN)
        elif key == "step":
            # Never return 0 for step to prevent schema validation errors
            # Entity locking is enforced by min=max, not step=0
            if val is not None and val != 0:
                return float(val)
            # Use oven-specific step for temperature controls
            if self.entity_attr in ["targetTemperatureC", "targetTemperatureF"]:
                return TEMP_OVEN_STEP
            return DEFAULT_NUMBER_STEP
        if val is None and self.capability:
            val = _get_capability_constraint(self.capability, key)
        return float(val or DEFAULT_NUMBER_STEP)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        # Check if entity is locked by program (min=max, step=0, or not supported)
        if self._is_locked_by_program():
            current_program = self._get_current_program_name() or "unknown"
            locked_value = self._get_locked_value()

            # Provide specific error message based on lock reason
            if self.entity_attr == "targetFoodProbeTemperatureC":
                food_probe_state = self.reported_state.get("foodProbeInsertionState")
                if food_probe_state == FOOD_PROBE_STATE_NOT_INSERTED:
                    raise HomeAssistantError(
                        "Food probe must be inserted to set target temperature."
                    )
                elif not self._is_supported_by_program():
                    raise HomeAssistantError(
                        f"Food probe temperature not supported by program '{current_program}'"
                    )
                else:
                    raise HomeAssistantError(
                        f"Food probe temperature locked at {locked_value}°C for program '{current_program}'"
                    )
            elif not self._is_supported_by_program():
                raise HomeAssistantError(
                    f"'{self.entity_attr}' not supported by program '{current_program}'"
                )
            else:
                # Locked due to min=max or step=0
                raise HomeAssistantError(
                    f"'{self.entity_attr}' locked at {locked_value} for program '{current_program}'"
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
            "Electrolux number entity %s setting value: raw=%s, unit=%s",
            self.entity_attr,
            value,
            self.unit,
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
                "Please check that the appliance is plugged in, has network connectivity and is connected to cloud services."
            )

        # Remote control validation removed - API handles this with precise appliance-specific rules.
        # Different appliances have different states (ENABLED, NOT_SAFETY_RELEVANT_ENABLED, persistentRemoteControl)
        # that only the API can accurately validate. Error handling in util.py displays friendly messages.

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

        cap_step = _get_capability_constraint(self.capability, "step")
        if cap_step is None or cap_step == 1:
            command_value = int(command_value)

        client: ElectroluxApiClient = self.api

        # Format the value according to appliance capabilities
        formatted_value = format_command_for_appliance(
            self.capability, self.entity_attr, command_value
        )

        # Save old cached value for rollback BEFORE sse update
        old_cached_value = command_value

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

            # Optimistically update local state using base class helper method
            # Store the API value (seconds for time entities, raw value otherwise)
            self._apply_optimistic_update(
                self.entity_attr,
                command_value,
                "API value, will be confirmed by SSE",
            )

        except AuthenticationError as auth_ex:
            _LOGGER.error(
                "Electrolux authentication error setting %s, rolling back from %s to %s",
                self.entity_attr,
                value,
                old_cached_value,
            )
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
            # Re-raise the error
            raise

    @property
    def available(self) -> bool:
        """Check if the entity is supported.

        Number entities must remain available regardless of program support
        to prevent UI rendering issues (per Entity Availability Rules).
        They will be clamped/locked at minimum values when not supported.
        """
        return super().available

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        # Always enable entities by default - availability is controlled by the available property
        return True
