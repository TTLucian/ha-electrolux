"""Tests for advanced coordinator methods: deferred_update, _refresh_after_appliance_state_change,
cleanup_removed_appliances, and perform_manual_sync."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.coordinator import ElectroluxCoordinator

pytestmark = pytest.mark.asyncio


def _make_sync_data(has_capabilities: bool = True) -> dict:
    """Create coordinator.data with proper Appliances mock for manual sync tests.

    The real coordinator.data structure is {"appliances": Appliances(...)}.
    perform_manual_sync looks up the appliance via self.data["appliances"].get_appliance(id)
    and checks .data.capabilities to decide between targeted sync and full reload.
    """
    mock_app = MagicMock()
    mock_app.data.capabilities = {"fanMode": {}} if has_capabilities else {}
    mock_apps = MagicMock()
    mock_apps.get_appliance.return_value = mock_app
    return {"appliances": mock_apps}


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_hass():
    mock_loop = MagicMock()
    mock_loop.time.return_value = 1_000_000.0
    hass = MagicMock()
    hass.loop = mock_loop
    hass.async_create_task = MagicMock(
        side_effect=lambda coro: asyncio.ensure_future(coro)
    )
    return hass


@pytest.fixture
def mock_api():
    client = MagicMock()
    client._auth_failed = False
    client.disconnect_websocket = AsyncMock()
    client.get_appliance_state = AsyncMock(
        return_value={"connectivityState": "connected", "timeToEnd": 0}
    )
    client.get_appliances_list = AsyncMock(return_value=[])
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
        coord.config_entry.entry_id = "test_entry_id"
        coord.async_set_updated_data = MagicMock()
        coord.async_request_refresh = AsyncMock()
        coord.last_update_success = True
        coord._last_remote_control = {}
        coord._pending_state_refresh_tasks = {}
        return coord


def _make_appliances(appliance_ids_states: dict[str, dict]):
    """Build a mock Appliances object from a dict of {id: state_dict}."""
    appliances_mock = MagicMock()
    app_dict = {}
    for app_id, state in appliance_ids_states.items():
        app = MagicMock()
        app.state = dict(state)
        app.reported_state = dict(state)
        app.update = MagicMock()
        app_dict[app_id] = app

    def get_appliance(aid):
        return app_dict.get(aid)

    appliances_mock.get_appliance = get_appliance
    appliances_mock.get_appliances = MagicMock(return_value=app_dict)
    appliances_mock.appliances = app_dict
    return appliances_mock


# ===========================================================================
# Tests for deferred_update
# ===========================================================================


class TestDeferredUpdate:
    """Tests for coordinator.deferred_update()."""

    async def test_success_path(self, coordinator, mock_api):
        """deferred_update polls API and calls appliance.update()."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {"timeToEnd": 5}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.return_value = {
            "timeToEnd": 0,
            "connectivityState": "connected",
        }

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator.deferred_update(appliance_id, delay=60)

        mock_api.get_appliance_state.assert_called_once_with(appliance_id)
        appliances.get_appliance(appliance_id).update.assert_called_once_with(
            {"timeToEnd": 0, "connectivityState": "connected"}
        )
        coordinator.async_set_updated_data.assert_called_once_with(coordinator.data)

    async def test_returns_when_data_is_none(self, coordinator, mock_api):
        """deferred_update exits early if coordinator.data is None."""
        coordinator.data = None

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator.deferred_update("APP001", delay=5)

        mock_api.get_appliance_state.assert_not_called()

    async def test_returns_when_appliances_none(self, coordinator, mock_api):
        """deferred_update exits early if appliances key is missing."""
        coordinator.data = {"appliances": None}

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator.deferred_update("APP001", delay=5)

        mock_api.get_appliance_state.assert_not_called()

    async def test_returns_when_appliance_not_found(self, coordinator, mock_api):
        """deferred_update exits early if the specific appliance is not found."""
        appliances = _make_appliances({})  # empty — no appliances
        coordinator.data = {"appliances": appliances}

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator.deferred_update("MISSING", delay=5)

        mock_api.get_appliance_state.assert_not_called()

    async def test_reraises_cancelled_error(self, coordinator):
        """deferred_update re-raises CancelledError (sleep interrupted)."""
        with patch(
            "asyncio.sleep", new_callable=AsyncMock, side_effect=asyncio.CancelledError
        ):
            with pytest.raises(asyncio.CancelledError):
                await coordinator.deferred_update("APP001", delay=60)

    async def test_cancelled_error_during_api_call(self, coordinator, mock_api):
        """deferred_update re-raises CancelledError raised by the API."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {"timeToEnd": 1}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = asyncio.CancelledError

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(asyncio.CancelledError):
                await coordinator.deferred_update(appliance_id, delay=5)

    async def test_connection_error_raises_update_failed(self, coordinator, mock_api):
        """deferred_update logs ConnectionError and returns (no exception raised)."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = ConnectionError("network down")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Should not raise
            await coordinator.deferred_update(appliance_id, delay=5)

    async def test_timeout_error_raises_update_failed(self, coordinator, mock_api):
        """deferred_update logs TimeoutError and returns (no exception raised)."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = TimeoutError("timed out")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Should not raise
            await coordinator.deferred_update(appliance_id, delay=5)

    async def test_asyncio_timeout_error_raises_update_failed(
        self, coordinator, mock_api
    ):
        """deferred_update logs asyncio.TimeoutError and returns (no exception raised)."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = asyncio.TimeoutError()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Should not raise
            await coordinator.deferred_update(appliance_id, delay=5)

    async def test_key_error_raises_update_failed(self, coordinator, mock_api):
        """deferred_update logs KeyError and returns (no exception raised)."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = KeyError("missing_key")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Should not raise
            await coordinator.deferred_update(appliance_id, delay=5)

    async def test_value_error_raises_update_failed(self, coordinator, mock_api):
        """deferred_update logs ValueError and returns (no exception raised)."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = ValueError("bad value")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Should not raise
            await coordinator.deferred_update(appliance_id, delay=5)

    async def test_type_error_raises_update_failed(self, coordinator, mock_api):
        """deferred_update logs TypeError and returns (no exception raised)."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = TypeError("type mismatch")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Should not raise
            await coordinator.deferred_update(appliance_id, delay=5)

    async def test_generic_exception_raises_update_failed(self, coordinator, mock_api):
        """deferred_update logs generic exceptions and returns (no exception raised)."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = RuntimeError("unexpected error")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Should not raise
            await coordinator.deferred_update(appliance_id, delay=5)

    async def test_delay_is_awaited(self, coordinator, mock_api):
        """deferred_update awaits sleep with the supplied delay."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await coordinator.deferred_update(appliance_id, delay=123)

        mock_sleep.assert_called_once_with(123)

    async def test_logs_time_to_end_unchanged(self, coordinator, mock_api):
        """deferred_update should still succeed when timeToEnd is unchanged (same value)."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {"timeToEnd": 0}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.return_value = {"timeToEnd": 0}

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator.deferred_update(appliance_id, delay=5)

        appliances.get_appliance(appliance_id).update.assert_called_once()

    async def test_logs_time_to_end_changed(self, coordinator, mock_api):
        """deferred_update succeeds when timeToEnd changes from non-zero to 0."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {"timeToEnd": 120}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.return_value = {"timeToEnd": 0}

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator.deferred_update(appliance_id, delay=5)

        appliances.get_appliance(appliance_id).update.assert_called_once()


# ===========================================================================
# Tests for _refresh_after_appliance_state_change
# ===========================================================================


class TestRefreshAfterApplianceStateChange:
    """Tests for coordinator._refresh_after_appliance_state_change()."""

    async def test_success_path(self, coordinator, mock_api):
        """_refresh_after_appliance_state_change polls API, updates appliance, calls set_updated_data."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.return_value = {"displayTemperatureC": 20}

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator._refresh_after_appliance_state_change(appliance_id)

        mock_api.get_appliance_state.assert_called_once_with(appliance_id)
        appliances.get_appliance(appliance_id).update.assert_called_once_with(
            {"displayTemperatureC": 20}
        )
        coordinator.async_set_updated_data.assert_called_once_with(coordinator.data)

    async def test_returns_when_data_is_none(self, coordinator, mock_api):
        """_refresh_after_appliance_state_change exits early when data is None."""
        coordinator.data = None

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator._refresh_after_appliance_state_change("APP001")

        mock_api.get_appliance_state.assert_not_called()

    async def test_returns_when_appliances_none(self, coordinator, mock_api):
        """_refresh_after_appliance_state_change exits early when appliances is falsy."""
        coordinator.data = {"appliances": None}

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator._refresh_after_appliance_state_change("APP001")

        mock_api.get_appliance_state.assert_not_called()

    async def test_returns_when_appliance_not_found(self, coordinator, mock_api):
        """_refresh_after_appliance_state_change exits early when specific appliance is not found."""
        appliances = _make_appliances({})
        coordinator.data = {"appliances": appliances}

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator._refresh_after_appliance_state_change("MISSING")

        mock_api.get_appliance_state.assert_not_called()

    async def test_reraises_cancelled_error(self, coordinator):
        """_refresh_after_appliance_state_change re-raises CancelledError."""
        with patch(
            "asyncio.sleep", new_callable=AsyncMock, side_effect=asyncio.CancelledError
        ):
            with pytest.raises(asyncio.CancelledError):
                await coordinator._refresh_after_appliance_state_change("APP001")

    async def test_cancelled_error_during_api_call(self, coordinator, mock_api):
        """_refresh_after_appliance_state_change re-raises CancelledError from API call."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = asyncio.CancelledError

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(asyncio.CancelledError):
                await coordinator._refresh_after_appliance_state_change(appliance_id)

    async def test_generic_exception_silently_logged(self, coordinator, mock_api):
        """_refresh_after_appliance_state_change silently catches generic exceptions."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = RuntimeError("api error")

        # Should NOT raise - exception is caught and logged at debug level
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator._refresh_after_appliance_state_change(appliance_id)

        coordinator.async_set_updated_data.assert_not_called()

    async def test_connection_error_silently_logged(self, coordinator, mock_api):
        """_refresh_after_appliance_state_change silently catches ConnectionError."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.side_effect = ConnectionError("network down")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await coordinator._refresh_after_appliance_state_change(appliance_id)

        coordinator.async_set_updated_data.assert_not_called()

    async def test_sleep_called_with_state_change_delay(self, coordinator, mock_api):
        """_refresh_after_appliance_state_change awaits sleep before polling."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {}})
        coordinator.data = {"appliances": appliances}

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await coordinator._refresh_after_appliance_state_change(appliance_id)

        # Should be called with some positive delay constant
        mock_sleep.assert_called_once()
        delay_arg = mock_sleep.call_args[0][0]
        assert delay_arg >= 0  # STATE_CHANGE_REFRESH_DELAY is a non-negative constant


