"""Utilities for the Electrolux platform."""

import base64
import json
import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .api_client import ElectroluxApiClient, get_electrolux_session  # noqa: F401
from .const import (
    CONF_NOTIFICATION_DEFAULT,
    CONF_NOTIFICATION_DIAG,
    CONF_NOTIFICATION_WARNING,
    DOMAIN,  # noqa: F401 — re-exported for backward compatibility
    NAME,
    SECONDS_PER_MINUTE,
    TIME_INVALID_SENTINEL,
)
from .exceptions import (  # noqa: F401
    REMOTE_CONTROL_ERROR_PHRASES,
    ApplianceOfflineError,
    AuthenticationError,
    CommandError,
    CommandValidationError,
    NetworkError,
    RateLimitError,
    RemoteControlDisabledError,
)
from .token_manager import ElectroluxTokenManager  # noqa: F401

_LOGGER: logging.Logger = logging.getLogger(__package__)


def should_send_notification(config_entry, alert_severity, alert_status) -> bool:
    """Determine if the notification should be sent based on severity and config."""
    if alert_status == "NOT_NEEDED":
        return False
    if alert_severity == "DIAGNOSTIC":
        return config_entry.data.get(CONF_NOTIFICATION_DIAG, False)
    elif alert_severity == "WARNING":
        return config_entry.data.get(CONF_NOTIFICATION_WARNING, False)
    else:
        return config_entry.data.get(CONF_NOTIFICATION_DEFAULT, True)


def create_notification(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    alert_name: str,
    alert_severity: str,
    alert_status: str,
    title: str = NAME,
):
    """Create a notification."""

    message = (
        f"Alert: {alert_name}</br>Severity: {alert_severity}</br>Status: {alert_status}"
    )

    if should_send_notification(config_entry, alert_severity, alert_status) is False:
        _LOGGER.debug(
            "Discarding notification.\nTitle: %s\nMessage: %s",
            title,
            message,
        )
        return

    # Convert the string to base64 - this prevents the same alert being spammed
    input_string = f"{title}-{message}"
    bytes_string = input_string.encode("utf-8")
    base64_bytes = base64.b64encode(bytes_string)
    base64_string = base64_bytes.decode("utf-8")

    # send notification with crafted notification id so we dont spam notifications
    _LOGGER.debug(
        "Sending notification.\nTitle: %s\nMessage: %s",
        title,
        message,
    )
    hass.async_create_task(
        hass.services.async_call(
            "persistent_notification",
            "create",
            {"message": message, "title": title, "notification_id": base64_string},
        )
    )


def time_seconds_to_minutes(seconds: float | None) -> int | None:
    """Convert seconds to minutes."""
    if seconds is None:
        return None
    if seconds == TIME_INVALID_SENTINEL:
        return TIME_INVALID_SENTINEL
    return round(seconds / SECONDS_PER_MINUTE)


def time_minutes_to_seconds(minutes: float | None) -> int | None:
    """Convert minutes to seconds."""
    if minutes is None:
        return None
    if minutes == TIME_INVALID_SENTINEL:
        return TIME_INVALID_SENTINEL
    return int(minutes) * SECONDS_PER_MINUTE


def celsius_to_fahrenheit(celsius: float | None) -> float | None:
    """Convert Celsius to Fahrenheit."""
    if celsius is None:
        return None
    return round((celsius * 9 / 5) + 32, 2)


def fahrenheit_to_celsius(fahrenheit: float | None) -> float | None:
    """Convert Fahrenheit to Celsius."""
    if fahrenheit is None:
        return None
    return round((fahrenheit - 32) * 5 / 9, 2)


async def execute_command_with_error_handling(
    client: "ElectroluxApiClient",
    pnc_id: str,
    command: dict[str, Any],
    entity_attr: str,
    logger: logging.Logger,
    capability: dict[str, Any] | None = None,
) -> Any:
    """Execute command with standardized error handling.

    Args:
        client: API client instance
        pnc_id: Appliance ID
        command: Command dictionary to send
        entity_attr: Entity attribute name (for logging)
        logger: Logger instance
        capability: Capability definition for enhanced error messages

    Returns:
        Command result

    Raises:
        HomeAssistantError: With user-friendly message
    """
    logger.debug("Executing command for %s: %s", entity_attr, command)

    try:
        result = await client.execute_appliance_command(pnc_id, command)
        logger.debug("Command succeeded for %s: %s", entity_attr, result)
        return result

    except Exception as ex:
        # Use shared error mapping function
        raise map_command_error_to_home_assistant_error(
            ex, entity_attr, logger, capability
        ) from ex


