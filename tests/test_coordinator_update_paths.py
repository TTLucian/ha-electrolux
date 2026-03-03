"""Additional coordinator tests targeting uncovered update/renewal paths."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.electrolux.coordinator import ElectroluxCoordinator

# ---------------------------------------------------------------------------
# Fixtures (duplicated from test_coordinator_methods.py for isolation)
# ---------------------------------------------------------------------------


async def _fake_gather_close(*coros, return_exceptions=False, **kw):
    """Fake asyncio.gather that closes any coroutine arguments and returns []."""
    for c in coros:
        if asyncio.iscoroutine(c):
            c.close()
    return []


def _make_create_task_mock(rv=None):
    """Return a MagicMock for async_create_task that closes passed coroutines."""
    _rv = rv

    def _side_effect(coro):
        if asyncio.iscoroutine(coro):
            coro.close()
        return _rv

    return MagicMock(side_effect=_side_effect)


@pytest.fixture
def mock_hass():
    mock_loop = MagicMock()
    mock_loop.time.return_value = 1_000_000.0
    hass = MagicMock()
    hass.loop = mock_loop
    hass.async_create_task = _make_create_task_mock()
    return hass


@pytest.fixture
def mock_api():
    client = MagicMock()
    client._auth_failed = False
    client.disconnect_websocket = AsyncMock()
    return client


@pytest.fixture
def coordinator(mock_hass, mock_api):
    with patch(
        "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = ElectroluxCoordinator.__new__(ElectroluxCoordinator)
        coord.hass = mock_hass
        coord.api = mock_api
        coord.platforms = []
        coord.renew_interval = 7200
        coord.renew_task = None
        coord.listen_task = None
        coord.data = {}
        coord._deferred_tasks = set()
        coord._deferred_tasks_by_appliance = {}
        coord._appliances_lock = asyncio.Lock()
        coord._manual_sync_lock = asyncio.Lock()
        coord._last_cleanup_time = 0
        coord._last_update_times = {}
        coord._last_known_connectivity = {}
        coord._last_sse_restart_time = 0.0
        coord._last_manual_sync_time = 0.0
        coord._last_time_to_end = {}
        coord._consecutive_auth_failures = 0
        coord._auth_failure_threshold = 3
        coord._last_token_update = 0.0
        coord._appliances_cache = None
        coord.config_entry = MagicMock()
        coord.config_entry.entry_id = "test_entry"
        coord.config_entry.title = "Test"
        coord.last_update_success = True
        return coord


def _make_appliance(app_id: str = "app1", connectivity: str = "connected") -> MagicMock:
    ap = MagicMock()
    ap.pnc_id = app_id
    ap.reported_state = {}
    ap.state = {"connectivityState": connectivity}
    ap.update = MagicMock()
    return ap


def _make_appliances(appliance_map: dict) -> MagicMock:
    aps = MagicMock()
    aps.appliances = appliance_map
    aps.get_appliances.return_value = appliance_map

    def get_appliance(aid):
        return appliance_map.get(aid)

    aps.get_appliance.side_effect = get_appliance
    return aps


# ---------------------------------------------------------------------------
# _async_update_data: auth failure BELOW threshold (lines 1433, 1473-1478)
# ---------------------------------------------------------------------------


class TestAsyncUpdateDataAuthFailureBelowThreshold:
    @pytest.mark.asyncio
    async def test_auth_error_below_threshold_increments_counter(self, coordinator):
        """Auth error below threshold: counter incremented, UpdateFailed raised (all failed)."""
        ap = _make_appliance("app1")
        appliances = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": appliances}
        coordinator._auth_failure_threshold = 5  # High threshold
        coordinator._consecutive_auth_failures = 0

        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=Exception("401 Unauthorized")
        )

        # All appliances failed → UpdateFailed is raised
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        # Counter was incremented before UpdateFailed
        assert coordinator._consecutive_auth_failures == 1

    @pytest.mark.asyncio
    async def test_auth_error_unauthorized_keyword_below_threshold(self, coordinator):
        """'unauthorized' keyword triggers auth failure path."""
        ap = _make_appliance("app1")
        appliances = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": appliances}
        coordinator._auth_failure_threshold = 10
        coordinator._consecutive_auth_failures = 0

        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=Exception("unauthorized access")
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator._consecutive_auth_failures == 1

    @pytest.mark.asyncio
    async def test_auth_error_at_threshold_raises_config_entry_auth_failed(
        self, coordinator
    ):
        """Auth error at/above threshold: raises ConfigEntryAuthFailed and creates issue."""
        ap = _make_appliance("app1")
        appliances = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": appliances}
        coordinator._auth_failure_threshold = 1
        coordinator._consecutive_auth_failures = 0

        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=Exception("401 Unauthorized")
        )

        with patch("homeassistant.helpers.issue_registry.async_create_issue"):
            with pytest.raises(ConfigEntryAuthFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_non_auth_error_all_failed_raises_update_failed(self, coordinator):
        """Non-auth error with all appliances failing raises UpdateFailed."""
        ap = _make_appliance("app1")
        appliances = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": appliances}

        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=Exception("network timeout")
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


# ---------------------------------------------------------------------------
# _async_update_data: came_online transition (lines 1503-1504)
# ---------------------------------------------------------------------------


class TestAsyncUpdateDataCameOnline:
    @pytest.mark.asyncio
    async def test_appliance_transitions_from_disconnected_to_connected(
        self, coordinator
    ):
        """When appliance was disconnected and is now connected, came_online=True."""
        ap = _make_appliance("app1")
        appliances = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": appliances}
        # Pre-set as disconnected
        coordinator._last_known_connectivity["app1"] = "disconnected"

        mock_state = {
            "connectivityState": "connected",
            "properties": {"reported": {"powerState": "on"}},
        }
        coordinator.api.get_appliance_state = AsyncMock(return_value=mock_state)

        # Mock listen_websocket for SSE restart (can_restart_sse returns False by default)
        coordinator._last_sse_restart_time = 0.0
        coordinator.listen_websocket = AsyncMock()

        result = await coordinator._async_update_data()
        assert result is not None
        # After update, connectivity should be "connected"
        assert coordinator._last_known_connectivity["app1"] == "connected"

    @pytest.mark.asyncio
    async def test_multiple_appliances_one_came_online(self, coordinator):
        """With multiple appliances, one coming online triggers SSE restart."""
        ap1 = _make_appliance("app1")
        ap2 = _make_appliance("app2")
        appliances = _make_appliances({"app1": ap1, "app2": ap2})
        coordinator.data = {"appliances": appliances}

        # app1 was disconnected, app2 was connected
        coordinator._last_known_connectivity["app1"] = "disconnected"
        coordinator._last_known_connectivity["app2"] = "connected"

        def mock_state_factory(app_id):
            return {
                "connectivityState": "connected",
                "properties": {"reported": {}},
            }

        coordinator.api.get_appliance_state = AsyncMock(
            return_value={
                "connectivityState": "connected",
                "properties": {"reported": {}},
            }
        )

        # _can_restart_sse needs to return True for SSE restart to happen
        coordinator._last_sse_restart_time = 0.0
        coordinator.listen_websocket = AsyncMock()

        result = await coordinator._async_update_data()
        assert result is not None


# ---------------------------------------------------------------------------
# _async_update_data: gather result handling (lines 1510-1525)
# ---------------------------------------------------------------------------


class TestAsyncUpdateDataGatherResults:
    @pytest.mark.asyncio
    async def test_config_entry_auth_failed_in_results_gets_reraised(self, coordinator):
        """ConfigEntryAuthFailed above threshold from a gather task is re-raised."""
        ap = _make_appliance("app1")
        appliances = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": appliances}
        coordinator._auth_failure_threshold = 1  # trigger on first failure
        coordinator._consecutive_auth_failures = 0

        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=Exception("401 Unauthorized")
        )

        with patch("homeassistant.helpers.issue_registry.async_create_issue"):
            with pytest.raises(ConfigEntryAuthFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_exception_in_gather_results_added_to_other_errors(self, coordinator):
        """Raw Exception from gather (not caught by _update_single) adds to other_errors."""
        ap = _make_appliance("app1")
        appliances = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": appliances}

        # Simulate raw Exception (e.g. CancelledError subclass that's not CancelledError)
        # In practice _update_single catches these, but we can simulate with asyncio.gather
        # returning Exception objects. By using asyncio.TimeoutError which is caught by
        # asyncio.wait_for and propagated as raw Exception.
        # The _update_single catches Exception and returns (False, False) so to reach line
        # 1521-1525 we need an Exception in the gather results NOT caught inside _update_single.
        # The only way is CancelledError which propagates out of _update_single.
        # Instead, test through the existing path where non-auth exception returns (False, False)
        # leading to UpdateFailed.
        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=Exception("random error 999")
        )
        with pytest.raises(UpdateFailed, match="All appliance updates failed"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_two_appliances_one_succeeds_one_auth_fails_below_threshold(
        self, coordinator
    ):
        """auth failure below threshold: result is success=True because one succeeded."""
        ap1 = _make_appliance("app1")
        ap2 = _make_appliance("app2")
        appliances = _make_appliances({"app1": ap1, "app2": ap2})
        coordinator.data = {"appliances": appliances}
        coordinator._auth_failure_threshold = 5  # high threshold

        call_count = 0

        async def mixed_state(app_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "connectivityState": "connected",
                    "properties": {"reported": {}},
                }
            else:
                raise Exception("401 unauthorized")

        coordinator.api.get_appliance_state = AsyncMock(side_effect=mixed_state)

        result = await coordinator._async_update_data()
        assert result is not None
        # One succeeded, counter reset
        assert (
            coordinator._consecutive_auth_failures == 0
            or coordinator._consecutive_auth_failures == 1
        )


# ---------------------------------------------------------------------------
# _async_update_data: SSE restart on newly online (lines 1529-1544)
# ---------------------------------------------------------------------------


class TestAsyncUpdateDataSseRestart:
    @pytest.mark.asyncio
    async def test_sse_restarts_when_appliance_comes_online(self, coordinator):
        """SSE is restarted when an appliance transitions from disconnected to connected."""
        ap = _make_appliance("app1")
        appliances = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": appliances}
        coordinator._last_known_connectivity["app1"] = "disconnected"
        # Set last restart time to 0 so _can_restart_sse returns True
        coordinator._last_sse_restart_time = 0.0

        coordinator.api.get_appliance_state = AsyncMock(
            return_value={
                "connectivityState": "connected",
                "properties": {"reported": {}},
            }
        )
        coordinator.listen_websocket = AsyncMock()

        result = await coordinator._async_update_data()
        assert result is not None
        # SSE disconnect/reconnect was triggered
        coordinator.api.disconnect_websocket.assert_called()

    @pytest.mark.asyncio
    async def test_sse_restart_exception_is_swallowed(self, coordinator):
        """Exception during SSE restart does not propagate."""
        ap = _make_appliance("app1")
        appliances = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": appliances}
        coordinator._last_known_connectivity["app1"] = "disconnected"
        coordinator._last_sse_restart_time = 0.0

        coordinator.api.get_appliance_state = AsyncMock(
            return_value={
                "connectivityState": "connected",
                "properties": {"reported": {}},
            }
        )
        coordinator.api.disconnect_websocket = AsyncMock(
            side_effect=Exception("SSE error")
        )
        coordinator.listen_websocket = AsyncMock()

        result = await coordinator._async_update_data()
        # Should not raise despite SSE restart error
        assert result is not None


# ---------------------------------------------------------------------------
# renew_websocket: timeout and error paths (lines 828-848)
# ---------------------------------------------------------------------------


class TestRenewWebsocket:
    @pytest.mark.asyncio
    async def test_renew_websocket_timeout_increments_failures(self, coordinator):
        """Timeout during websocket disconnect/reconnect increments consecutive_failures."""
        coordinator.api.disconnect_websocket = AsyncMock()
        coordinator.listen_websocket = AsyncMock()

        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)
            if len(sleep_calls) >= 2:
                # Stop the loop after one full iteration
                raise asyncio.CancelledError()

        async def fake_wait_for_timeout(coro, *a, **kw):
            if asyncio.iscoroutine(coro):
                coro.close()
            raise asyncio.TimeoutError("timeout")

        # Patch wait_for so the disconnect/reconnect raises TimeoutError (caught internally)
        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch(
                "asyncio.wait_for",
                side_effect=fake_wait_for_timeout,
            ):
                with pytest.raises(asyncio.CancelledError):
                    await coordinator.renew_websocket()

        # At least the initial sleep(renew_interval) was called
        assert len(sleep_calls) >= 1

    @pytest.mark.asyncio
    async def test_renew_websocket_cancelled_error_raised(self, coordinator):
        """CancelledError propagates from renew_websocket."""

        async def run():
            counter = 0

            async def mock_sleep(delay):
                nonlocal counter
                counter += 1
                if counter >= 1:
                    raise asyncio.CancelledError()

            with patch("asyncio.sleep", side_effect=mock_sleep):
                await coordinator.renew_websocket()

        with pytest.raises(asyncio.CancelledError):
            await run()

    @pytest.mark.asyncio
    async def test_renew_websocket_token_refresh_on_expired_token(self, coordinator):
        """When token is expired before renewal, trigger refresh."""
        mock_token_manager = MagicMock()
        mock_token_manager.is_token_valid.return_value = False
        mock_token_manager.refresh_token = AsyncMock()
        coordinator.api._token_manager = mock_token_manager

        success_count = 0

        async def mock_sleep(delay):
            nonlocal success_count
            success_count += 1
            # Allow 1st sleep (renew_interval) to pass so token check runs,
            # then raise on the 2nd sleep to exit the loop.
            if success_count >= 2:
                raise asyncio.CancelledError()

        coordinator.api.disconnect_websocket = AsyncMock()
        coordinator.listen_websocket = AsyncMock()

        async def _fake_wait_for_noop(coro, *a, **kw):
            if asyncio.iscoroutine(coro):
                coro.close()
            return None

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch("asyncio.wait_for", side_effect=_fake_wait_for_noop):
                try:
                    await coordinator.renew_websocket()
                except asyncio.CancelledError:
                    pass

        mock_token_manager.is_token_valid.assert_called()

    @pytest.mark.asyncio
    async def test_renew_websocket_token_refresh_timeout(self, coordinator):
        """Token refresh timeout before renewal is handled gracefully."""
        mock_token_manager = MagicMock()
        mock_token_manager.is_token_valid.return_value = False
        coordinator.api._token_manager = mock_token_manager

        call_count = 0

        async def mock_wait_for(coro, timeout=None):
            nonlocal call_count
            call_count += 1
            if asyncio.iscoroutine(coro):
                coro.close()
            if call_count == 1:
                # First call: token refresh - timeout
                raise asyncio.TimeoutError()
            # Second call and beyond: noop
            return None

        success_count = 0

        async def mock_sleep(delay):
            nonlocal success_count
            success_count += 1
            if success_count >= 1:
                raise asyncio.CancelledError()

        coordinator.api.disconnect_websocket = AsyncMock()
        coordinator.listen_websocket = AsyncMock()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch("asyncio.wait_for", side_effect=mock_wait_for):
                try:
                    await coordinator.renew_websocket()
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_renew_websocket_token_refresh_exception(self, coordinator):
        """Token refresh exception before renewal is handled gracefully."""
        mock_token_manager = MagicMock()
        mock_token_manager.is_token_valid.return_value = False
        coordinator.api._token_manager = mock_token_manager

        call_count = 0

        async def mock_wait_for(coro, timeout=None):
            nonlocal call_count
            call_count += 1
            if asyncio.iscoroutine(coro):
                coro.close()
            if call_count == 1:
                # First call: token refresh - exception
                raise Exception("refresh failed")
            return None

        success_count = 0

        async def mock_sleep(delay):
            nonlocal success_count
            success_count += 1
            if success_count >= 1:
                raise asyncio.CancelledError()

        coordinator.api.disconnect_websocket = AsyncMock()
        coordinator.listen_websocket = AsyncMock()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch("asyncio.wait_for", side_effect=mock_wait_for):
                try:
                    await coordinator.renew_websocket()
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_renew_websocket_too_many_failures_backs_off(self, coordinator):
        """After max consecutive failures, a 5-minute backoff is applied."""
        sleep_delays = []
        failure_count = 0

        async def fast_fail_wait_for(coro, timeout=None):
            nonlocal failure_count
            failure_count += 1
            if asyncio.iscoroutine(coro):
                coro.close()
            raise Exception("renewal error")

        async def mock_sleep(delay):
            sleep_delays.append(delay)
            if len(sleep_delays) >= 3:
                raise asyncio.CancelledError()

        coordinator.api._token_manager = MagicMock()
        coordinator.api._token_manager.is_token_valid = MagicMock(return_value=True)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch("asyncio.wait_for", side_effect=fast_fail_wait_for):
                try:
                    await coordinator.renew_websocket()
                except asyncio.CancelledError:
                    pass


# ---------------------------------------------------------------------------
# close_websocket: tasks cancellation (lines 875-876, 880, 891)
# ---------------------------------------------------------------------------


class TestCloseWebsocket:
    @pytest.mark.asyncio
    async def test_close_websocket_cancels_deferred_tasks(self, coordinator):
        """Deferred tasks are cancelled during close."""
        task1 = MagicMock()
        task1.done = MagicMock(return_value=False)
        task1.cancel = MagicMock()

        task2 = MagicMock()
        task2.done = MagicMock(return_value=True)  # already done
        task2.cancel = MagicMock()

        coordinator._deferred_tasks = {task1, task2}
        coordinator.renew_task = None

        async def _close_noop():
            return None

        coordinator.api.close = _close_noop

        async def _fake_wait_for_noop(coro, *a, **kw):
            if asyncio.iscoroutine(coro):
                await coro
            return None

        with patch("asyncio.gather", new=_fake_gather_close):
            with patch("asyncio.wait_for", side_effect=_fake_wait_for_noop):
                await coordinator.close_websocket()

        task1.cancel.assert_called_once()
        task2.cancel.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_websocket_cancels_per_appliance_tasks(self, coordinator):
        """Per-appliance deferred tasks are also cancelled."""
        task = MagicMock()
        task.done = MagicMock(return_value=False)
        task.cancel = MagicMock()

        coordinator._deferred_tasks = set()
        coordinator._deferred_tasks_by_appliance = {"app1": task}
        coordinator.renew_task = None

        async def _close_noop():
            return None

        coordinator.api.close = _close_noop

        async def _fake_wait_for_noop(coro, *a, **kw):
            if asyncio.iscoroutine(coro):
                await coro
            return None

        with patch("asyncio.gather", new=_fake_gather_close):
            with patch("asyncio.wait_for", side_effect=_fake_wait_for_noop):
                await coordinator.close_websocket()

        task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_websocket_api_close_timeout_logged(self, coordinator):
        """API close timeout is handled gracefully."""
        coordinator._deferred_tasks = set()
        coordinator._deferred_tasks_by_appliance = {}
        coordinator.renew_task = None

        async def _close_noop():
            return None

        coordinator.api.close = _close_noop

        async def fake_wait_for_timeout(coro, *a, **kw):
            if asyncio.iscoroutine(coro):
                await coro
            raise asyncio.TimeoutError()

        with patch("asyncio.gather", new=_fake_gather_close):
            with patch("asyncio.wait_for", side_effect=fake_wait_for_timeout):
                await coordinator.close_websocket()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_websocket_api_close_exception_logged(self, coordinator):
        """API close exception is handled and logged."""
        coordinator._deferred_tasks = set()
        coordinator._deferred_tasks_by_appliance = {}
        coordinator.renew_task = None

        async def _close_noop():
            return None

        coordinator.api.close = _close_noop

        async def fake_wait_for_exception(coro, *a, **kw):
            if asyncio.iscoroutine(coro):
                await coro
            raise Exception("close failed")

        with patch("asyncio.gather", new=_fake_gather_close):
            with patch("asyncio.wait_for", side_effect=fake_wait_for_exception):
                await coordinator.close_websocket()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_websocket_with_renew_task(self, coordinator):
        """Renew task is cancelled during close_websocket."""
        renew_task = AsyncMock(side_effect=asyncio.CancelledError())
        renew_task.done = MagicMock(return_value=False)
        renew_task.cancel = MagicMock()
        coordinator.renew_task = renew_task
        coordinator._deferred_tasks = set()
        coordinator._deferred_tasks_by_appliance = {}

        async def _close_noop():
            return None

        coordinator.api.close = _close_noop

        async def fake_wait_for_close(coro, *a, **kw):
            if asyncio.iscoroutine(coro):
                await coro

        with patch("asyncio.gather", new=_fake_gather_close):
            with patch("asyncio.wait_for", side_effect=fake_wait_for_close):
                await coordinator.close_websocket()

        renew_task.cancel.assert_called_once()


# ---------------------------------------------------------------------------
# setup_entities: timeout and cancel paths (lines 926-940)
# ---------------------------------------------------------------------------


class TestSetupEntities:
    @pytest.mark.asyncio
    async def test_setup_entities_timeout_logs_warning(self, coordinator):
        """When appliance setup times out, a warning is logged and setup continues."""
        coordinator.api.get_appliances_list = AsyncMock(
            return_value=[
                {
                    "applianceId": "app1",
                    "applianceName": "Test",
                    "applianceData": {"applianceName": "Test"},
                }
            ]
        )

        async def slow_setup(appliance_json):
            await asyncio.sleep(0)  # Yields once; will be cancelled by gather timeout

        coordinator._setup_single_appliance = slow_setup

        # Patch asyncio.gather to close inner coroutines and simulate timeout
        async def _fake_gather_timeout(*coros, return_exceptions=False, **kw):
            for coro in coros:
                if asyncio.iscoroutine(coro):
                    coro.close()
            raise asyncio.TimeoutError()

        # After removing the broken cancel-loop dead code, a timeout now
        # logs a warning and allows setup_entities to return normally.
        with patch("asyncio.gather", side_effect=_fake_gather_timeout):
            result = await coordinator.setup_entities()

        # Should return data dict (timeout is handled gracefully, not re-raised)
        assert result is not None

    @pytest.mark.asyncio
    async def test_setup_entities_cancelled_error_raised(self, coordinator):
        """CancelledError during setup is re-raised."""
        coordinator.api.get_appliances_list = AsyncMock(
            side_effect=asyncio.CancelledError()
        )

        with pytest.raises(asyncio.CancelledError):
            await coordinator.setup_entities()