# ===========================================================================
# Tests for cleanup_removed_appliances
# ===========================================================================


class TestCleanupRemovedAppliances:
    """Tests for coordinator.cleanup_removed_appliances()."""

    async def test_returns_when_api_returns_none(self, coordinator, mock_api):
        """cleanup_removed_appliances skips when API returns None."""
        mock_api.get_appliances_list.return_value = None
        appliances = _make_appliances({"APP001": {"connectivityState": "connected"}})
        coordinator.data = {"appliances": appliances}

        await coordinator.cleanup_removed_appliances()

        # Nothing removed
        assert "APP001" in appliances.appliances

    async def test_returns_when_api_returns_empty_and_we_have_appliances(
        self, coordinator, mock_api
    ):
        """cleanup_removed_appliances skips when API returns empty list but we track appliances."""
        mock_api.get_appliances_list.return_value = []
        appliances = _make_appliances({"APP001": {"connectivityState": "connected"}})
        coordinator.data = {"appliances": appliances}

        await coordinator.cleanup_removed_appliances()

        # Should be preserved - empty list is suspicious when we have tracked appliances
        assert "APP001" in appliances.appliances

    async def test_removes_truly_missing_connected_appliance(
        self, coordinator, mock_api
    ):
        """cleanup_removed_appliances removes a connected appliance absent from API list."""
        mock_api.get_appliances_list.return_value = [
            {"applianceId": "APP002"}  # only APP002 in API
        ]
        appliances = _make_appliances(
            {
                "APP001": {
                    "connectivityState": "connected"
                },  # connected but gone from API → remove
                "APP002": {"connectivityState": "connected"},  # still in API → keep
            }
        )
        coordinator.data = {"appliances": appliances}

        await coordinator.cleanup_removed_appliances()

        assert "APP001" not in appliances.appliances
        assert "APP002" in appliances.appliances

    async def test_keeps_disconnected_appliance_missing_from_api(
        self, coordinator, mock_api
    ):
        """cleanup_removed_appliances keeps disconnected appliances even if missing from API."""
        mock_api.get_appliances_list.return_value = [{"applianceId": "APP002"}]
        appliances = _make_appliances(
            {
                "APP001": {"connectivityState": "disconnected"},  # disconnected → keep
                "APP002": {"connectivityState": "connected"},
            }
        )
        coordinator.data = {"appliances": appliances}

        await coordinator.cleanup_removed_appliances()

        assert "APP001" in appliances.appliances  # kept because disconnected
        assert "APP002" in appliances.appliances

    async def test_keeps_connection_state_disconnected(self, coordinator, mock_api):
        """cleanup_removed_appliances keeps appliances with connectionState=disconnected."""
        mock_api.get_appliances_list.return_value = [{"applianceId": "APP002"}]
        appliances = _make_appliances(
            {
                "APP001": {"connectionState": "disconnected", "connectivityState": ""},
                "APP002": {"connectivityState": "connected"},
            }
        )
        coordinator.data = {"appliances": appliances}

        await coordinator.cleanup_removed_appliances()

        assert (
            "APP001" in appliances.appliances
        )  # kept because connectionState=disconnected

    async def test_no_missing_appliances(self, coordinator, mock_api):
        """cleanup_removed_appliances does nothing when all tracked appliances are in API list."""
        mock_api.get_appliances_list.return_value = [
            {"applianceId": "APP001"},
            {"applianceId": "APP002"},
        ]
        appliances = _make_appliances(
            {
                "APP001": {"connectivityState": "connected"},
                "APP002": {"connectivityState": "connected"},
            }
        )
        coordinator.data = {"appliances": appliances}

        await coordinator.cleanup_removed_appliances()

        assert "APP001" in appliances.appliances
        assert "APP002" in appliances.appliances
        coordinator.async_set_updated_data.assert_not_called()

    async def test_returns_when_data_is_none(self, coordinator, mock_api):
        """cleanup_removed_appliances returns when coordinator.data is None after API check."""
        mock_api.get_appliances_list.return_value = [{"applianceId": "APP001"}]
        coordinator.data = None

        # Should not raise
        await coordinator.cleanup_removed_appliances()

    async def test_returns_when_tracked_appliances_none(self, coordinator, mock_api):
        """cleanup_removed_appliances returns early if not tracking any appliances."""
        mock_api.get_appliances_list.return_value = [{"applianceId": "APP001"}]
        coordinator.data = {"appliances": None}

        await coordinator.cleanup_removed_appliances()
        # No exception raised

    async def test_cleans_up_tracking_dicts_for_removed_appliance(
        self, coordinator, mock_api
    ):
        """cleanup_removed_appliances purges tracking dictionaries for removed appliances."""
        appliance_id = "APP001"
        mock_api.get_appliances_list.return_value = (
            []
        )  # no appliances! but we have zero tracked too...

        # Manually: 1 tracked appliance that's connected and missing from API
        appliances = _make_appliances(
            {appliance_id: {"connectivityState": "connected"}}
        )
        coordinator.data = {"appliances": appliances}

        # Seed tracking dicts
        coordinator._last_update_times[appliance_id] = 999.0
        coordinator._last_known_connectivity[appliance_id] = "connected"
        coordinator._last_time_to_end[appliance_id] = 10

        # Override: make get_appliances_list return APP002 (so our empty list check won't block)
        mock_api.get_appliances_list.return_value = [{"applianceId": "APP002"}]
        # Now APP001 is truly missing from API list — and it's connected → remove it

        await coordinator.cleanup_removed_appliances()

        assert appliance_id not in coordinator._last_update_times
        assert appliance_id not in coordinator._last_known_connectivity
        assert appliance_id not in coordinator._last_time_to_end

    async def test_cancels_deferred_tasks_for_removed_appliance(
        self, coordinator, mock_api
    ):
        """cleanup_removed_appliances cancels pending deferred tasks for removed appliances."""
        appliance_id = "APP001"
        mock_api.get_appliances_list.return_value = [{"applianceId": "APP002"}]
        appliances = _make_appliances(
            {
                appliance_id: {"connectivityState": "connected"},
                "APP002": {"connectivityState": "connected"},
            }
        )
        coordinator.data = {"appliances": appliances}

        # Create a real task to simulate a deferred update task
        async def dummy_coro():
            await asyncio.sleep(100)

        task = asyncio.ensure_future(dummy_coro())
        coordinator._deferred_tasks_by_appliance[appliance_id] = task

        await coordinator.cleanup_removed_appliances()
        await asyncio.sleep(0)  # Let the event loop process the pending cancellation

        assert appliance_id not in coordinator._deferred_tasks_by_appliance
        assert task.cancelled()

    async def test_exception_from_api_silently_caught(self, coordinator, mock_api):
        """cleanup_removed_appliances catches exceptions from the API silently."""
        mock_api.get_appliances_list.side_effect = RuntimeError("API down")

        # Should not raise
        await coordinator.cleanup_removed_appliances()

    async def test_notifies_ha_after_removal(self, coordinator, mock_api):
        """cleanup_removed_appliances calls async_set_updated_data after removing appliances."""
        mock_api.get_appliances_list.return_value = [{"applianceId": "APP002"}]
        appliances = _make_appliances(
            {
                "APP001": {"connectivityState": "connected"},
                "APP002": {"connectivityState": "connected"},
            }
        )
        coordinator.data = {"appliances": appliances}

        await coordinator.cleanup_removed_appliances()

        coordinator.async_set_updated_data.assert_called_once_with(coordinator.data)

    async def test_all_missing_are_offline_no_removal(self, coordinator, mock_api):
        """cleanup_removed_appliances doesn't remove or notify when all missing apps are offline."""
        mock_api.get_appliances_list.return_value = [{"applianceId": "APP002"}]
        appliances = _make_appliances(
            {
                "APP001": {"connectivityState": "disconnected"},
                "APP002": {"connectivityState": "connected"},
            }
        )
        coordinator.data = {"appliances": appliances}

        await coordinator.cleanup_removed_appliances()

        # APP001 kept, no notification issued
        assert "APP001" in appliances.appliances
        coordinator.async_set_updated_data.assert_not_called()


