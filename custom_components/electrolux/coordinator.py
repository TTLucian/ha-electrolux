"""Electrolux integration."""

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ElectroluxLibraryEntity
from .const import DOMAIN, TIME_ENTITIES_TO_UPDATE
from .models import Appliance, Appliances, ApplianceState
from .util import (
    AuthenticationError,
    ElectroluxApiClient,
    NetworkError,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)

# Configuration constants
#
# SSE (Server-Sent Events) Configuration:
# - SSE_RENEW_INTERVAL_HOURS: How often to renew the SSE connection
#   to prevent timeouts and ensure fresh connection
#
# API Timeouts:
# - APPLIANCE_STATE_TIMEOUT: Max time to wait for appliance state
# - APPLIANCE_CAPABILITY_TIMEOUT: Max time to wait for capabilities
# - SETUP_TIMEOUT_TOTAL: Total timeout for all appliances during setup
# - UPDATE_TIMEOUT: Timeout for background state updates
#
# Deferred Update Configuration:
# - DEFERRED_UPDATE_DELAY: Delay before checking appliance state after
#   cycle completion (Electrolux doesn't send final update)
# - TIME_ENTITY_THRESHOLD_HIGH: Trigger deferred update when time
#   remaining is below this threshold
#
# Cleanup:
# - CLEANUP_INTERVAL: How often to check for removed appliances

SSE_RENEW_INTERVAL_HOURS = 6
APPLIANCE_STATE_TIMEOUT = 12.0  # seconds
APPLIANCE_CAPABILITY_TIMEOUT = 12.0  # seconds
SETUP_TIMEOUT_TOTAL = 30.0  # seconds
UPDATE_TIMEOUT = 15.0  # seconds
FIRST_REFRESH_TIMEOUT = 15.0  # seconds for initial setup refresh
DEFERRED_UPDATE_DELAY = 70  # seconds
DEFERRED_TASK_LIMIT = 5  # maximum concurrent deferred tasks
CLEANUP_INTERVAL = 86400  # 24 hours in seconds
TASK_CANCEL_TIMEOUT = 2.0  # seconds for task cancellation timeouts
WEBSOCKET_DISCONNECT_TIMEOUT = 5.0  # seconds for websocket disconnect
WEBSOCKET_BACKOFF_DELAY = 300  # 5 minutes in seconds for backoff
API_DISCONNECT_TIMEOUT = 3.0  # seconds for API disconnect

# String constants for data keys
APPLIANCE_ID_KEY = "applianceId"
APPLIANCE_ID_ALT_KEY = "appliance_id"
PROPERTY_KEY = "property"
VALUE_KEY = "value"
CONNECTIVITY_STATE_KEY = "connectivityState"
USER_ID_KEY = "userId"
TIMESTAMP_KEY = "timestamp"

# Connectivity states
STATE_CONNECTED = "connected"
STATE_DISCONNECTED = "disconnected"

# Authentication error keywords
AUTH_ERROR_KEYWORDS = [
    "401",
    "unauthorized",
    "auth",
    "token",
    "invalid grant",
    "forbidden",
]

# Time entity thresholds
TIME_ENTITY_THRESHOLD_LOW = 0
TIME_ENTITY_THRESHOLD_HIGH = 1  # seconds


class ElectroluxCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    api: ElectroluxApiClient

    def __init__(
        self,
        hass: HomeAssistant,
        client: ElectroluxApiClient,
        renew_interval: int,
        username: str,
    ) -> None:
        """Initialize."""
        self.hass = hass
        self.api = client
        self.platforms: list[str] = []
        self.renew_task: Optional[asyncio.Task] = None
        self.listen_task: Optional[asyncio.Task] = None
        self.renew_interval = renew_interval
        self._deferred_tasks: set = set()  # Track deferred update tasks
        self._deferred_tasks_by_appliance: dict[str, asyncio.Task] = (
            {}
        )  # Track deferred tasks by appliance
        self._appliances_lock = asyncio.Lock()  # Shared lock for appliances dict
        self._manual_sync_lock = (
            asyncio.Lock()
        )  # Prevent concurrent manual sync operations
        self._last_cleanup_time = 0  # Track when we last ran appliance cleanup
        self._last_update_times: dict[str, float] = (
            {}
        )  # Track last update time per appliance
        self._last_known_connectivity: dict[str, str] = (
            {}
        )  # Track previous connectivity state per appliance
        self._last_sse_restart_time = 0.0  # Track when we last restarted SSE
        self._last_manual_sync_time = 0.0  # Track when we last performed manual sync

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                hours=SSE_RENEW_INTERVAL_HOURS
            ),  # Health check every 6 hours instead of 30 seconds
        )

    async def async_login(self) -> bool:
        """Authenticate with the service."""
        _LOGGER.debug("Electrolux async_login: Starting authentication test")
        try:
            # Test authentication by fetching appliances
            _LOGGER.debug(
                "Electrolux async_login: Testing authentication with appliances list fetch"
            )
            await self.api.get_appliances_list()
            _LOGGER.info("Electrolux logged in successfully")
            _LOGGER.debug("Electrolux async_login: Authentication test passed")
            return True
        except AuthenticationError as ex:
            _LOGGER.error(f"Electrolux authentication failed: {ex}")
            _LOGGER.debug(f"Electrolux async_login: AuthenticationError caught: {ex}")
            raise ConfigEntryAuthFailed("Invalid credentials") from ex
        except NetworkError as ex:
            _LOGGER.error(f"Network error during login: {ex}")
            _LOGGER.debug(f"Electrolux async_login: NetworkError caught: {ex}")
            raise ConfigEntryNotReady from ex
        except Exception as ex:
            # Catch-all for unexpected errors
            _LOGGER.exception(f"Unexpected error during login: {ex}")
            _LOGGER.debug(f"Electrolux async_login: Unexpected exception caught: {ex}")
            raise ConfigEntryNotReady from ex

    def setup_token_refresh_callback(self) -> None:
        """Set up the token refresh callback to update config entry with new tokens."""
        _LOGGER.debug("Setting up token refresh callback")
        if not hasattr(self, "config_entry") or self.config_entry is None:
            _LOGGER.debug(
                "setup_token_refresh_callback: No config_entry available, skipping callback setup"
            )
            return

        # Capture config_entry in local variable to satisfy mypy
        config_entry = self.config_entry
        _LOGGER.debug(
            f"setup_token_refresh_callback: Setting up callback for config entry {config_entry.entry_id}"
        )

        def on_token_update(
            access_token: str, refresh_token: str, api_key: str, expires_at: int
        ) -> None:
            """Callback to update config entry with refreshed tokens and expiration."""
            _LOGGER.debug(
                f"Tokens refreshed, updating config entry (expires at {expires_at})"
            )
            _LOGGER.debug(
                f"on_token_update: Received new tokens - access_token length: {len(access_token)}, refresh_token length: {len(refresh_token)}"
            )
            # Log last 5 characters of new refresh token for debugging rotation chain
            refresh_suffix = (
                refresh_token[-5:] if len(refresh_token) >= 5 else refresh_token
            )
            _LOGGER.debug(f"New refresh token suffix: ...{refresh_suffix}")
            new_data = dict(config_entry.data)
            new_data["access_token"] = access_token
            new_data["refresh_token"] = refresh_token
            new_data["token_expires_at"] = expires_at
            _LOGGER.debug("on_token_update: Updating config entry with new token data")
            self.hass.config_entries.async_update_entry(config_entry, data=new_data)
            _LOGGER.debug("on_token_update: Config entry updated successfully")

        self.api.set_token_update_callback_with_expiry(on_token_update)
        _LOGGER.debug(
            "setup_token_refresh_callback: Token update callback registered with API client"
        )

    async def handle_authentication_error(self, exception: Exception) -> None:
        """Handle authentication errors by raising ConfigEntryAuthFailed.

        This method should be called when authentication errors are detected
        during command execution or other API calls outside the normal update cycle.
        """
        _LOGGER.debug(f"Handling authentication error: {exception}")
        error_msg = str(exception).lower()
        if any(keyword in error_msg for keyword in AUTH_ERROR_KEYWORDS):
            _LOGGER.warning(f"Authentication failed during operation: {exception}")
            raise ConfigEntryAuthFailed(
                "Token expired or invalid - please reauthenticate"
            ) from exception

    async def deferred_update(self, appliance_id: str, delay: int) -> None:
        """Deferred update due to Electrolux not sending updated data at the end of the appliance program/cycle."""
        _LOGGER.debug(
            f"Electrolux scheduling deferred update for appliance {appliance_id}"
        )
        await asyncio.sleep(delay)
        _LOGGER.debug(
            f"Electrolux scheduled deferred update for appliance {appliance_id} running"
        )
        if self.data is None:
            _LOGGER.warning("No coordinator data available for deferred update")
            return
        appliances: Any = self.data.get("appliances", None)
        if not appliances:
            return
        try:
            appliance: Appliance = appliances.get_appliance(appliance_id)
            if appliance:
                appliance_status = await self.api.get_appliance_state(appliance_id)
                appliance.update(appliance_status)
                new_data = dict(self.data)
                self.async_set_updated_data(new_data)
        except asyncio.CancelledError:
            # Always re-raise cancellation
            raise
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as ex:
            # Network errors - log and raise UpdateFailed
            _LOGGER.error(
                f"Network error during deferred update for {appliance_id}: {ex}"
            )
            raise UpdateFailed(f"Network error: {ex}") from ex
        except (KeyError, ValueError, TypeError) as ex:
            # Data validation errors - log and raise UpdateFailed
            _LOGGER.error(f"Data error during deferred update for {appliance_id}: {ex}")
            raise UpdateFailed(f"Invalid data: {ex}") from ex
        except Exception as ex:
            # Catch-all for unexpected errors
            _LOGGER.exception(
                f"Unexpected error during deferred update for {appliance_id}"
            )
            raise UpdateFailed(f"Unexpected error: {ex}") from ex

    def incoming_data(self, data: dict[str, Any]) -> None:
        """Process incoming data."""
        # Update reported data
        if self.data is None:
            _LOGGER.warning("No coordinator data available for incoming data update")
            return
        appliances: Any = self.data.get("appliances", None)
        if not appliances:
            _LOGGER.warning("No appliances data available for incoming data update")
            return

        # Handle incremental updates: {"applianceId": "...", "property": "...", "value": "..."}
        if self._is_incremental_update(data):
            self._process_incremental_update(data, appliances)
            return

        # Handle bulk updates: {"appliance_id1": {...}, "appliance_id2": {...}}
        self._process_bulk_update(data, appliances)

    def _is_incremental_update(self, data: dict[str, Any]) -> bool:
        """Return True if data contains incremental update fields."""
        return (
            bool(data)
            and APPLIANCE_ID_KEY in data
            and PROPERTY_KEY in data
            and VALUE_KEY in data
        )

    def _process_incremental_update(
        self, data: dict[str, Any], appliances: Any
    ) -> None:
        """Process an incremental property update."""
        appliance_id = data[APPLIANCE_ID_KEY]
        _LOGGER.debug(
            f"Electrolux appliance state updated for {appliance_id} "
            f"(incremental: {data[PROPERTY_KEY]} = {data[VALUE_KEY]})"
        )

        # Log info message when appliance becomes offline
        if (
            data[PROPERTY_KEY] == CONNECTIVITY_STATE_KEY
            and str(data[VALUE_KEY]).lower() == STATE_DISCONNECTED
        ):
            _LOGGER.info(f"Device {appliance_id} is now offline")

        appliance = appliances.get_appliance(appliance_id)
        if appliance is None:
            _LOGGER.warning(
                f"Received incremental data for unknown appliance {appliance_id}, ignoring"
            )
            return

        try:
            appliance.update_reported_data({data[PROPERTY_KEY]: data[VALUE_KEY]})
        except (KeyError, ValueError, TypeError) as ex:
            _LOGGER.error(
                f"Data validation error updating incremental data for appliance {appliance_id}: {ex}"
            )
            return
        except Exception:
            _LOGGER.exception(
                f"Unexpected error updating incremental data for appliance {appliance_id}"
            )
            return

        # Notify entities of the update
        new_data = dict(self.data)
        self.async_set_updated_data(new_data)

        # Mark appliance as connected since we're receiving data (unless explicitly set to disconnected)
        if (
            data[PROPERTY_KEY] != CONNECTIVITY_STATE_KEY
            or str(data[VALUE_KEY]).lower() != STATE_DISCONNECTED
        ):
            if appliance.state.get("connectivityState") == "disconnected":
                _LOGGER.info(f"Device {appliance_id} is back online")
            appliance.state["connectivityState"] = "connected"

        # Update last seen time for this appliance (real-time updates via SSE)
        self._last_update_times[appliance_id] = self.hass.loop.time()

        # Check for deferred update due to Electrolux bug: no data sent when appliance cycle is over
        self._check_deferred_update(data, appliance_id)

    def _check_deferred_update(self, data: dict[str, Any], appliance_id: str) -> None:
        """Schedule deferred update if time entity reaches threshold."""
        appliance_data = {data[PROPERTY_KEY]: data[VALUE_KEY]}
        if self._should_defer_update(appliance_data):
            self._schedule_deferred_update(appliance_id)

    def _should_defer_update(self, appliance_data: dict[str, Any]) -> bool:
        """Return True if any time entity value is at threshold."""
        for key, value in appliance_data.items():
            if key in TIME_ENTITIES_TO_UPDATE:
                if (
                    value is not None
                    and TIME_ENTITY_THRESHOLD_LOW < value <= TIME_ENTITY_THRESHOLD_HIGH
                ):
                    return True
        return False

    def _schedule_deferred_update(self, appliance_id: str) -> None:
        """Schedule a deferred update for an appliance."""
        # Cancel existing deferred task for this appliance if any
        if appliance_id in self._deferred_tasks_by_appliance:
            old_task = self._deferred_tasks_by_appliance[appliance_id]
            if not old_task.done():
                _LOGGER.debug(f"Cancelling existing deferred update for {appliance_id}")
                old_task.cancel()

        # Check if we can add more deferred tasks
        if len(self._deferred_tasks) >= DEFERRED_TASK_LIMIT:
            _LOGGER.debug(
                f"Skipping deferred update for {appliance_id}, too many active tasks"
            )
            return

        # Create new deferred task
        task = self.hass.async_create_task(
            self.deferred_update(appliance_id, DEFERRED_UPDATE_DELAY)
        )
        self._deferred_tasks.add(task)
        self._deferred_tasks_by_appliance[appliance_id] = task

        # Cleanup callback
        def cleanup_deferred(t: asyncio.Task, app_id: str = appliance_id) -> None:
            """Remove task from tracking when done."""
            # app_id is captured by VALUE at definition time
            if self._deferred_tasks_by_appliance.get(app_id) == t:
                # Use pop for safety as established in previous fixes
                self._deferred_tasks_by_appliance.pop(app_id, None)

        task.add_done_callback(cleanup_deferred)

    def _process_bulk_update(self, data: dict[str, Any], appliances: Any) -> None:
        """Process a bulk appliance state update."""
        # Extract appliance ID from the SSE payload
        appliance_id = data.get(APPLIANCE_ID_KEY) or data.get(APPLIANCE_ID_ALT_KEY)
        if not appliance_id:
            _LOGGER.warning(f"No applianceId found in SSE data: {data}")
            return

        appliance = appliances.get_appliance(appliance_id)
        if appliance is None:
            _LOGGER.warning(
                f"Received data for unknown appliance {appliance_id}, ignoring"
            )
            return

        # Extract the actual appliance data from the payload
        appliance_data = data.get("data") or data.get("state") or data
        if appliance_data == data:
            # If no specific data field, assume the whole payload except applianceId is the data
            appliance_data = {
                k: v
                for k, v in data.items()
                if k
                not in [
                    APPLIANCE_ID_KEY,
                    APPLIANCE_ID_ALT_KEY,
                    USER_ID_KEY,
                    TIMESTAMP_KEY,
                ]
            }

        _LOGGER.debug(
            f"Electrolux appliance state updated for {appliance_id} "
            f"(bulk: {list(appliance_data.keys())})"
        )

        try:
            appliance.update_reported_data(appliance_data)
        except (KeyError, ValueError, TypeError) as ex:
            _LOGGER.error(
                f"Data validation error updating reported data for appliance {appliance_id}: {ex}"
            )
            return
        except Exception:
            _LOGGER.exception(
                f"Unexpected error updating reported data for appliance {appliance_id}"
            )
            return

        # Mark appliance as connected since we're receiving data (unless explicitly set to disconnected)
        connectivity_in_data = appliance_data.get(CONNECTIVITY_STATE_KEY)
        if (
            connectivity_in_data is None
            or str(connectivity_in_data).lower() != STATE_DISCONNECTED
        ):
            if appliance.state.get("connectivityState") == "disconnected":
                _LOGGER.info(f"Device {appliance_id} is back online")
            appliance.state["connectivityState"] = "connected"

        # Update last seen time for this appliance
        self._last_update_times[appliance_id] = self.hass.loop.time()

        new_data = dict(self.data)
        self.async_set_updated_data(new_data)

        # Check for deferred update due to Electrolux bug: no data sent when appliance cycle is over
        if self._should_defer_update(appliance_data):
            # Limit deferred tasks to prevent pile-up (max 5 concurrent)
            if len(self._deferred_tasks) < DEFERRED_TASK_LIMIT:
                task = self.hass.async_create_task(
                    self.deferred_update(appliance_id, DEFERRED_UPDATE_DELAY)
                )
                self._deferred_tasks.add(task)
                task.add_done_callback(self._deferred_tasks.discard)

    async def listen_websocket(self) -> None:
        """Listen for state changes."""
        if self.data is None:
            _LOGGER.warning("No coordinator data available, skipping SSE setup")
            return
        appliances: Any = self.data.get("appliances", None)
        if not appliances:
            _LOGGER.warning("No appliance data available, skipping SSE setup")
            return

        ids = appliances.get_appliance_ids()
        _LOGGER.debug(f"Electrolux listen_websocket for appliances {','.join(ids)}")
        if ids is None or len(ids) == 0:
            _LOGGER.debug("No appliances to listen for, skipping SSE setup")
            return

        # watch_for_appliance_state_updates in util.py handles kill-before-restart safely
        try:
            await asyncio.wait_for(
                self.api.watch_for_appliance_state_updates(ids, self.incoming_data),
                timeout=3600,  # 1 hour max for SSE setup
            )
            _LOGGER.debug(
                f"Successfully started SSE listening for {len(ids)} appliances"
            )
        except Exception as ex:
            _LOGGER.error(f"Failed to start SSE listening: {ex}")
            raise

    async def renew_websocket(self):
        """Renew SSE event stream."""
        consecutive_failures = 0
        max_consecutive_failures = 5

        while True:
            try:
                await asyncio.sleep(self.renew_interval)
                _LOGGER.debug("Electrolux renew SSE event stream")

                # Cancel existing SSE task before disconnecting
                # Note: util.py watch_for_appliance_state_updates handles kill-before-restart,
                # but we still need to disconnect here for renewal

                # Disconnect and reconnect with timeout
                try:
                    await asyncio.wait_for(
                        self.api.disconnect_websocket(),
                        timeout=WEBSOCKET_DISCONNECT_TIMEOUT,
                    )
                    await asyncio.wait_for(
                        self.listen_websocket(), timeout=UPDATE_TIMEOUT
                    )
                    consecutive_failures = 0  # Reset on success
                except asyncio.TimeoutError:
                    _LOGGER.warning("Timeout during websocket renewal")
                    consecutive_failures += 1
                except Exception as ex:
                    _LOGGER.error(f"Error during websocket renewal: {ex}")
                    consecutive_failures += 1

                # If too many consecutive failures, back off
                if consecutive_failures >= max_consecutive_failures:
                    _LOGGER.warning(
                        "Too many websocket renewal failures, backing off for 5 minutes"
                    )
                    await asyncio.sleep(WEBSOCKET_BACKOFF_DELAY)  # 5 minute backoff
                    consecutive_failures = 0

            except asyncio.CancelledError:
                _LOGGER.debug("Websocket renewal cancelled")
                raise
            except Exception as ex:
                _LOGGER.error(f"Electrolux renew SSE failed {ex}")
                consecutive_failures += 1

    async def close_websocket(self):
        """Close SSE event stream."""
        # Cancel renewal task with shorter timeout
        if self.renew_task and not self.renew_task.done():
            self.renew_task.cancel()
            try:
                await asyncio.wait_for(self.renew_task, timeout=TASK_CANCEL_TIMEOUT)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                _LOGGER.debug("Electrolux renewal task cancelled/timeout during close")

        # Cancel all deferred tasks aggressively
        tasks_to_cancel = list(self._deferred_tasks.copy())
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete cancellation
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        self._deferred_tasks.clear()

        # Cancel per-appliance deferred tasks
        appliance_tasks = list(self._deferred_tasks_by_appliance.values())
        for task in appliance_tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellations
        if appliance_tasks:
            await asyncio.gather(*appliance_tasks, return_exceptions=True)

        self._deferred_tasks_by_appliance.clear()

        # Close API connection - util.py handles SSE stream cleanup
        try:
            await asyncio.wait_for(self.api.close(), timeout=API_DISCONNECT_TIMEOUT)
        except (asyncio.TimeoutError, Exception) as ex:
            if isinstance(ex, asyncio.TimeoutError):
                _LOGGER.debug("Electrolux API close timeout")
            else:
                _LOGGER.error(f"Electrolux close SSE failed {ex}")

    async def setup_entities(self):
        """Configure entities."""
        _LOGGER.debug("Electrolux setup_entities")
        appliances = Appliances({})
        self.data = {"appliances": appliances}
        try:
            appliances_list = await self.api.get_appliances_list()
            if appliances_list is None:
                _LOGGER.error(
                    "Electrolux unable to retrieve appliances list. Cancelling setup"
                )
                raise ConfigEntryNotReady(
                    "Electrolux unable to retrieve appliances list. Cancelling setup"
                )
            _LOGGER.debug(
                f"Electrolux get_appliances_list {self.api} {json.dumps(appliances_list)}"
            )

            # Process appliances concurrently to reduce setup time
            appliance_tasks = []
            for appliance_json in appliances_list:
                appliance_id = appliance_json.get("applianceId")
                if appliance_id:
                    task = self._setup_single_appliance(appliance_json)
                    appliance_tasks.append(task)

            # Wait for all appliance setup tasks with a global timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*appliance_tasks, return_exceptions=True),
                    timeout=30.0,  # Total timeout for all appliances
                )
            except asyncio.TimeoutError:
                _LOGGER.warning(
                    "Timeout setting up appliances, cancelling pending tasks"
                )
                # Cancel all pending tasks
                for task in appliance_tasks:
                    if not task.done():
                        task.cancel()

                # Wait for cancellations to complete
                await asyncio.gather(*appliance_tasks, return_exceptions=True)

        except asyncio.CancelledError:
            _LOGGER.debug("Electrolux setup_entities cancelled")
            raise
        except Exception as exception:
            _LOGGER.debug(f"setup_entities: {exception}")
            raise UpdateFailed from exception
        return self.data

    async def _setup_single_appliance(self, appliance_json: dict[str, Any]) -> None:
        """Setup a single appliance concurrently."""
        try:
            appliance_id = appliance_json.get("applianceId")
            connection_status = appliance_json.get("connectionState")
            appliance_name = appliance_json.get("applianceData", {}).get(
                "applianceName"
            )

            # Make concurrent API calls for this appliance
            info_task = asyncio.create_task(
                asyncio.wait_for(
                    self.api.get_appliances_info([appliance_id]),
                    timeout=APPLIANCE_STATE_TIMEOUT,
                )
            )
            state_task = asyncio.create_task(
                asyncio.wait_for(
                    self.api.get_appliance_state(appliance_id),
                    timeout=APPLIANCE_STATE_TIMEOUT,
                )
            )
            capabilities_task = asyncio.create_task(
                asyncio.wait_for(
                    self.api.get_appliance_capabilities(appliance_id),
                    timeout=APPLIANCE_CAPABILITY_TIMEOUT,
                )
            )

            # Wait for info and state (required), capabilities optional
            try:
                appliance_infos, appliance_state = await asyncio.gather(
                    info_task, state_task
                )
            except (ConnectionError, TimeoutError, asyncio.TimeoutError) as ex:
                _LOGGER.warning(
                    f"Network error getting required data for appliance {appliance_id}: {ex}"
                )
                # Cleanup ALL pending tasks for this appliance
                for task in [info_task, state_task, capabilities_task]:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        except Exception:
                            pass  # Suppress secondary errors during cleanup
                return
            except Exception as ex:
                _LOGGER.warning(
                    f"Failed to get required data for appliance {appliance_id}: {ex}"
                )
                # Cleanup ALL pending tasks for this appliance
                for task in [info_task, state_task, capabilities_task]:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        except Exception:
                            pass  # Suppress secondary errors during cleanup
                return

            # Try to get capabilities (optional)
            appliance_capabilities = None
            try:
                appliance_capabilities = await capabilities_task
            except Exception as ex:
                _LOGGER.debug(
                    f"Could not get capabilities for appliance {appliance_id}: {ex}"
                )

            # Process appliance data
            appliance_info = appliance_infos[0] if appliance_infos else None
            appliance_model = appliance_info.get("model") if appliance_info else ""
            if not appliance_model:
                appliance_model = appliance_json.get("applianceData", {}).get(
                    "modelName", ""
                )
            brand = appliance_info.get("brand") if appliance_info else ""
            if not brand:
                brand = "Electrolux"

            # Create appliance object
            if not appliance_id:
                _LOGGER.error("Missing appliance_id for appliance, skipping")
                return

            from typing import cast

            appliance = Appliance(
                coordinator=self,
                pnc_id=appliance_id,
                name=appliance_name or "Unknown",
                brand=brand,
                model=appliance_model,
                state=cast(ApplianceState, appliance_state),
            )

            # Thread-safe addition to appliances dict
            async with self._appliances_lock:
                self.data["appliances"].appliances[appliance_id] = appliance

            appliance.setup(
                ElectroluxLibraryEntity(
                    name=appliance_name or "Unknown",
                    status=connection_status or "unknown",
                    state=appliance_state,
                    appliance_info=appliance_info or {},
                    capabilities=appliance_capabilities or {},
                )
            )

            _LOGGER.debug(f"Successfully set up appliance {appliance_id}")

        except (KeyError, ValueError, TypeError, AttributeError) as ex:
            _LOGGER.error(
                f"Data validation error setting up appliance {appliance_json.get('applianceId')}: {ex}"
            )
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as ex:
            _LOGGER.error(
                f"Network error setting up appliance {appliance_json.get('applianceId')}: {ex}"
            )
        except Exception:
            _LOGGER.exception(
                f"Unexpected error setting up appliance {appliance_json.get('applianceId')}"
            )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data for all appliances concurrently."""
        # Check if auth has failed and trigger reauth
        if hasattr(self.api, "_auth_failed") and self.api._auth_failed:
            _LOGGER.debug("Auth failure detected, triggering reauth")
            raise ConfigEntryAuthFailed("Authentication failed - please reauthenticate")

        if self.data is None:
            _LOGGER.warning("Coordinator data not initialized, skipping update")
            return {"appliances": Appliances({})}
        appliances: Appliances = self.data.get("appliances")  # type: ignore[assignment,union-attr]
        app_dict = appliances.get_appliances()

        if not app_dict:
            return self.data

        async def _update_single(app_id: str, app_obj) -> tuple[bool, bool]:
            """Returns (success, came_online) tuple."""
            try:
                # Use a strict timeout for the background refresh
                status = await asyncio.wait_for(
                    self.api.get_appliance_state(app_id), timeout=UPDATE_TIMEOUT
                )
                app_obj.update(status)

                # Track connectivity transitions for SSE restart logic
                old_state = self._last_known_connectivity.get(app_id)
                new_state = status.get(
                    "connectivityState", "connected"
                )  # Default to connected if not specified

                # Check if this appliance just came online
                came_online = old_state == "disconnected" and new_state == "connected"

                # Mark as connected since we successfully got state from API
                app_obj.state["connectivityState"] = new_state

                # Update our memory for next check
                self._last_known_connectivity[app_id] = new_state

                # Update last seen time for successful updates
                self._last_update_times[app_id] = self.hass.loop.time()
                return True, came_online  # Success + transition info
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                error_msg = str(ex).lower()
                # Check if this is an authentication error - these should still fail the update
                if any(keyword in error_msg for keyword in AUTH_ERROR_KEYWORDS):
                    _LOGGER.warning(f"Authentication failed during data update: {ex}")
                    # Create an issue to trigger reauth flow
                    from homeassistant.helpers import issue_registry

                    if self.config_entry is not None:
                        entry_id = self.config_entry.entry_id
                        entry_title = self.config_entry.title
                    else:
                        entry_id = "<unknown>"
                        entry_title = "<unknown>"

                    issue_registry.async_create_issue(
                        self.hass,
                        DOMAIN,
                        f"invalid_refresh_token_{entry_id}",
                        is_fixable=True,
                        severity=issue_registry.IssueSeverity.ERROR,
                        translation_key="invalid_refresh_token",
                        translation_placeholders={"entry_title": entry_title},
                    )
                    raise ConfigEntryAuthFailed("Token expired or invalid") from ex
                # For other errors, just log and return failure
                _LOGGER.warning(f"Failed to update {app_id} during refresh: {ex}")
                return False, False  # Failure + no transition

        # Run all updates concurrently
        results = await asyncio.gather(
            *(_update_single(aid, aobj) for aid, aobj in app_dict.items()),
            return_exceptions=True,
        )

        # Process results
        successful = 0
        newly_online_appliances = []
        other_errors = []

        _LOGGER.debug(f"Update results: {results}")

        for i, result in enumerate(results):
            app_id = list(app_dict.keys())[i]  # Get appliance ID for this result
            if isinstance(result, tuple) and len(result) == 2:
                success, came_online = result
                if success:
                    successful += 1
                    if came_online:
                        newly_online_appliances.append(app_id)
                        _LOGGER.info(f"Appliance {app_id} came back online!")
                else:
                    other_errors.append(f"{app_id}: Update failed")
            elif isinstance(result, ConfigEntryAuthFailed):
                # Re-raise auth errors immediately to trigger re-auth flow
                raise result
            elif isinstance(result, Exception):
                # Capture the actual exception message
                other_errors.append(f"{app_id}: {type(result).__name__}: {str(result)}")
            else:
                # Fallback for unexpected result types
                other_errors.append(f"{app_id}: Unexpected result: {result}")

        # Trigger SSE restart if appliances came back online
        if newly_online_appliances and self._can_restart_sse():
            _LOGGER.info(
                f"Restarting SSE stream to include {len(newly_online_appliances)} newly online appliance(s)"
            )
            try:
                # Disconnect existing SSE
                await asyncio.wait_for(
                    self.api.disconnect_websocket(),
                    timeout=WEBSOCKET_DISCONNECT_TIMEOUT,
                )
                # Reconnect with updated appliance list
                await asyncio.wait_for(self.listen_websocket(), timeout=UPDATE_TIMEOUT)
                _LOGGER.debug(
                    "SSE stream restarted successfully for newly online appliances"
                )
            except Exception as ex:
                _LOGGER.warning(
                    f"Failed to restart SSE stream for newly online appliances: {ex}"
                )
                # Don't raise - this is not critical, normal renewal will handle it

        # Improved logging for the failure case
        if successful == 0 and len(app_dict) > 0:
            error_detail = (
                "; ".join(other_errors) if other_errors else "Unknown internal error"
            )
            _LOGGER.error(f"All appliance updates failed. Errors: [{error_detail}]")
            raise UpdateFailed(f"All appliance updates failed: {error_detail}")

        # Log partial failures
        if other_errors:
            _LOGGER.debug(
                f"Some appliances failed to update ({successful}/{len(app_dict)} successful)"
            )

        # Periodically clean up removed appliances (once per day)
        # Check if we should run cleanup
        if not hasattr(self, "_last_cleanup_time"):
            self._last_cleanup_time = 0

        current_time = self.hass.loop.time()
        if current_time - self._last_cleanup_time > CLEANUP_INTERVAL:  # 24 hours
            _LOGGER.debug("Running periodic appliance cleanup")
            await self.cleanup_removed_appliances()
            self._last_cleanup_time = int(current_time)

        # Note: Appliances are not marked offline based on update timeouts.
        # Connectivity is determined by explicit "connectivityState" messages
        # or API polling failures. Idle appliances that don't send updates
        # remain marked as connected.

        return self.data

    def _can_restart_sse(self) -> bool:
        """Check if we can restart SSE (debounced to prevent hammering)."""
        current_time = self.hass.loop.time()
        # Allow SSE restart only once every 15 minutes
        SSE_RESTART_COOLDOWN = 900  # 15 minutes
        if current_time - self._last_sse_restart_time > SSE_RESTART_COOLDOWN:
            self._last_sse_restart_time = current_time
            return True
        return False

    async def cleanup_removed_appliances(self) -> None:
        """Remove appliances that no longer exist in the account."""
        try:
            # Get current appliance list from API
            appliances_list = await self.api.get_appliances_list()
            if not appliances_list:
                # If API returns None/empty, don't remove appliances - this could be a temporary API issue
                _LOGGER.debug(
                    "API returned no appliances list, skipping cleanup to avoid removing appliances due to temporary issues"
                )
                return

            # Validate that we got a proper list with at least some appliances
            # If the API returns an empty list when we have appliances, it might be an error
            if (
                self.data
                and self.data.get("appliances")
                and len(self.data["appliances"].appliances) > 0
            ):
                # We have tracked appliances but API returned empty list - this could be an API issue
                # Only proceed with cleanup if we're confident the list is valid
                if len(appliances_list) == 0:
                    _LOGGER.warning(
                        "API returned empty appliance list while tracking appliances - skipping cleanup to prevent accidental removal"
                    )
                    return

            # Get current appliance IDs
            current_ids = set()
            for appliance_json in appliances_list:
                if appliance_id := appliance_json.get("applianceId"):
                    current_ids.add(appliance_id)

            # Get appliances we're tracking
            if self.data is None:
                _LOGGER.warning("No coordinator data available for cleanup")
                return
            tracked_appliances = self.data.get("appliances")
            if not tracked_appliances:
                return

            tracked_ids = set(tracked_appliances.appliances.keys())

            # Find appliances that were removed
            removed_ids = tracked_ids - current_ids

            if removed_ids:
                _LOGGER.info(
                    f"Removing {len(removed_ids)} appliances no longer in account: {removed_ids}"
                )

                # Remove from tracking with lock protection
                async with self._appliances_lock:
                    for appliance_id in removed_ids:
                        # .pop() is safe if key doesn't exist
                        removed = tracked_appliances.appliances.pop(appliance_id, None)
                        if removed:
                            _LOGGER.debug(
                                f"Removed appliance {appliance_id} from tracking"
                            )

                # Trigger entity registry cleanup
                self.async_set_updated_data(self.data)

        except Exception as ex:
            _LOGGER.debug(f"Error during appliance cleanup: {ex}")

    async def perform_manual_sync(self, appliance_id: str, appliance_name: str) -> None:
        """Perform manual sync operation in a thread-safe manner.

        Args:
            appliance_id: The ID of the appliance triggering the sync
            appliance_name: The name of the appliance for logging

        Raises:
            HomeAssistantError: If manual sync fails or is rate limited
        """
        # Use lock to prevent concurrent manual sync operations
        async with self._manual_sync_lock:
            _LOGGER.info(
                "Starting manual sync for appliance %s (%s)",
                appliance_name,
                appliance_id,
            )

            # Check if we're within the manual sync cooldown period (1 minute)
            current_time = self.hass.loop.time()
            MANUAL_SYNC_COOLDOWN = 60  # 1 minute
            if current_time - self._last_manual_sync_time < MANUAL_SYNC_COOLDOWN:
                cooldown_remaining = MANUAL_SYNC_COOLDOWN - (
                    current_time - self._last_manual_sync_time
                )
                seconds_remaining = int(cooldown_remaining)
                error_msg = (
                    f"Manual sync rate limited. Please wait at least 1 minute before trying again. "
                    f"({seconds_remaining} seconds remaining)"
                )
                _LOGGER.warning(
                    "Manual sync blocked by cooldown for appliance %s (%s): %d seconds remaining",
                    appliance_name,
                    appliance_id,
                    seconds_remaining,
                )
                raise HomeAssistantError(error_msg)

            # Update the manual sync timestamp
            self._last_manual_sync_time = current_time

            # Log warning about sensible usage
            _LOGGER.info(
                "Manual sync initiated for appliance %s (%s). "
                "Please use this feature sensibly to avoid unnecessary API calls.",
                appliance_name,
                appliance_id,
            )

            try:
                # Step 1: Disconnect websocket safely
                _LOGGER.debug(
                    "Manual sync step 1: Disconnecting websocket for appliance %s",
                    appliance_id,
                )
                await asyncio.wait_for(
                    self.api.disconnect_websocket(),
                    timeout=WEBSOCKET_DISCONNECT_TIMEOUT,
                )

                # Step 2: Force fresh API poll for all data
                _LOGGER.debug(
                    "Manual sync step 2: Requesting coordinator refresh for appliance %s",
                    appliance_id,
                )
                await self.async_request_refresh()

                # Step 3: Start fresh real-time stream
                _LOGGER.debug(
                    "Manual sync step 3: Starting fresh websocket connection for appliance %s",
                    appliance_id,
                )
                await asyncio.wait_for(self.listen_websocket(), timeout=UPDATE_TIMEOUT)

                _LOGGER.info(
                    "Manual sync completed successfully for appliance %s (%s)",
                    appliance_name,
                    appliance_id,
                )

            except asyncio.TimeoutError as timeout_ex:
                error_msg = f"Manual sync timed out: {timeout_ex}"
                _LOGGER.error(
                    "Manual sync timeout for appliance %s (%s): %s",
                    appliance_name,
                    appliance_id,
                    timeout_ex,
                )
                # Try to restart websocket even on timeout to recover
                try:
                    await asyncio.wait_for(
                        self.listen_websocket(), timeout=UPDATE_TIMEOUT
                    )
                except Exception:
                    _LOGGER.error(
                        "Failed to recover websocket after timeout for appliance %s",
                        appliance_id,
                    )
                raise HomeAssistantError(error_msg) from timeout_ex

            except Exception as ex:
                error_msg = f"Manual sync failed: {ex}"
                _LOGGER.error(
                    "Manual sync failed for appliance %s (%s): %s",
                    appliance_name,
                    appliance_id,
                    ex,
                )
                # Try to restart websocket to recover from failed state
                try:
                    await asyncio.wait_for(
                        self.listen_websocket(), timeout=UPDATE_TIMEOUT
                    )
                except Exception as recovery_ex:
                    _LOGGER.error(
                        "Failed to recover websocket after error for appliance %s: %s",
                        appliance_id,
                        recovery_ex,
                    )
                raise HomeAssistantError(error_msg) from ex


# Optional health check for debugging
def get_health_status(self) -> dict[str, Any]:
    """Return integration health status for diagnostics."""
    return {
        "websocket_connected": self.listen_task is not None
        and not self.listen_task.done(),
        "appliances_count": len(self.data.get("appliances", {})) if self.data else 0,
        "last_update_success": self.last_update_success,
    }
