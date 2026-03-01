"""API client and related utilities for the Electrolux integration."""

import asyncio
import logging
from typing import Any

from electrolux_group_developer_sdk.client.appliance_client import (
    ApplianceClient,  # type: ignore[import-untyped]
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import issue_registry

from .const import DOMAIN
from .exceptions import NetworkError
from .token_manager import ElectroluxTokenManager

_LOGGER: logging.Logger = logging.getLogger(__package__)


def get_electrolux_session(
    api_key, access_token, refresh_token, client_session, hass=None, config_entry=None
) -> "ElectroluxApiClient":
    """Return Electrolux API Session.

    Note: client_session is currently unused by the underlying SDK but is kept
    for future compatibility when the SDK supports passing in a shared aiohttp session.
    """
    return ElectroluxApiClient(api_key, access_token, refresh_token, hass, config_entry)


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
            # Add listeners for each appliance (clear stale registrations first to
            # prevent double-firing when the SSE stream is restarted/renewed)
            for appliance_id in appliance_ids:
                self._client.remove_all_listeners_by_appliance_id(appliance_id)
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