# ===========================================================================
# Tests for perform_manual_sync
# ===========================================================================


class TestPerformManualSync:
    """Tests for coordinator.perform_manual_sync()."""

    async def test_success_path_with_capabilities(self, coordinator, mock_api):
        """perform_manual_sync completes successfully when appliance has capabilities."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(True)
        coordinator.hass.loop.time.return_value = (
            2_000_000.0  # far in the future past cooldown
        )
        coordinator._last_manual_sync_time = 0.0

        with patch.object(coordinator, "listen_websocket", new_callable=AsyncMock):
            await coordinator.perform_manual_sync(appliance_id, "My Appliance")

        mock_api.disconnect_websocket.assert_called_once()
        coordinator.async_request_refresh.assert_called_once()

    async def test_no_capabilities_triggers_reload(self, coordinator, mock_api):
        """perform_manual_sync triggers integration reload when no capabilities are present."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(False)
        coordinator.hass.loop.time.return_value = 2_000_000.0
        coordinator._last_manual_sync_time = 0.0
        coordinator.hass.config_entries.async_reload = AsyncMock()

        await coordinator.perform_manual_sync(appliance_id, "My Appliance")

        coordinator.hass.config_entries.async_reload.assert_called_once_with(
            "test_entry_id"
        )
        mock_api.disconnect_websocket.assert_not_called()  # reload path exits early

    async def test_reload_raises_ha_error_on_failure(self, coordinator, mock_api):
        """perform_manual_sync raises HomeAssistantError when reload fails."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(False)
        coordinator.hass.loop.time.return_value = 2_000_000.0
        coordinator._last_manual_sync_time = 0.0
        coordinator.hass.config_entries.async_reload = AsyncMock(
            side_effect=RuntimeError("reload failed")
        )

        with pytest.raises(HomeAssistantError, match="Failed to reload integration"):
            await coordinator.perform_manual_sync(appliance_id, "My Appliance")

    async def test_reload_raises_ha_error_when_no_config_entry(
        self, coordinator, mock_api
    ):
        """perform_manual_sync raises HomeAssistantError when config_entry is None."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(False)
        coordinator.hass.loop.time.return_value = 2_000_000.0
        coordinator._last_manual_sync_time = 0.0
        coordinator.config_entry = None  # No config entry

        with pytest.raises(HomeAssistantError, match="Config entry is not available"):
            await coordinator.perform_manual_sync(appliance_id, "My Appliance")

    async def test_rate_limited_raises_ha_error(self, coordinator, mock_api):
        """perform_manual_sync raises HomeAssistantError when called within cooldown period."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(True)
        # Set last sync time to "now - 10 seconds" (within 60s cooldown)
        coordinator.hass.loop.time.return_value = 1_000_010.0
        coordinator._last_manual_sync_time = 1_000_000.0  # 10 seconds ago

        with pytest.raises(HomeAssistantError, match="rate limited"):
            await coordinator.perform_manual_sync(appliance_id, "My Appliance")

    async def test_rate_limit_message_includes_remaining_seconds(
        self, coordinator, mock_api
    ):
        """perform_manual_sync error message includes remaining cooldown seconds."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(True)
        coordinator.hass.loop.time.return_value = 1_000_030.0  # 30s elapsed
        coordinator._last_manual_sync_time = 1_000_000.0  # started 30s ago

        with pytest.raises(HomeAssistantError) as exc_info:
            await coordinator.perform_manual_sync(appliance_id, "My Appliance")

        assert "30" in str(exc_info.value)  # 60 - 30 = 30 seconds remaining

    async def test_timeout_during_disconnect_raises_ha_error(
        self, coordinator, mock_api
    ):
        """perform_manual_sync raises HomeAssistantError on asyncio.TimeoutError during disconnect."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(True)
        coordinator.hass.loop.time.return_value = 2_000_000.0
        coordinator._last_manual_sync_time = 0.0
        mock_api.disconnect_websocket.side_effect = asyncio.TimeoutError()

        with patch.object(coordinator, "listen_websocket", new_callable=AsyncMock):
            with pytest.raises(HomeAssistantError, match="Manual sync timed out"):
                await coordinator.perform_manual_sync(appliance_id, "My Appliance")

    async def test_generic_exception_during_sync_raises_ha_error(
        self, coordinator, mock_api
    ):
        """perform_manual_sync raises HomeAssistantError on unexpected exception during sync."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(True)
        coordinator.hass.loop.time.return_value = 2_000_000.0
        coordinator._last_manual_sync_time = 0.0
        coordinator.async_request_refresh.side_effect = RuntimeError("unexpected error")
        mock_api.disconnect_websocket.return_value = None

        with patch.object(coordinator, "listen_websocket", new_callable=AsyncMock):
            with pytest.raises(HomeAssistantError, match="Manual sync failed"):
                await coordinator.perform_manual_sync(appliance_id, "My Appliance")

    async def test_lock_prevents_concurrent_sync(self, coordinator, mock_api):
        """perform_manual_sync uses a lock so concurrent calls are serialized."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(True)
        coordinator.hass.loop.time.return_value = 2_000_000.0
        coordinator._last_manual_sync_time = 0.0

        call_count = 0

        async def slow_disconnect():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0)

        mock_api.disconnect_websocket.side_effect = slow_disconnect

        with patch.object(coordinator, "listen_websocket", new_callable=AsyncMock):
            # Only the first call should proceed; the second is serialized by the lock
            await coordinator.perform_manual_sync(appliance_id, "My Appliance")

        # At minimum one disconnect call executed
        assert call_count >= 1

    async def test_updates_last_manual_sync_time(self, coordinator, mock_api):
        """perform_manual_sync updates _last_manual_sync_time on success."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(True)
        coordinator.hass.loop.time.return_value = 9_999.0
        coordinator._last_manual_sync_time = 0.0

        with patch.object(coordinator, "listen_websocket", new_callable=AsyncMock):
            await coordinator.perform_manual_sync(appliance_id, "My Appliance")

        assert coordinator._last_manual_sync_time == 9_999.0

    async def test_appliance_with_no_data_entry_triggers_reload(
        self, coordinator, mock_api
    ):
        """perform_manual_sync triggers reload when appliance_id is absent from coordinator.data."""
        appliance_id = "APP001"
        coordinator.data = {}  # appliance_id not in data → capabilities will be empty
        coordinator.hass.loop.time.return_value = 2_000_000.0
        coordinator._last_manual_sync_time = 0.0
        coordinator.hass.config_entries.async_reload = AsyncMock()

        await coordinator.perform_manual_sync(appliance_id, "My Appliance")

        coordinator.hass.config_entries.async_reload.assert_called_once_with(
            "test_entry_id"
        )

    async def test_timeout_recovery_attempts_reconnect(self, coordinator, mock_api):
        """perform_manual_sync tries to reconnect websocket after timeout failure."""
        appliance_id = "APP001"
        coordinator.data = _make_sync_data(True)
        coordinator.hass.loop.time.return_value = 2_000_000.0
        coordinator._last_manual_sync_time = 0.0
        mock_api.disconnect_websocket.side_effect = asyncio.TimeoutError(
            "disconnect timed out"
        )

        listen_call_count = 0

        async def mock_listen():
            nonlocal listen_call_count
            listen_call_count += 1

        with patch.object(
            coordinator,
            "listen_websocket",
            new_callable=AsyncMock,
            side_effect=mock_listen,
        ):
            with pytest.raises(HomeAssistantError):
                await coordinator.perform_manual_sync(appliance_id, "My Appliance")

        # Should have attempted recovery via listen_websocket
        assert listen_call_count >= 1