def string_to_boolean(value: str | None, fallback=True) -> bool | str | None:
    """Convert a string input to boolean."""
    if value is None:
        return None

    on_values = {
        "active blocking",  # descalingReminderState: blocking problem
        "active not blocking",  # descalingReminderState: non-blocking problem (still a problem)
        "charging",
        "connected",
        "detected",
        "enabled",
        "home",
        "hot",
        "inserted",
        "light",
        "locked",
        "locking",
        "motion",
        "moving",
        "occupied",
        "on",
        "open",
        "plugged",
        "power",
        "problem",
        "running",
        "smoke",
        "sound",
        "steam tank empty",
        "tampering",
        "true",
        "unsafe",
        "update available",
        "vibration",
        "wet",
        "yes",
    }

    off_values = {
        "away",
        "clear",
        "closed",
        "disabled",
        "disconnected",
        "dry",
        "false",
        "no",
        "no light",
        "no motion",
        "no power",
        "no problem",
        "no smoke",
        "no sound",
        "no tampering",
        "no vibration",
        "normal",
        "not active",  # descalingReminderState: no descaling needed
        "not charging",
        "not inserted",
        "not occupied",
        "not running",
        "off",
        "safe",
        "steam tank full",
        "stopped",
        "unlocked",
        "unlocking",
        "unplugged",
        "up-to-date",
        "up to date",
    }

    normalize_input = re.sub(r"\s+", " ", value.replace("_", " ").strip().lower())

    if normalize_input in on_values:
        return True
    if normalize_input in off_values:
        return False
    _LOGGER.debug("Electrolux unable to convert value to boolean")
    if fallback:
        return value
    return False


def _parse_error_detail_for_user_message(
    detail_lower: str, capability: dict[str, Any] | None = None
) -> str | None:
    """Parse error detail to extract user-friendly error message.

    Returns a specific error message if the detail matches known patterns,
    otherwise returns None to use the generic message.
    """
    if "invalid step" in detail_lower:
        # Get step value from capability for dynamic error message
        step_value = "valid"
        if capability:
            step = capability.get("step")
            if step is not None:
                step_value = str(step)
        return f"Invalid Value: This appliance requires increments of {step_value}."

    if "type mismatch" in detail_lower:
        return "Integration Error: Formatting mismatch (Expected Boolean/String)."

    # Additional patterns for remote control issues
    if any(phrase in detail_lower for phrase in REMOTE_CONTROL_ERROR_PHRASES):
        return "Remote control is disabled for this appliance. Please enable it on the appliance's control panel."

    if "temporary_locked" in detail_lower or "temporary lock" in detail_lower:
        return "Remote control is temporarily locked. Please open and close the appliance door, then press the physical 'Remote Start' button on the appliance."

    if any(
        phrase in detail_lower
        for phrase in [
            "not supported by program",
            "program does not allow",
            "not allowed in current program",
            "program restriction",
            "not available for this program",
            "program not supported",
        ]
    ):
        return "Setting not available for the selected program. Please change the program or check program settings."

    if any(
        phrase in detail_lower
        for phrase in [
            "food probe not inserted",
            "probe not inserted",
            "food probe not detected",
            "probe not detected",
            "food probe required",
            "probe required",
        ]
    ):
        return "Food probe must be inserted to set probe temperature. Please insert the food probe into the appliance."

    if any(
        phrase in detail_lower
        for phrase in [
            "door open",
            "door is open",
            "close door",
            "door must be closed",
            "door not closed",
        ]
    ):
        return "Appliance door must be closed to perform this operation. Please close the appliance door."

    if any(
        phrase in detail_lower
        for phrase in [
            "appliance busy",
            "appliance running",
            "cycle in progress",
            "operation in progress",
            "appliance active",
            "cannot change while running",
        ]
    ):
        return "Cannot change settings while appliance is running. Please wait for the current operation to complete."

    if any(
        phrase in detail_lower
        for phrase in [
            "child lock active",
            "child lock enabled",
            "safety lock active",
            "safety lock enabled",
            "control locked",
            "controls locked",
        ]
    ):
        return "Controls are locked. Please disable the child lock or safety lock on the appliance."

    if "string value not allowed" in detail_lower:
        return "Command not available in the appliance's current state."

    return None


