"""Utlities for the Electrolux platform."""

import asyncio
import base64
import logging
import re
import time
from typing import Any, Awaitable, Callable

from electrolux_group_developer_sdk.auth.auth_data import (
    AuthData,  # type: ignore[import-untyped]
)
from electrolux_group_developer_sdk.auth.token_manager import (
    TokenManager,  # type: ignore[import-untyped]
)
from electrolux_group_developer_sdk.client.appliance_client import (
    ApplianceClient,  # type: ignore[import-untyped]
)
from electrolux_group_developer_sdk.client.client_util import (
    request,  # type: ignore[import-untyped]
)
from electrolux_group_developer_sdk.config import (
    TOKEN_REFRESH_URL,  # type: ignore[import-untyped]
)
from electrolux_group_developer_sdk.constants import (  # type: ignore[import-untyped]
    POST,
    REFRESH_TOKEN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import issue_registry as issue_registry

from .const import (
    ACCESS_TOKEN_VALIDITY_SECONDS,
    CONF_NOTIFICATION_DEFAULT,
    CONF_NOTIFICATION_DIAG,
    CONF_NOTIFICATION_WARNING,
    DOMAIN,
    NAME,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)

# Common error pattern lists for reuse across functions
REMOTE_CONTROL_ERROR_PHRASES = [
    "remote control disabled",
    "remote control not enabled",
    "remote control is not enabled",
    "remote control not active",
    "remote control is not active",
    "remote control off",
    "rc disabled",
    "rc not enabled",
    "rc not active",
]


class CommandError(Exception):
    """Base exception for command errors."""

    pass


class RemoteControlDisabledError(CommandError):
    """Remote control is disabled."""

    pass


class ApplianceOfflineError(CommandError):
    """Appliance is disconnected."""

    pass


class CommandValidationError(CommandError):
    """Command validation failed."""

    pass


class RateLimitError(CommandError):
    """Rate limit exceeded."""

    pass


class AuthenticationError(CommandError):
    """Authentication failed - tokens expired or invalid."""

    pass


class NetworkError(CommandError):
    """Network connectivity error."""

    pass


def get_electrolux_session(
    api_key, access_token, refresh_token, client_session, hass=None, config_entry=None
) -> "ElectroluxApiClient":
    """Return Electrolux API Session.

    Note: client_session is currently unused by the underlying SDK but is kept
    for future compatibility when the SDK supports passing in a shared aiohttp session.
    """
    return ElectroluxApiClient(api_key, access_token, refresh_token, hass, config_entry)


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
    if seconds == -1:
        return -1
    return round(seconds / 60)


def time_minutes_to_seconds(minutes: float | None) -> int | None:
    """Convert minutes to seconds."""
    if minutes is None:
        return None
    if minutes == -1:
        return -1
    return int(minutes) * 60


async def retry_with_backoff(
    coro,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    logger: logging.Logger | None = None,
) -> Any:
    """Execute a coroutine with exponential backoff retry logic.

    Args:
        coro: The coroutine to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to multiply delay by on each retry
        logger: Logger instance for debug messages

    Returns:
        The result of the coroutine

    Raises:
        The last exception encountered if all retries fail
    """
    if logger is None:
        logger = _LOGGER

    last_exception = None
    delay = base_delay

    for attempt in range(max_retries + 1):
        try:
            return await coro
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as ex:
            last_exception = ex
            if attempt < max_retries:
                logger.warning(
                    "Network error on attempt %d/%d: %s. Retrying in %.1f seconds...",
                    attempt + 1,
                    max_retries + 1,
                    ex,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)
            else:
                logger.error(
                    "Network error failed after %d attempts: %s",
                    max_retries + 1,
                    ex,
                )
        except Exception as ex:
            # For non-network errors, don't retry
            logger.debug("Non-retryable error: %s", ex)
            raise

    # If we get here, all retries failed with network errors
    if last_exception:
        raise last_exception
    else:
        raise NetworkError("All retry attempts failed with unknown errors")


def validate_api_response(
    response: Any, expected_keys: list[str] | None = None
) -> bool:
    """Validate API response structure.

    Args:
        response: The API response to validate
        expected_keys: List of keys that should be present in the response

    Returns:
        True if response is valid, False otherwise
    """
    if response is None:
        _LOGGER.warning("API response is None")
        return False

    if expected_keys:
        if not isinstance(response, dict):
            _LOGGER.warning("API response is not a dict: %s", type(response))
            return False

        missing_keys = [key for key in expected_keys if key not in response]
        if missing_keys:
            _LOGGER.warning("API response missing expected keys: %s", missing_keys)
            return False

    return True


async def safe_api_call(
    coro,
    operation_name: str,
    logger: logging.Logger | None = None,
    retry_network_errors: bool = True,
) -> Any:
    """Execute an API call with comprehensive error handling.

    Args:
        coro: The coroutine to execute
        operation_name: Name of the operation for logging
        logger: Logger instance
        retry_network_errors: Whether to retry on network errors

    Returns:
        The result of the coroutine

    Raises:
        HomeAssistantError: With user-friendly message
        ConfigEntryAuthFailed: For authentication errors
    """
    if logger is None:
        logger = _LOGGER

    try:
        if retry_network_errors:
            return await retry_with_backoff(
                coro,
                max_retries=2,
                base_delay=1.0,
                logger=logger,
            )
        else:
            return await coro

    except (ConnectionError, TimeoutError, asyncio.TimeoutError) as ex:
        logger.error("Network error during %s: %s", operation_name, ex)
        raise HomeAssistantError(
            f"Network connection failed during {operation_name}. Please check your internet connection."
        ) from ex

    except Exception as ex:
        error_str = str(ex).lower()

        # Check for authentication errors
        if any(
            keyword in error_str
            for keyword in [
                "401",
                "unauthorized",
                "invalid grant",
                "token",
                "forbidden",
                "auth",
            ]
        ):
            logger.warning("Authentication error during %s: %s", operation_name, ex)
            raise ConfigEntryAuthFailed(
                "Authentication failed - please reauthenticate"
            ) from ex

        # Check for rate limiting
        if any(
            keyword in error_str
            for keyword in ["429", "rate limit", "too many requests", "throttled"]
        ):
            logger.warning("Rate limit exceeded during %s: %s", operation_name, ex)
            raise HomeAssistantError(
                "Too many requests sent. Please wait a moment and try again."
            ) from ex

        # Generic error
        logger.error("Unexpected error during %s: %s", operation_name, ex)
        raise HomeAssistantError(
            f"Operation failed: {operation_name}. Check logs for details."
        ) from ex


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
        "charging",
        "connected",
        "detected",
        "enabled",
        "home",
        "hot",
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
        "not charging",
        "not occupied",
        "not running",
        "off",
        "safe",
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

    # Method 1: Try to parse structured error response
    error_data = None
    try:
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
                    import json

                    error_data = json.loads(response.text)
                except Exception:
                    pass  # Text parsing failed, continue without error data
        # Check if exception has direct error data
        elif hasattr(ex, "error_data"):
            error_data = getattr(ex, "error_data")
        elif hasattr(ex, "details"):
            error_data = getattr(ex, "details")
    except Exception:
        # Parsing failed, continue to other methods
        pass

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
                            "Command failed for %s: %s (overridden to remote control disabled)",
                            entity_attr,
                            ex,
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
                        detail_message = _parse_error_detail_for_user_message(
                            detail_lower, capability
                        )

            except Exception:
                # If detail parsing fails, continue with generic message
                pass

            if detail_message:
                user_message = detail_message

            logger.warning(
                "Command failed for %s: %s - %s",
                entity_attr,
                error_code,
                ex,
            )
            return HomeAssistantError(user_message)

    # Check for Type mismatch errors specifically (prevent false positive remote control errors)
    error_str = str(ex).lower()
    if "type mismatch" in error_str:
        logger.warning(
            "Command failed for %s: type mismatch - %s",
            entity_attr,
            ex,
        )
        return HomeAssistantError(
            f"Integration Error: Data type mismatch for {entity_attr}. Expected Boolean."
        )

    # Method 2: Check HTTP status codes
    status_code = None
    try:
        status_code = getattr(ex, "status", None)
        if not status_code and hasattr(ex, "response"):
            response = getattr(ex, "response")
            status_code = getattr(response, "status", None)
        if not status_code and hasattr(ex, "status_code"):
            status_code = getattr(ex, "status_code")
    except Exception:
        pass  # Safely handle any attribute access errors

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
                            "Command failed for %s: HTTP %d - %s (overridden to remote control disabled)",
                            entity_attr,
                            status_code,
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
                            detail_message = _parse_error_detail_for_user_message(
                                detail_lower, capability
                            )
                # If detail parsing fails, continue with generic message
                except Exception:
                    pass  # Detail parsing failed, use generic message

                if detail_message:
                    user_message = detail_message

            logger.warning(
                "Command failed for %s: HTTP %d - %s",
                entity_attr,
                status_code,
                ex,
            )
            return HomeAssistantError(user_message)

    # Method 3: Improved string pattern matching (fallback)
    error_msg = str(ex).lower()

    # More comprehensive pattern matching
    if any(phrase in error_msg for phrase in REMOTE_CONTROL_ERROR_PHRASES):
        logger.warning(
            "Command failed for %s: remote control disabled - %s",
            entity_attr,
            ex,
        )
        return HomeAssistantError(
            "Remote control is disabled for this appliance. "
            "Please enable it on the appliance's control panel."
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
            "Command failed for %s: appliance offline - %s",
            entity_attr,
            ex,
        )
        return HomeAssistantError(
            "Appliance is disconnected or not available. "
            "Check the appliance's network connection."
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
            "Command failed for %s: rate limited - %s",
            entity_attr,
            ex,
        )
        return HomeAssistantError(
            "Too many commands sent. Please wait a moment and try again."
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
        logger.warning(
            "Command failed for %s: command validation error - %s",
            entity_attr,
            ex,
        )
        return HomeAssistantError(
            "Command not accepted by appliance. Check that the appliance supports this operation."
        )

    # Default: Generic error
    logger.error(
        "Command failed for %s with unexpected error: %s",
        entity_attr,
        ex,
    )
    return HomeAssistantError(f"Command failed: {ex}. Check logs for details.")


def get_capability(capabilities: dict[str, Any], key: str) -> Any:
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
    capability: dict[str, Any], attr: str, value: Any
) -> Any:
    """Format a command value according to the appliance capability specifications.

    This function dynamically formats Home Assistant command values to match
    the expected format for the Electrolux appliance based on capability metadata.

    Args:
        capability: The capability definition for the attribute
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
                    # For sliders, we still want to ensure step compliance
                    # Calculate from a reasonable minimum (0 for most cases if min not specified)
                    step_base = min_val if min_val is not None else 0
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


class _TokenRefreshHandler(logging.Handler):
    """Logging handler to detect token refresh failures and report to HA issue registry."""

    def __init__(self, client: "ElectroluxApiClient", hass: HomeAssistant) -> None:
        super().__init__()
        self._client = client
        self._hass = hass

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            lmsg = msg.lower()
            # Only match messages indicating PERMANENT token refresh failure (not normal expiration)
            # The SDK handles normal access token expiration automatically
            permanent_token_error_indicators = [
                "refresh token is invalid",
                "invalid grant",
                "invalid refresh token",
                "refresh token expired",
            ]
            is_permanent_token_error = any(
                indicator in lmsg for indicator in permanent_token_error_indicators
            )

            if is_permanent_token_error:
                try:
                    # Schedule the async issue creation on the HA event loop
                    self._hass.loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self._client._trigger_reauth(msg))
                    )
                except Exception:
                    _LOGGER.exception("Failed to schedule token refresh issue creation")
        except Exception:
            _LOGGER.exception("TokenRefreshHandler emit failed")


class ElectroluxTokenManager(TokenManager):
    """Custom token manager that captures token expiration information."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        api_key: str,
        on_token_update: Callable[[str, str, str], None] | None = None,
    ):
        """Initialize the custom token manager."""
        super().__init__(
            access_token, refresh_token, api_key, on_token_update=on_token_update
        )
        self._on_token_update_with_expiry: (
            Callable[[str, str, str, int], None] | None
        ) = None
        self._on_auth_error: Callable[[str], Awaitable[None]] | None = None
        self._refresh_lock = asyncio.Lock()
        self._last_refresh_time = 0
        self._expires_at = 0  # Store token expiration timestamp
        self._last_failed_refresh = 0  # Track failed refresh attempts

    async def get_auth_data(self) -> AuthData:
        """Get authentication data, refreshing tokens if necessary.

        This method provides proactive token refresh but relies on refresh_token()
        for synchronization since refresh_token() now acquires its own lock.
        """
        # Check if token needs refresh (no lock here - refresh_token() handles it)
        current_time = int(time.time())
        if self._expires_at and (self._expires_at - current_time <= 900):  # 15 minutes
            _LOGGER.debug("get_auth_data: Token expired or expiring soon, refreshing")
            success = await self.refresh_token()
            if not success:
                _LOGGER.warning(
                    "get_auth_data: Token refresh failed, returning stale token. "
                    "Reauthentication may be required."
                )
        return self._auth_data

    def set_token_update_callback_with_expiry(
        self, callback: Callable[[str, str, str, int], None]
    ) -> None:
        """Set callback that includes expiration timestamp."""
        self._on_token_update_with_expiry = callback

    def set_auth_error_callback(
        self, callback: Callable[[str], Awaitable[None]]
    ) -> None:
        """Set callback for authentication errors."""
        self._on_auth_error = callback

    async def refresh_token(self) -> bool:
        """Refresh the access token and capture expiration information.

        This method is thread-safe and can be called concurrently from anywhere.
        It acquires the refresh lock internally to prevent race conditions.

        CRITICAL FIX: This method now acquires its own lock, preventing race
        conditions when the SDK's ApplianceClient calls it directly in response
        to 401 errors.
        """
        async with self._refresh_lock:  # CRITICAL FIX: Acquire lock here!
            current_time = int(time.time())
            _LOGGER.debug(
                f"TokenManager refresh_token: Starting token refresh process at {current_time}"
            )

            # Double-check token freshness (another task may have just refreshed while we waited for lock)
            if self._expires_at and (
                self._expires_at - current_time > 900
            ):  # 15 minutes
                remaining_seconds = self._expires_at - current_time
                _LOGGER.debug(
                    f"TokenManager refresh_token: Token already fresh ({remaining_seconds}s remaining), skipping refresh"
                )
                return True

            # Check retry cooldown: don't attempt refresh if we failed recently
            if current_time - self._last_failed_refresh < 60:
                cooldown_remaining = 60 - (current_time - self._last_failed_refresh)
                _LOGGER.debug(
                    f"TokenManager refresh_token: Refresh on cooldown, {cooldown_remaining}s remaining after last failure"
                )
                return False

            _LOGGER.debug("TokenManager refresh_token: Preparing refresh request")
            auth_data = self._auth_data

            if not auth_data or auth_data.refresh_token is None:
                _LOGGER.error("TokenManager refresh_token: Refresh token is missing")
                from homeassistant.exceptions import ConfigEntryAuthFailed

                raise ConfigEntryAuthFailed("Missing refresh token")

            payload = {REFRESH_TOKEN: auth_data.refresh_token}
            _LOGGER.debug(
                f"TokenManager refresh_token: Sending refresh request to {TOKEN_REFRESH_URL}"
            )

            try:
                _LOGGER.debug("TokenManager refresh_token: Making HTTP request")
                data = await request(
                    method=POST, url=TOKEN_REFRESH_URL, json_body=payload
                )
                _LOGGER.debug("TokenManager refresh_token: HTTP request successful")

                # Calculate expiration timestamp
                expires_in = data.get("expiresIn", ACCESS_TOKEN_VALIDITY_SECONDS)
                expires_at = int(time.time()) + expires_in
                _LOGGER.debug(
                    f"TokenManager refresh_token: Token expires in {expires_in}s, expires_at: {expires_at}"
                )

                # Update with new tokens
                _LOGGER.debug("TokenManager refresh_token: Updating token data")
                self.update_with_expiry(
                    access_token=data["accessToken"],
                    refresh_token=data["refreshToken"],
                    api_key=auth_data.api_key,
                    expires_at=expires_at,
                )

                # Update last refresh timestamp and clear failed refresh counter
                self._last_refresh_time = current_time
                self._last_failed_refresh = 0  # Clear the failure timestamp on success
                _LOGGER.debug(
                    f"TokenManager refresh_token: Token refresh completed successfully at {current_time}"
                )
                return True

            except Exception as e:
                error_msg = str(e).lower()
                _LOGGER.debug(
                    f"TokenManager refresh_token: Exception during refresh: {e}"
                )
                # Check for permanent token errors (401/Invalid Grant)
                if any(
                    keyword in error_msg
                    for keyword in ["401", "invalid grant", "forbidden"]
                ):
                    _LOGGER.error(
                        f"TokenManager refresh_token: Permanent token error: {e}"
                    )
                    # Trigger reauthentication immediately
                    if self._on_auth_error:
                        _LOGGER.debug(
                            "TokenManager refresh_token: Triggering auth error callback"
                        )
                        await self._on_auth_error(f"Token refresh failed: {e}")
                    return False

                # For other errors, set cooldown and return False
                _LOGGER.error(f"TokenManager refresh_token: Token refresh failed: {e}")
                self._last_failed_refresh = current_time
                _LOGGER.debug(
                    f"TokenManager refresh_token: Set failed refresh timestamp to {current_time}"
                )
                return False

    def update_with_expiry(
        self, access_token: str, refresh_token: str, api_key: str, expires_at: int
    ) -> None:
        """Update the authentication data with expiration information."""
        # Call the enhanced callback if available
        if self._on_token_update_with_expiry:
            self._on_token_update_with_expiry(
                access_token, refresh_token, api_key, expires_at
            )
        # Fall back to standard callback
        elif self._on_token_update:
            self._on_token_update(access_token, refresh_token, api_key)

        self._auth_data = AuthData(access_token, refresh_token, api_key)
        self._expires_at = expires_at  # Store expiration timestamp for freshness checks