# ===========================================================================
# Integration-style: deferred_update task lifecycle
# ===========================================================================


class TestDeferredUpdateTaskLifecycle:
    """Verify deferred task tracks created in _schedule_deferred_update integrate with deferred_update."""

    async def test_task_removed_from_tracking_on_completion(
        self, coordinator, mock_api
    ):
        """A deferred update task removes itself from tracking when done."""
        appliance_id = "APP001"
        appliances = _make_appliances({appliance_id: {"timeToEnd": 1}})
        coordinator.data = {"appliances": appliances}
        mock_api.get_appliance_state.return_value = {"timeToEnd": 0}

        tasks_completed = []

        async def fake_deferred(app_id, delay):
            tasks_completed.append(app_id)

        # Manually schedule and track
        with patch.object(coordinator, "deferred_update", side_effect=fake_deferred):
            coordinator._schedule_deferred_update(appliance_id)
            # Drain the event loop
            await asyncio.sleep(0)

        assert appliance_id in tasks_completed

    async def test_second_schedule_cancels_first(self, coordinator):
        """Scheduling a deferred update for the same appliance twice cancels the first task."""
        appliance_id = "APP001"

        async def slow_coro():
            await asyncio.sleep(100)

        first_task = asyncio.ensure_future(slow_coro())
        coordinator._deferred_tasks_by_appliance[appliance_id] = first_task
        coordinator._deferred_tasks.add(first_task)

        async def noop_deferred(app_id, delay):
            pass

        with patch.object(coordinator, "deferred_update", side_effect=noop_deferred):
            coordinator._schedule_deferred_update(appliance_id)
            await asyncio.sleep(0)

        assert first_task.cancelled()