def map_command_error_to_home_assistant_error(
    ex: Exception,
    entity_attr: str,
    logger: logging.Logger,
    capability: dict[str, Any] | None = None,
) -> HomeAssistantError:
    """Map command exceptions to user-friendly Home Assistant errors.

    Uses multiple detection methods for robustness:
    1. Structured error response parsing
    2. HTTP status code detection
    3. Improved string pattern matching

    Args:
        ex: The original exception
        entity_attr: Entity attribute name (for logging)
        logger: Logger instance

    Returns:
        HomeAssistantError with user-friendly message
    """

    # Check for authentication errors first - these should be handled differently
    error_str = str(ex).lower()
    if any(
        keyword in error_str
        for keyword in [
            "401",
            "unauthorized",
            "forbidden",
            "invalid grant",
            "token",
            "auth",
        ]
    ):
        logger.warning(
            "Authentication error detected for %s: %s",
            entity_attr,
            ex,
        )
        raise AuthenticationError("Authentication failed") from ex

    # Method 1: Try to parse structured error response and extract status code
    error_data = None
    status_code = None
    try:
        # Extract status code first
        status_code = getattr(ex, "status", None)
        if not status_code and hasattr(ex, "response"):
            response = getattr(ex, "response")
            status_code = getattr(response, "status", None)
        if not status_code and hasattr(ex, "status_code"):
            status_code = getattr(ex, "status_code")

        # Check if exception has response data
        if hasattr(ex, "response") and getattr(ex, "response", None):
            response = getattr(ex, "response")
            if hasattr(response, "json") and callable(getattr(response, "json", None)):
                try:
                    error_data = response.json()
                except Exception:
                    pass  # JSON parsing failed, try text parsing next
            elif hasattr(response, "text"):
                try:
                    error_data = json.loads(response.text)
                except Exception:
                    pass  # Text parsing failed, continue without error data
        # Check if exception has direct error data
        elif hasattr(ex, "error_data"):
            error_data = getattr(ex, "error_data")
        elif hasattr(ex, "details"):
            error_data = getattr(ex, "details")

        # If no structured data found, try parsing the exception message string
        if not error_data:

            ex_str = str(ex)
            # Look for JSON-like dict in the message: message='{"error": ...}' or message="{'error': ...}"
            match = re.search(r"message=['\"](\{.+?\})['\"]", ex_str)
            if match:
                try:
                    # Replace single quotes with double quotes for valid JSON
                    json_str = match.group(1).replace("'", '"')
                    error_data = json.loads(json_str)
                except Exception:
                    pass  # Parsing failed
    except Exception:
        # Parsing failed, continue to other methods
        pass

    # Format error data and status code for logging
    error_data_str = ""
    if error_data:
        try:
            error_data_str = f" | API Response: {json.dumps(error_data)}"
        except Exception:
            error_data_str = f" | API Response: {error_data}"

    status_code_str = f" | HTTP {status_code}" if status_code else ""

    # If we got structured error data, use it
    if error_data and isinstance(error_data, dict):
        error_code = (
            error_data.get("code")
            or error_data.get("error_code")
            or error_data.get("error")
            or error_data.get("status")
        )

        # Map error codes to user-friendly messages
        ERROR_CODE_MAPPING = {
            "REMOTE_CONTROL_DISABLED": "Remote control is disabled for this appliance. Please enable it on the appliance's control panel.",
            "RC_DISABLED": "Remote control is disabled for this appliance. Please enable it on the appliance's control panel.",
            "REMOTE_CONTROL_NOT_ACTIVE": "Remote control is disabled for this appliance. Please enable it on the appliance's control panel.",
            "APPLIANCE_OFFLINE": "Appliance is disconnected or not available. Check the appliance's network connection.",
            "DEVICE_OFFLINE": "Appliance is disconnected or not available. Check the appliance's network connection.",
            "CONNECTION_LOST": "Appliance is disconnected or not available. Check the appliance's network connection.",
            "RATE_LIMIT_EXCEEDED": "Too many commands sent. Please wait a moment and try again.",
            "RATE_LIMIT": "Too many commands sent. Please wait a moment and try again.",
            "TOO_MANY_REQUESTS": "Too many commands sent. Please wait a moment and try again.",
            "COMMAND_VALIDATION_ERROR": "Command not accepted by appliance. Check that the appliance supports this operation.",
            "VALIDATION_ERROR": "Command not accepted by appliance. Check that the appliance supports this operation.",
            "INVALID_COMMAND": "Command not accepted by appliance. Check that the appliance supports this operation.",
        }

        if error_code and str(error_code).upper() in ERROR_CODE_MAPPING:
            user_message = ERROR_CODE_MAPPING[str(error_code).upper()]

            # Special handling for COMMAND_VALIDATION_ERROR with remote control issues
            if str(error_code).upper() == "COMMAND_VALIDATION_ERROR":
                if error_data and isinstance(error_data, dict):
                    detail = error_data.get("detail") or error_data.get("message", "")
                    if detail and "remote control" in str(detail).lower():
                        user_message = "Remote control is disabled for this appliance. Please enable it on the appliance's control panel."
                        logger.warning(
                            "Command failed for %s: %s (overridden to remote control disabled)%s%s",
                            entity_attr,
                            ex,
                            status_code_str,
                            error_data_str,
                        )
                        return HomeAssistantError(user_message)

            # Enhanced error code handling with detail parsing
            detail_message = None
            try:
                # Try to extract detail from error response
                if error_data and isinstance(error_data, dict):
                    detail = error_data.get("detail") or error_data.get("message")
                    logger.debug(
                        "Error code detail parsing: error_data=%s, detail=%s",
                        error_data,
                        detail,
                    )
                    if detail:
                        detail_lower = str(detail).lower()
                        # Try pattern-based parsing first
                        detail_message = _parse_error_detail_for_user_message(
                            detail_lower, capability
                        )
                        # If no pattern matched but we have a detail, use the raw API response
                        if (
                            not detail_message
                            and str(detail) != "Command validation failed"
                        ):
                            detail_message = f"Command not accepted: {detail}"

            except Exception:
                # If detail parsing fails, continue with generic message
                pass

            if detail_message:
                user_message = detail_message

            logger.warning(
                "Command failed for %s: error_code=%s%s%s | %s",
                entity_attr,
                error_code,
                status_code_str,
                error_data_str,
                ex,
            )
            return HomeAssistantError(user_message)

    # Check for Type mismatch errors specifically (prevent false positive remote control errors)
    error_str = str(ex).lower()
    if "type mismatch" in error_str:
        logger.warning(
            "Command failed for %s: type mismatch%s%s | %s",
            entity_attr,
            status_code_str,
            error_data_str,
            ex,
        )
        return HomeAssistantError(
            f"Integration Error: Data type mismatch for {entity_attr}. Expected Boolean.",
            translation_domain=DOMAIN,
            translation_key="type_mismatch",
            translation_placeholders={"attr": entity_attr},
        )

    # Method 2: Check HTTP status codes (already extracted above)
    if status_code:
        STATUS_CODE_MAPPING = {
            403: "Remote control is disabled for this appliance. Please enable it on the appliance's control panel.",
            406: "Command not accepted by appliance. Check that the appliance supports this operation.",
            429: "Too many commands sent. Please wait a moment and try again.",
            503: "Appliance is disconnected or not available. Check the appliance's network connection.",
        }

        if status_code in STATUS_CODE_MAPPING:
            user_message = STATUS_CODE_MAPPING[status_code]

            # Enhanced 406 error handling with detail parsing
            if status_code == 406:
                # Special handling for 406 with remote control issues
                if error_data and isinstance(error_data, dict):
                    detail = error_data.get("detail") or error_data.get("message", "")
                    if detail and "remote control" in str(detail).lower():
                        user_message = "Remote control is disabled for this appliance. Please enable it on the appliance's control panel."
                        logger.warning(
                            "Command failed for %s: HTTP %d%s (overridden to remote control disabled) | %s",
                            entity_attr,
                            status_code,
                            error_data_str,
                            ex,
                        )
                        return HomeAssistantError(user_message)

                detail_message = None
                try:
                    # Try to extract detail from error response
                    if error_data and isinstance(error_data, dict):
                        detail = error_data.get("detail") or error_data.get("message")
                        logger.debug(
                            "406 error detail parsing: error_data=%s, detail=%s",
                            error_data,
                            detail,
                        )
                        if detail:
                            detail_lower = str(detail).lower()
                            # Try pattern-based parsing first
                            detail_message = _parse_error_detail_for_user_message(
                                detail_lower, capability
                            )
                            # If no pattern matched but we have a detail, use the raw API response
                            if (
                                not detail_message
                                and str(detail) != "Command validation failed"
                            ):
                                detail_message = f"Command not accepted: {detail}"
                # If detail parsing fails, continue with generic message
                except Exception:
                    pass  # Detail parsing failed, use generic message

                if detail_message:
                    user_message = detail_message

            logger.warning(
                "Command failed for %s: HTTP %d%s | %s",
                entity_attr,
                status_code,
                error_data_str,
                ex,
            )
            return HomeAssistantError(user_message)

    # Method 3: Improved string pattern matching (fallback)
    error_msg = str(ex).lower()

    # More comprehensive pattern matching
    if any(phrase in error_msg for phrase in REMOTE_CONTROL_ERROR_PHRASES):
        logger.warning(
            "Command failed for %s: remote control disabled%s%s | %s",
            entity_attr,
            status_code_str,
            error_data_str,
            ex,
        )
        return HomeAssistantError(
            "Remote control is disabled for this appliance. "
            "Please enable it on the appliance's control panel.",
            translation_domain=DOMAIN,
            translation_key="remote_control_disabled",
        )

    elif any(
        phrase in error_msg
        for phrase in [
            "disconnected",
            "offline",
            "not available",
            "connection lost",
            "device offline",
            "appliance offline",
        ]
    ):
        logger.warning(
            "Command failed for %s: appliance offline%s%s | %s",
            entity_attr,
            status_code_str,
            error_data_str,
            ex,
        )
        return HomeAssistantError(
            "Appliance is disconnected or not available. "
            "Check the appliance's network connection.",
            translation_domain=DOMAIN,
            translation_key="appliance_disconnected",
        )

    elif any(
        phrase in error_msg
        for phrase in [
            "rate limit",
            "too many requests",
            "rate exceeded",
            "throttled",
            "429",
        ]
    ):
        logger.warning(
            "Command failed for %s: rate limited%s%s | %s",
            entity_attr,
            status_code_str,
            error_data_str,
            ex,
        )
        return HomeAssistantError(
            "Too many commands sent. Please wait a moment and try again.",
            translation_domain=DOMAIN,
            translation_key="command_rate_limited",
        )

    elif any(
        phrase in error_msg
        for phrase in [
            "command validation",
            "validation error",
            "invalid command",
            "not acceptable",
            "406",
        ]
    ):
        # Try to extract detail from error_data for more specific message
        detail_msg = None
        if error_data and isinstance(error_data, dict):
            detail = error_data.get("detail") or error_data.get("message")
            if detail:
                detail_lower = str(detail).lower()
                # Try pattern-based parsing first
                detail_msg = _parse_error_detail_for_user_message(
                    detail_lower, capability
                )
                # If no pattern matched but we have a detail, use the raw API response
                if not detail_msg and str(detail) != "Command validation failed":
                    detail_msg = f"Command not accepted: {detail}"

        if not detail_msg:
            # Fallback: try to extract useful info from exception string
            ex_str = str(ex)
            if len(ex_str) > 0 and len(ex_str) < 200:
                detail_msg = f"Command not accepted by appliance: {ex_str}"
            else:
                detail_msg = "Command not accepted by appliance. Check that the appliance supports this operation."

        logger.warning(
            "Command failed for %s: command validation error%s%s | %s",
            entity_attr,
            status_code_str,
            error_data_str,
            ex,
        )
        return HomeAssistantError(detail_msg)

    # Default: Generic error
    logger.error(
        "Command failed for %s with unexpected error%s%s | %s",
        entity_attr,
        status_code_str,
        error_data_str,
        ex,
    )
    return HomeAssistantError(f"Command failed: {ex}. Check logs for details.")


