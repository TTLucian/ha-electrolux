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
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ElectroluxLibraryEntity
from .const import DOMAIN, TIME_ENTITIES_TO_UPDATE
from .models import Appliance, Appliances, ApplianceState
from .util import ElectroluxApiClient

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
APPLIANCE_STATE_TIMEOUT = 8.0  # seconds
APPLIANCE_CAPABILITY_TIMEOUT = 8.0  # seconds
SETUP_TIMEOUT_TOTAL = 30.0  # seconds
UPDATE_TIMEOUT = 10.0  # seconds
FIRST_REFRESH_TIMEOUT = 15.0  # seconds for initial setup refresh
DEFERRED_UPDATE_DELAY = 70  # seconds
DEFERRED_TASK_LIMIT = 5  # maximum concurrent deferred tasks
CLEANUP_INTERVAL = 86400  # 24 hours in seconds
TASK_CANCEL_TIMEOUT = 2.0  # seconds for task cancellation timeouts
WEBSOCKET_DISCONNECT_TIMEOUT = 5.0  # seconds for websocket disconnect
WEBSOCKET_BACKOFF_DELAY = 300  # 5 minutes in seconds for backoff
API_DISCONNECT_TIMEOUT = 3.0  # seconds for API disconnect

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
        self._last_cleanup_time = 0  # Track when we last ran appliance cleanup

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
        try:
            # Test authentication by fetching appliances
            await self.api.get_appliances_list()
            _LOGGER.info("Electrolux logged in successfully")
            return True
        except Exception as ex:
            error_msg = str(ex).lower()
            if "invalid grant" in error_msg:
                _LOGGER.error("Electrolux authentication failed: invalid grant")
                raise ConfigEntryAuthFailed("Invalid credentials") from ex
            # For transient network/other errors, allow HA to retry setup
            _LOGGER.error("Could not log in to ElectroluxStatus, %s", ex)
            raise ConfigEntryNotReady from ex

    async def handle_authentication_error(self, exception: Exception) -> None:
        """Handle authentication errors by raising ConfigEntryAuthFailed.

        This method should be called when authentication errors are detected
        during command execution or other API calls outside the normal update cycle.
        """
        error_msg = str(exception).lower()
        if any(
            keyword in error_msg
            for keyword in [
                "401",
                "unauthorized",
                "auth",
                "token",
                "invalid grant",
                "forbidden",
            ]
        ):
            _LOGGER.warning("Authentication failed during operation: %s", exception)
            raise ConfigEntryAuthFailed(
                "Token expired or invalid - please reauthenticate"
            ) from exception

    async def deferred_update(self, appliance_id: str, delay: int) -> None:
        """Deferred update due to Electrolux not sending updated data at the end of the appliance program/cycle."""
        _LOGGER.debug(
            "Electrolux scheduling deferred update for appliance %s", appliance_id
        )
        await asyncio.sleep(delay)
        _LOGGER.debug(
            "Electrolux scheduled deferred update for appliance %s running",
            appliance_id,
        )
        appliances: Any = self.data.get("appliances", None)
        if not appliances:
            return
        try:
            appliance: Appliance = appliances.get_appliance(appliance_id)
            if appliance:
                appliance_status = await self.api.get_appliance_state(appliance_id)
                appliance.update(appliance_status)
                self.async_set_updated_data(self.data)
        except asyncio.CancelledError:
            # Always re-raise cancellation
            raise
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as ex:
            # Network errors - log and raise UpdateFailed
            _LOGGER.error(
                "Network error during deferred update for %s: %s", appliance_id, ex
            )
            raise UpdateFailed(f"Network error: {ex}") from ex
        except (KeyError, ValueError, TypeError) as ex:
            # Data validation errors - log and raise UpdateFailed
            _LOGGER.error(
                "Data error during deferred update for %s: %s", appliance_id, ex
            )
            raise UpdateFailed(f"Invalid data: {ex}") from ex
        except Exception as ex:
            # Catch-all for unexpected errors
            _LOGGER.exception(
                "Unexpected error during deferred update for %s", appliance_id
            )
            raise UpdateFailed(f"Unexpected error: {ex}") from ex

    def incoming_data(self, data: dict[str, Any]) -> None:
        """Process incoming data."""
        # Update reported data
        appliances: Any = self.data.get("appliances", None)
        if not appliances:
            _LOGGER.warning("No appliances data available for incoming data update")
            return

        # Handle incremental updates: {"applianceId": "...", "property": "...", "value": "..."}
        if data and "applianceId" in data and "property" in data and "value" in data:
            appliance_id = data["applianceId"]
            _LOGGER.debug(
                "Electrolux appliance state updated for %s (incremental: %s = %s)",
                appliance_id,
                data["property"],
                data["value"],
            )
            appliance = appliances.get_appliance(appliance_id)
            if appliance is None:
                _LOGGER.warning(
                    "Received incremental data for unknown appliance %s, ignoring",
                    appliance_id,
                )
                return

            try:
                appliance.update_reported_data({data["property"]: data["value"]})
            except (KeyError, ValueError, TypeError) as ex:
                _LOGGER.error(
                    "Data validation error updating incremental data for appliance %s: %s",
                    appliance_id,
                    ex,
                )
                return
            except Exception:
                _LOGGER.exception(
                    "Unexpected error updating incremental data for appliance %s",
                    appliance_id,
                )
                return

            self.async_set_updated_data(self.data)

            # Check for deferred update due to Electrolux bug: no data sent when appliance cycle is over
            appliance_data = {data["property"]: data["value"]}
            do_deferred = False
            for key, value in appliance_data.items():
                if key in TIME_ENTITIES_TO_UPDATE:
                    if (
                        value is not None
                        and TIME_ENTITY_THRESHOLD_LOW
                        < value
                        <= TIME_ENTITY_THRESHOLD_HIGH
                    ):
                        do_deferred = True
                        break
            if do_deferred:
                # Cancel existing deferred task for this appliance if any
                if appliance_id in self._deferred_tasks_by_appliance:
                    old_task = self._deferred_tasks_by_appliance[appliance_id]
                    if not old_task.done():
                        _LOGGER.debug(
                            "Cancelling existing deferred update for %s", appliance_id
                        )
                        old_task.cancel()

                # Create new deferred task
                task = self.hass.async_create_task(
                    self.deferred_update(appliance_id, DEFERRED_UPDATE_DELAY)
                )
                self._deferred_tasks_by_appliance[appliance_id] = task

                # Cleanup callback
                def cleanup_deferred(t: asyncio.Task) -> None:
                    """Remove task from tracking when done."""
                    if self._deferred_tasks_by_appliance.get(appliance_id) == t:
                        del self._deferred_tasks_by_appliance[appliance_id]

                task.add_done_callback(cleanup_deferred)
            return

        # Handle bulk updates: {"appliance_id1": {...}, "appliance_id2": {...}}
        # Extract appliance ID from the SSE payload
        appliance_id = data.get("applianceId") or data.get("appliance_id")
        if not appliance_id:
            _LOGGER.warning("No applianceId found in SSE data: %s", data)
            return

        appliance = appliances.get_appliance(appliance_id)
        if appliance is None:
            _LOGGER.warning(
                "Received data for unknown appliance %s, ignoring", appliance_id
            )
            return

        # Extract the actual appliance data from the payload
        appliance_data = data.get("data") or data.get("state") or data
        if appliance_data == data:
            # If no specific data field, assume the whole payload except applianceId is the data
            appliance_data = {
                k: v
                for k, v in data.items()
                if k not in ["applianceId", "appliance_id", "userId", "timestamp"]
            }

        _LOGGER.debug(
            "Electrolux appliance state updated for %s (bulk: %s)",
            appliance_id,
            list(appliance_data.keys()),
        )

        try:
            appliance.update_reported_data(appliance_data)
        except (KeyError, ValueError, TypeError) as ex:
            _LOGGER.error(
                "Data validation error updating reported data for appliance %s: %s",
                appliance_id,
                ex,
            )
            return
        except Exception:
            _LOGGER.exception(
                "Unexpected error updating reported data for appliance %s",
                appliance_id,
            )
            return

        self.async_set_updated_data(self.data)

        # Check for deferred update due to Electrolux bug: no data sent when appliance cycle is over
        do_deferred = False
        for key, value in appliance_data.items():
            if key in TIME_ENTITIES_TO_UPDATE:
                if (
                    value is not None
                    and TIME_ENTITY_THRESHOLD_LOW < value <= TIME_ENTITY_THRESHOLD_HIGH
                ):
                    do_deferred = True
                    break
        if do_deferred:
            # Limit deferred tasks to prevent pile-up (max 5 concurrent)
            if len(self._deferred_tasks) < DEFERRED_TASK_LIMIT:
                task = self.hass.async_create_task(
                    self.deferred_update(appliance_id, DEFERRED_UPDATE_DELAY)
                )
                self._deferred_tasks.add(task)
                task.add_done_callback(self._deferred_tasks.discard)
            else:
                _LOGGER.debug(
                    "Skipping deferred update for %s, too many active tasks",
                    appliance_id,
                )

    async def listen_websocket(self) -> None:
        """Listen for state changes."""
        appliances: Any = self.data.get("appliances", None)
        if not appliances:
            _LOGGER.warning("No appliance data available, skipping SSE setup")
            return

        ids = appliances.get_appliance_ids()
        _LOGGER.debug("Electrolux listen_websocket for appliances %s", ",".join(ids))
        if ids is None or len(ids) == 0:
            _LOGGER.debug("No appliances to listen for, skipping SSE setup")
            return

        # watch_for_appliance_state_updates in util.py handles kill-before-restart safely
        try:
            await self.api.watch_for_appliance_state_updates(ids, self.incoming_data)
            _LOGGER.debug(
                "Successfully started SSE listening for %d appliances", len(ids)
            )
        except Exception as ex:
            _LOGGER.error("Failed to start SSE listening: %s", ex)
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
                    _LOGGER.error("Error during websocket renewal: %s", ex)
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
                _LOGGER.error("Electrolux renew SSE failed %s", ex)
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
                _LOGGER.error("Electrolux close SSE failed %s", ex)

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
                "Electrolux get_appliances_list %s %s",
                self.api,
                json.dumps(appliances_list),
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
            _LOGGER.debug("setup_entities: %s", exception)
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
                    "Network error getting required data for appliance %s: %s",
                    appliance_id,
                    ex,
                )
                # Cancel the capabilities task if it hasn't completed
                if not capabilities_task.done():
                    capabilities_task.cancel()
                return
            except Exception as ex:
                _LOGGER.warning(
                    "Failed to get required data for appliance %s: %s", appliance_id, ex
                )
                # Cancel the capabilities task if it hasn't completed
                if not capabilities_task.done():
                    capabilities_task.cancel()
                return

            # Try to get capabilities (optional)
            appliance_capabilities = None
            try:
                appliance_capabilities = await capabilities_task
            except Exception as ex:
                _LOGGER.debug(
                    "Could not get capabilities for appliance %s: %s", appliance_id, ex
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

            _LOGGER.debug("Successfully set up appliance %s", appliance_id)

        except (KeyError, ValueError, TypeError, AttributeError) as ex:
            _LOGGER.error(
                "Data validation error setting up appliance %s: %s",
                appliance_json.get("applianceId"),
                ex,
            )
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as ex:
            _LOGGER.error(
                "Network error setting up appliance %s: %s",
                appliance_json.get("applianceId"),
                ex,
            )
        except Exception:
            _LOGGER.exception(
                "Unexpected error setting up appliance %s",
                appliance_json.get("applianceId"),
            )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data for all appliances concurrently."""
        appliances: Appliances = self.data.get("appliances")  # type: ignore[assignment,union-attr]
        app_dict = appliances.get_appliances()

        if not app_dict:
            return self.data

        async def _update_single(app_id: str, app_obj) -> bool:
            try:
                # Use a strict timeout for the background refresh
                status = await asyncio.wait_for(
                    self.api.get_appliance_state(app_id), timeout=UPDATE_TIMEOUT
                )
                app_obj.update(status)
                return True  # Success
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                error_msg = str(ex).lower()
                # Check if this is an authentication error - these should still fail the update
                if any(
                    keyword in error_msg
                    for keyword in ["401", "unauthorized", "auth", "token"]
                ):
                    _LOGGER.warning("Authentication failed during data update: %s", ex)
                    # Create an issue to trigger reauth flow
                    from homeassistant.helpers import issue_registry

                    issue_registry.async_create_issue(
                        self.hass,
                        DOMAIN,
                        f"invalid_refresh_token_{self.config_entry.entry_id}",
                        is_fixable=True,
                        issue_domain=DOMAIN,
                        severity=issue_registry.IssueSeverity.ERROR,
                        translation_key="invalid_refresh_token",
                        translation_placeholders={
                            "entry_title": self.config_entry.title,
                        },
                    )
                    raise ConfigEntryAuthFailed("Token expired or invalid") from ex
                # For other errors, just log and return failure
                _LOGGER.debug("Failed to update %s during refresh: %s", app_id, ex)
                return False  # Failure

        # Run all updates concurrently
        results = await asyncio.gather(
            *(_update_single(aid, aobj) for aid, aobj in app_dict.items()),
            return_exceptions=True,
        )

        # Check if any auth errors occurred (these should propagate)
        auth_errors = []
        other_errors = []
        successful = 0

        for result in results:
            if isinstance(result, ConfigEntryAuthFailed):
                auth_errors.append(result)
            elif isinstance(result, Exception):
                other_errors.append(result)
            elif result is True:
                successful += 1

        # Propagate authentication errors immediately
        if auth_errors:
            _LOGGER.error(
                "Authentication failed during update (%d appliances)", len(auth_errors)
            )
            raise auth_errors[0]  # Raise first auth error

        # Check if all appliances failed
        if successful == 0 and len(app_dict) > 0:
            _LOGGER.error(
                "All appliance updates failed. Errors: %s",
                [str(e) for e in other_errors[:3]],  # Show first 3 errors
            )
            raise UpdateFailed("All appliance updates failed")

        # Log partial failures
        if other_errors:
            _LOGGER.debug(
                "Some appliances failed to update (%d/%d successful)",
                successful,
                len(app_dict),
            )

        # Periodically clean up removed appliances (once per day)
        # Check if we should run cleanup
        if not hasattr(self, "_last_cleanup_time"):
            self._last_cleanup_time = 0

        import time

        current_time = time.time()
        if current_time - self._last_cleanup_time > CLEANUP_INTERVAL:  # 24 hours
            _LOGGER.debug("Running periodic appliance cleanup")
            await self.cleanup_removed_appliances()
            self._last_cleanup_time = int(current_time)

        return self.data

    async def cleanup_removed_appliances(self) -> None:
        """Remove appliances that no longer exist in the account."""
        try:
            # Get current appliance list from API
            appliances_list = await self.api.get_appliances_list()
            if not appliances_list:
                return

            # Get current appliance IDs
            current_ids = set()
            for appliance_json in appliances_list:
                if appliance_id := appliance_json.get("applianceId"):
                    current_ids.add(appliance_id)

            # Get appliances we're tracking
            tracked_appliances = self.data.get("appliances")
            if not tracked_appliances:
                return

            tracked_ids = set(tracked_appliances.appliances.keys())

            # Find appliances that were removed
            removed_ids = tracked_ids - current_ids

            if removed_ids:
                _LOGGER.info(
                    "Removing %d appliances no longer in account: %s",
                    len(removed_ids),
                    removed_ids,
                )

                # Remove from tracking
                for appliance_id in removed_ids:
                    del tracked_appliances.appliances[appliance_id]

                # Trigger entity registry cleanup
                self.async_set_updated_data(self.data)

        except Exception as ex:
            _LOGGER.debug("Error during appliance cleanup: %s", ex)