class ElectroluxApiClient:
    """Wrapper for the new Electrolux API client to maintain compatibility."""

    def __init__(
        self,
        api_key: str,
        access_token: str,
        refresh_token: str,
        hass: HomeAssistant | None = None,
        config_entry: ConfigEntry | None = None,
    ):
        """Initialize the API client."""
        # Explicitly annotate hass as optional HomeAssistant
        self.hass: HomeAssistant | None = hass
        self.config_entry: ConfigEntry | None = config_entry
        self._auth_failed = False  # Flag to indicate auth failure
        self.coordinator: Any = None  # Reference to coordinator for triggering refresh
        self._token_manager = ElectroluxTokenManager(
            access_token, refresh_token, api_key
        )
        # Set auth error callback to trigger reauthentication
        self._token_manager.set_auth_error_callback(self._trigger_reauth)
        self._client = ApplianceClient(self._token_manager)
        self._token_handler = None  # Track handler
        self._token_logger = None  # Track logger

        # Attach token refresh handler to surface token refresh failures as HA issues
        if hass:
            try:
                self._token_handler = _TokenRefreshHandler(self, hass)
                self._token_handler.setLevel(logging.ERROR)
                self._token_logger = logging.getLogger(
                    "electrolux_group_developer_sdk.auth.token_manager"
                )
                self._token_logger.addHandler(self._token_handler)
            except Exception:
                _LOGGER.exception("Failed to attach token refresh logger handler")

    def set_token_update_callback(self, callback):
        """Set the callback for token updates."""
        self._token_manager._on_token_update = callback

    def set_token_update_callback_with_expiry(self, callback):
        """Set the callback for token updates with expiration information."""
        self._token_manager.set_token_update_callback_with_expiry(callback)

    async def _trigger_reauth(self, message: str) -> None:
        """Trigger reauthentication by setting flag, creating issue, and forcing refresh."""
        _LOGGER.debug(f"_trigger_reauth: Triggering reauth due to: {message}")
        self._auth_failed = True
        _LOGGER.debug("_trigger_reauth: Set auth_failed flag to True")

        _LOGGER.debug(
            "_trigger_reauth: Reporting token refresh error to create HA issue"
        )
        await self._report_token_refresh_error(message)

        # Force an immediate coordinator refresh to trigger reauth
        if self.hass and self.coordinator:
            _LOGGER.debug(
                "_trigger_reauth: Forcing immediate coordinator refresh to trigger reauth"
            )
            self.hass.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.coordinator.async_refresh())
            )
            _LOGGER.debug("_trigger_reauth: Coordinator refresh task scheduled")
        else:
            _LOGGER.debug(
                "_trigger_reauth: Cannot force refresh - hass or coordinator not available"
            )

    async def _report_token_refresh_error(self, message: str) -> None:
        """Create an HA issue when token refresh fails so user can re-authenticate."""
        _LOGGER.debug(f"_report_token_refresh_error: Called with message: {message}")
        # Avoid passing None to Home Assistant APIs
        if not self.hass:
            _LOGGER.warning(
                "Token refresh failed but no Home Assistant instance available; skipping issue creation: %s",
                message,
            )
            return

        try:
            _LOGGER.debug("_report_token_refresh_error: Finding config entries")
            # Find the config entry
            entries = self.hass.config_entries.async_entries(DOMAIN)
            if entries:
                entry = entries[0]
                issue_id = f"invalid_refresh_token_{entry.entry_id}"
                _LOGGER.debug(
                    f"_report_token_refresh_error: Using entry {entry.entry_id} for issue ID {issue_id}"
                )
            else:
                issue_id = "invalid_refresh_token"
                _LOGGER.debug(
                    "_report_token_refresh_error: No entries found, using generic issue ID"
                )

            _LOGGER.warning("Token refresh failed: %s. Creating HA issue.", message)
            _LOGGER.debug(
                f"_report_token_refresh_error: Creating issue with ID {issue_id}"
            )
            issue_registry.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=True,
                is_persistent=True,
                severity=issue_registry.IssueSeverity.CRITICAL,
                translation_key="invalid_refresh_token",
                translation_placeholders={"message": message},
            )
            _LOGGER.debug("_report_token_refresh_error: HA issue created successfully")
        except Exception:
            _LOGGER.exception("Failed to create token refresh issue in Home Assistant")

    async def _handle_api_call(self, coro):
        """Wrap API calls to handle authentication errors."""
        _LOGGER.debug("_handle_api_call: Starting API call wrapper")
        try:
            result = await coro
            _LOGGER.debug("_handle_api_call: API call completed successfully")
            return result
        except Exception as ex:
            error_msg = str(ex).lower()
            _LOGGER.debug(f"_handle_api_call: Exception caught: {ex}")
            # Check for authentication-related errors
            if any(
                keyword in error_msg
                for keyword in [
                    "401",
                    "unauthorized",
                    "invalid grant",
                    "token",
                    "forbidden",
                ]
            ):
                # Trigger token refresh handler by logging the error
                _LOGGER.error("API call failed with authentication error: %s", ex)
                _LOGGER.debug(
                    "_handle_api_call: Authentication error detected, raising ConfigEntryAuthFailed"
                )
                # Also raise so coordinator can handle it
                from homeassistant.exceptions import ConfigEntryAuthFailed

                raise ConfigEntryAuthFailed(
                    "Authentication failed - token may be expired"
                ) from ex
            else:
                _LOGGER.debug("_handle_api_call: Non-authentication error, re-raising")
                # Re-raise other errors
                raise

    async def get_appliances_list(self):
        """Get list of appliances."""
        appliances = await self._handle_api_call(self._client.get_appliances())
        # Convert to the expected format
        result = []
        for appliance in appliances:
            # Try to extract model from PNC (Product Number Code)
            pnc = appliance.applianceId
            model_name = getattr(appliance, "model", "Unknown")
            if model_name == "Unknown" and pnc:
                # Extract model from PNC format like '944188772_00:31862190-443E07363DAB'
                pnc_parts = pnc.split("_")
                if len(pnc_parts) > 0:
                    model_part = pnc_parts[0]
                    # Use the first part as model if it looks like a model number
                    if model_part.isdigit() and len(model_part) >= 6:
                        model_name = model_part

            appliance_data = {
                "applianceId": appliance.applianceId,
                "applianceName": appliance.applianceName,
                "applianceType": appliance.applianceType,
                "connectionState": "connected",  # Assume connected
                "applianceData": {
                    "applianceName": appliance.applianceName,
                    "modelName": model_name,
                },
                "created": "2022-01-01T00:00:00.000Z",  # Mock creation date
            }
            _LOGGER.debug("API appliance list item processed")
            result.append(appliance_data)
        return result

    async def get_appliances_info(self, appliance_ids):
        """Get appliances info."""
        result = []
        for appliance_id in appliance_ids:
            try:
                details = await self._handle_api_call(
                    self._client.get_appliance_details(appliance_id)
                )
                # Try to extract model from PNC if API doesn't provide it
                # Note: Electrolux API often returns "Unknown" for model, but the PNC
                # contains the actual product code (e.g., "944188772") which is the most
                # specific model identifier available through the API
                model = getattr(details, "model", "Unknown")
                if model == "Unknown" and appliance_id:
                    # Extract model from PNC format like '944188772_00:31862190-443E07363DAB'
                    pnc_parts = appliance_id.split("_")
                    if len(pnc_parts) > 0:
                        model_part = pnc_parts[0]
                        # Use the first part as model if it looks like a model number
                        if model_part.isdigit() and len(model_part) >= 6:
                            model = model_part

                # Convert to expected format
                info = {
                    "pnc": appliance_id,
                    "brand": getattr(details, "brand", "Electrolux"),
                    "model": model,
                    "device_type": getattr(details, "deviceType", "Unknown"),
                    "variant": getattr(details, "variant", "Unknown"),
                    "color": getattr(details, "color", "Unknown"),
                }
                _LOGGER.debug("API appliance details retrieved for %s", appliance_id)
                result.append(info)
            except Exception as e:
                _LOGGER.warning(
                    "Failed to get info for appliance %s: %s", appliance_id, e
                )
        return result

    async def get_appliance_state(self, appliance_id) -> dict[str, Any]:
        """Get appliance state."""

        async def _get_state():
            state = await self._handle_api_call(
                self._client.get_appliance_state(appliance_id)
            )
            return state

        result = await safe_api_call(
            _get_state(),
            f"get appliance state for {appliance_id}",
            logger=_LOGGER,
        )

        # Validate response structure
        if isinstance(result, dict):
            reported = result.get("properties", {}).get("reported", {})
        elif hasattr(result, "properties") and isinstance(result.properties, dict):
            reported = result.properties.get("reported", {})
        else:
            _LOGGER.warning(
                "API response is not a dict or object with properties: %s", type(result)
            )
            raise HomeAssistantError(
                f"Invalid appliance state response for {appliance_id}"
            )

        # Convert to expected format
        return {
            "applianceId": appliance_id,
            "connectionState": "connected",
            "status": "enabled",
            "properties": {"reported": reported},
        }

    async def get_appliance_capabilities(self, appliance_id):
        """Get appliance capabilities."""

        async def _get_capabilities():
            details = await self._handle_api_call(
                self._client.get_appliance_details(appliance_id)
            )
            return details

        result = await safe_api_call(
            _get_capabilities(),
            f"get appliance capabilities for {appliance_id}",
            logger=_LOGGER,
        )

        # Validate response has capabilities
        if not hasattr(result, "capabilities") or not result.capabilities:
            _LOGGER.warning("No capabilities found for appliance %s", appliance_id)
            return {}

        return result.capabilities

    async def watch_for_appliance_state_updates(self, appliance_ids, callback):
        """Safely start SSE event stream."""
        # Ensure any existing stream is killed first
        if hasattr(self, "_sse_task") and self._sse_task:
            await self.disconnect_websocket()

        try:
            # Add listeners for each appliance
            for appliance_id in appliance_ids:
                self._client.add_listener(appliance_id, callback)
                _LOGGER.debug("Added SSE listener for appliance %s", appliance_id)

            # Start the event stream as a background task (it runs indefinitely)
            if self.hass:
                self._sse_task = self.hass.async_create_task(
                    self._client.start_event_stream()
                )
            else:
                self._sse_task = asyncio.create_task(self._client.start_event_stream())

            # Add callback to handle task failures
            def _handle_sse_failure(task):
                if task.cancelled():
                    _LOGGER.debug(
                        "SSE event stream was cancelled for appliances %s",
                        ", ".join(appliance_ids),
                    )
                elif task.exception() is not None:
                    _LOGGER.error(
                        "SSE event stream failed for appliances %s: %s",
                        ", ".join(appliance_ids),
                        task.exception(),
                    )
                    # Check if it's an auth error and trigger reauth
                    if self.hass and self.config_entry:
                        error_msg = str(task.exception()).lower()
                        auth_keywords = [
                            "401",
                            "unauthorized",
                            "auth",
                            "token",
                            "invalid grant",
                            "forbidden",
                        ]
                        if any(keyword in error_msg for keyword in auth_keywords):
                            _LOGGER.debug(
                                f"SSE auth error detected: {task.exception()}"
                            )
                            self.hass.loop.call_soon_threadsafe(
                                lambda: asyncio.create_task(
                                    self._trigger_reauth(
                                        f"SSE auth error: {task.exception()}"
                                    )
                                )
                            )
                    # Note: We don't mark appliances as offline here because SSE failure
                    # doesn't necessarily mean appliances are disconnected. Individual
                    # appliance connectivity is tracked through data updates and timeouts.
                    _LOGGER.warning(
                        "SSE stream failed for appliances %s. "
                        "Appliance connectivity will be determined by individual data updates.",
                        ", ".join(appliance_ids),
                    )
                else:
                    _LOGGER.debug(
                        "SSE event stream ended unexpectedly for appliances %s (no exception)",
                        ", ".join(appliance_ids),
                    )

            self._sse_task.add_done_callback(_handle_sse_failure)

            _LOGGER.debug(
                "Started SSE event stream for %d appliances", len(appliance_ids)
            )

        except Exception as e:
            _LOGGER.error("Failed to start SSE event stream: %s", e)
            raise

    async def disconnect_websocket(self):
        """Disconnect SSE event stream."""
        try:
            if (
                hasattr(self, "_sse_task")
                and self._sse_task
                and not self._sse_task.done()
            ):
                self._sse_task.cancel()
                try:
                    await self._sse_task
                except asyncio.CancelledError:
                    _LOGGER.debug(
                        "Electrolux SSE task was cancelled during disconnect, as expected"
                    )
                except Exception:
                    # Task finished with an exception, but we don't care during shutdown
                    _LOGGER.debug(
                        "Electrolux SSE task finished with exception during disconnect"
                    )
                self._sse_task = None
            _LOGGER.debug("SSE disconnect completed")
        except Exception as e:
            _LOGGER.error("Error during SSE disconnect: %s", e)

    async def get_user_metadata(self):
        """Get user metadata - compatibility method."""
        # Return mock metadata since the new API doesn't expose this
        return {"userId": "mock_user"}

    async def execute_appliance_command(self, appliance_id, command):
        """Execute a command on an appliance."""
        # Use the ApplianceClient's send_command method
        try:
            result = await self._handle_api_call(
                self._client.send_command(appliance_id, command)
            )
            return result
        except Exception:
            # Re-raise all exceptions to be handled by the calling entity
            raise

    async def close(self):
        """Decisive cleanup of resources."""
        # 1. Stop the SSE stream
        await self.disconnect_websocket()

        # 2. Remove the logging handler to prevent leaks
        if self._token_handler and self._token_logger:
            self._token_logger.removeHandler(self._token_handler)
            self._token_handler = None