def get_capability(
    capabilities: dict[str, Any], key: str
) -> int | float | str | bool | dict[str, Any] | None:
    """Safely get a capability value, handling both dict and direct value formats.

    For constant capabilities, returns the 'default' value if the capability is a dict.
    For other capabilities, returns the value directly.

    Args:
        capabilities: The capabilities dictionary
        key: The capability key to look up

    Returns:
        The capability value, or None if not found
    """
    if key not in capabilities:
        return None

    value = capabilities[key]
    if isinstance(value, dict):
        # For dict capabilities (like constants), return the default value
        return value.get("default")
    else:
        # For direct value capabilities, return the value as-is
        return value


def format_command_for_appliance(
    capability: dict[str, Any] | None, attr: str, value: Any
) -> Any:
    """Format a command value according to the appliance capability specifications.

    This function dynamically formats Home Assistant command values to match
    the expected format for the Electrolux appliance based on capability metadata.

    Args:
        capability: The capability definition for the attribute (can be None)
        attr: The attribute name (e.g., 'cavityLight', 'targetTemperatureC')
        value: The raw value from Home Assistant

    Returns:
        The formatted value ready for the appliance API
    """
    if not capability or not isinstance(capability, dict):
        # Fallback to original behavior if no capability info
        if isinstance(value, bool):
            return "ON" if value else "OFF"
        return value

    # Get the capability type
    cap_type = capability.get("type", "").lower()

    if cap_type == "boolean":
        # Boolean type - return raw Python bool
        if isinstance(value, bool):
            return value
        # Handle string representations
        if isinstance(value, str):
            return value.lower() in ("true", "on", "1", "yes")
        # Handle numeric representations
        return bool(value)

    elif "temperature" in attr.lower() or cap_type in ("number", "float", "integer"):
        # Temperature or numeric type - ensure float and apply step and range constraints
        try:
            numeric_value = float(value)

            # Get min/max bounds
            min_val = capability.get("min")
            max_val = capability.get("max")

            # Apply step constraints as safety measure (sliders should prevent invalid values, but this handles edge cases)
            step = capability.get("step")
            if step is not None:
                step = float(step)
                if step > 0:
                    # Calculate step base, aligning min to nearest step boundary if needed
                    # Example: min=15.56, step=1.0 -> step_base=16.0 (prevents calculating 23.56 from 24.0)
                    step_base = min_val if min_val is not None else 0
                    # Align step_base to step boundaries (fixes misaligned API values like 15.56 with step 1.0)
                    step_base = round(step_base / step) * step
                    steps_from_base = (numeric_value - step_base) / step
                    # Round to nearest valid step
                    numeric_value = step_base + round(steps_from_base) * step

            # Clamp to min/max bounds
            if min_val is not None:
                numeric_value = max(numeric_value, float(min_val))
            if max_val is not None:
                numeric_value = min(numeric_value, float(max_val))

            return numeric_value

        except (ValueError, TypeError):
            _LOGGER.warning(
                "Invalid numeric value %s for attribute %s, using as-is", value, attr
            )
            return value

    elif cap_type in ("string", "enum") or "values" in capability:
        # String or enum type - validate against allowed values
        values_dict = capability.get("values", {})

        if isinstance(values_dict, dict) and values_dict:
            # Special case: boolean input for string-based ON/OFF switches
            if isinstance(value, bool):
                # Check if this is an ON/OFF switch (case-insensitive)
                upper_values = {str(k).upper() for k in values_dict.keys()}
                if upper_values == {"ON", "OFF"}:
                    # Convert boolean to appropriate string value
                    target_value = "ON" if value else "OFF"
                    # Find the exact key with matching case
                    for key in values_dict.keys():
                        if key.upper() == target_value:
                            return key
                    # Fallback to uppercase if exact match not found
                    return target_value

            # Check if the value is a valid key in the values dict
            if str(value) in values_dict:
                return str(value)
            else:
                # Try to find a matching value by case-insensitive comparison
                value_str = str(value).lower()
                for key in values_dict.keys():
                    if key.lower() == value_str:
                        return key

                _LOGGER.warning(
                    "Value %s not found in allowed values for %s: %s",
                    value,
                    attr,
                    list(values_dict.keys()),
                )
                # Return the original value if not found - let the API handle validation
                return value
        else:
            # No values constraint, return as string
            return str(value)

    else:
        # Unknown or unspecified type - use fallback logic
        if isinstance(value, bool):
            return "ON" if value else "OFF"
        return value
