"""Tests for ElectroluxCoordinator methods - increasing coordinator coverage."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.electrolux.coordinator import (
    APPLIANCE_ID_ALT_KEY,
    APPLIANCE_ID_KEY,
    DEFERRED_TASK_LIMIT,
    PROPERTY_KEY,
    VALUE_KEY,
    ElectroluxCoordinator,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_hass():
    """Return a minimal Home Assistant mock."""
    mock_loop = MagicMock()
    mock_loop.time.return_value = 1_000_000.0
    hass = MagicMock()
    hass.loop = mock_loop
    return hass


@pytest.fixture
def mock_api():
    """Return a minimal API client mock."""
    client = MagicMock()
    client._auth_failed = False
    return client


@pytest.fixture
def coordinator(mock_hass, mock_api):
    """Return a coordinator with mocked dependencies (no HA setup required)."""
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
        coord.config_entry = None
        coord.last_update_success = True
        return coord


def _make_appliance(app_id: str = "app1", connectivity: str = "connected") -> MagicMock:
    """Create a mock Appliance with commonly needed attributes."""
    ap = MagicMock()
    ap.pnc_id = app_id
    ap.reported_state = {}
    ap.state = {"connectivityState": connectivity}
    return ap


def _make_appliances(appliance_map: dict) -> MagicMock:
    """Create a mock Appliances collection."""
    aps = MagicMock()
    aps.appliances = appliance_map
    aps.get_appliances.return_value = appliance_map
    aps.get_appliance_ids.return_value = list(appliance_map.keys())

    def get_appliance(aid):
        return appliance_map.get(aid)

    aps.get_appliance.side_effect = get_appliance
    return aps


# ===========================================================================
# _is_incremental_update
# ===========================================================================


class TestIsIncrementalUpdate:
    def test_returns_true_for_valid_incremental_data(self, coordinator):
        data = {APPLIANCE_ID_KEY: "id1", PROPERTY_KEY: "temp", VALUE_KEY: 22}
        assert coordinator._is_incremental_update(data) is True

    def test_returns_false_for_empty_dict(self, coordinator):
        assert coordinator._is_incremental_update({}) is False

    def test_returns_false_missing_property_key(self, coordinator):
        data = {APPLIANCE_ID_KEY: "id1", VALUE_KEY: 22}
        assert coordinator._is_incremental_update(data) is False

    def test_returns_false_missing_value_key(self, coordinator):
        data = {APPLIANCE_ID_KEY: "id1", PROPERTY_KEY: "temp"}
        assert coordinator._is_incremental_update(data) is False

    def test_returns_false_missing_appliance_id(self, coordinator):
        data = {PROPERTY_KEY: "temp", VALUE_KEY: 22}
        assert coordinator._is_incremental_update(data) is False

    def test_returns_false_for_bulk_data(self, coordinator):
        # Bulk data does not have all three required keys
        data = {APPLIANCE_ID_KEY: "id1", "data": {"temp": 22}}
        assert coordinator._is_incremental_update(data) is False


# ===========================================================================
# _should_defer_update
# ===========================================================================


class TestShouldDeferUpdate:
    def test_returns_true_when_time_entity_at_threshold(self, coordinator):
        from custom_components.electrolux.const import TIME_ENTITIES_TO_UPDATE

        if not TIME_ENTITIES_TO_UPDATE:
            pytest.skip("No TIME_ENTITIES_TO_UPDATE defined")
        key = next(iter(TIME_ENTITIES_TO_UPDATE))
        assert coordinator._should_defer_update({key: 1}) is True

    def test_returns_false_when_time_entity_zero(self, coordinator):
        from custom_components.electrolux.const import TIME_ENTITIES_TO_UPDATE

        if not TIME_ENTITIES_TO_UPDATE:
            pytest.skip("No TIME_ENTITIES_TO_UPDATE defined")
        key = next(iter(TIME_ENTITIES_TO_UPDATE))
        # 0 is NOT in (0, 1], so should be False
        assert coordinator._should_defer_update({key: 0}) is False

    def test_returns_false_when_value_above_threshold(self, coordinator):
        from custom_components.electrolux.const import TIME_ENTITIES_TO_UPDATE

        if not TIME_ENTITIES_TO_UPDATE:
            pytest.skip("No TIME_ENTITIES_TO_UPDATE defined")
        key = next(iter(TIME_ENTITIES_TO_UPDATE))
        assert coordinator._should_defer_update({key: 100}) is False

    def test_returns_false_for_non_time_entity(self, coordinator):
        assert coordinator._should_defer_update({"randomProperty": 1}) is False

    def test_returns_false_for_none_value(self, coordinator):
        from custom_components.electrolux.const import TIME_ENTITIES_TO_UPDATE

        if not TIME_ENTITIES_TO_UPDATE:
            pytest.skip("No TIME_ENTITIES_TO_UPDATE defined")
        key = next(iter(TIME_ENTITIES_TO_UPDATE))
        assert coordinator._should_defer_update({key: None}) is False

    def test_returns_false_for_empty_dict(self, coordinator):
        assert coordinator._should_defer_update({}) is False


# ===========================================================================
# _can_restart_sse
# ===========================================================================


class TestCanRestartSse:
    def test_returns_true_when_no_previous_restart(self, coordinator):
        coordinator._last_sse_restart_time = 0.0
        coordinator.hass.loop.time.return_value = 1000.0
        assert coordinator._can_restart_sse() is True

    def test_updates_last_restart_time(self, coordinator):
        coordinator._last_sse_restart_time = 0.0
        coordinator.hass.loop.time.return_value = 5000.0
        coordinator._can_restart_sse()
        assert coordinator._last_sse_restart_time == 5000.0

    def test_returns_false_within_cooldown(self, coordinator):
        coordinator.hass.loop.time.return_value = 1000.0
        coordinator._last_sse_restart_time = 500.0  # 500s ago < 900s cooldown
        assert coordinator._can_restart_sse() is False

    def test_returns_true_after_cooldown(self, coordinator):
        coordinator.hass.loop.time.return_value = 2000.0
        coordinator._last_sse_restart_time = 0.0  # > 900s ago
        assert coordinator._can_restart_sse() is True


# ===========================================================================
# get_health_status
# ===========================================================================


class TestGetHealthStatus:
    def test_returns_dict_with_expected_keys(self, coordinator):
        coordinator.data = {"appliances": MagicMock(spec=dict)}
        coordinator.data["appliances"].__len__ = lambda self: 0
        result = coordinator.get_health_status()
        assert "websocket_connected" in result
        assert "appliances_count" in result
        assert "last_update_success" in result

    def test_websocket_connected_false_when_no_listen_task(self, coordinator):
        coordinator.listen_task = None
        result = coordinator.get_health_status()
        assert result["websocket_connected"] is False

    def test_websocket_connected_false_when_task_done(self, coordinator):
        task = MagicMock()
        task.done.return_value = True
        coordinator.listen_task = task
        result = coordinator.get_health_status()
        assert result["websocket_connected"] is False

    def test_websocket_connected_true_when_task_running(self, coordinator):
        task = MagicMock()
        task.done.return_value = False
        coordinator.listen_task = task
        result = coordinator.get_health_status()
        assert result["websocket_connected"] is True

    def test_appliances_count_zero_when_data_none(self, coordinator):
        coordinator.data = None
        result = coordinator.get_health_status()
        assert result["appliances_count"] == 0

    def test_last_update_success_reflects_coordinator_state(self, coordinator):
        coordinator.last_update_success = False
        result = coordinator.get_health_status()
        assert result["last_update_success"] is False


# ===========================================================================
# incoming_data
# ===========================================================================


class TestIncomingData:
    def test_does_nothing_when_data_is_none(self, coordinator):
        coordinator.data = None
        # Should not raise
        coordinator.incoming_data({"applianceId": "id1", "property": "p", "value": 1})

    def test_does_nothing_when_no_appliances_cache(self, coordinator):
        coordinator.data = {"appliances": MagicMock()}
        coordinator._appliances_cache = None
        # Should not raise
        coordinator.incoming_data({"applianceId": "id1", "property": "p", "value": 1})

    def test_routes_incremental_update(self, coordinator):
        ap = _make_appliance("app1")
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        coordinator._appliances_cache = aps
        data = {APPLIANCE_ID_KEY: "app1", PROPERTY_KEY: "opMode", VALUE_KEY: "auto"}
        with patch.object(coordinator, "_process_incremental_update") as mock_inc:
            coordinator.incoming_data(data)
            mock_inc.assert_called_once_with(data, aps)

    def test_routes_bulk_update(self, coordinator):
        ap = _make_appliance("app1")
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        coordinator._appliances_cache = aps
        data = {APPLIANCE_ID_KEY: "app1", "state": {"opMode": "auto"}}
        with patch.object(coordinator, "_process_bulk_update") as mock_bulk:
            coordinator.incoming_data(data)
            mock_bulk.assert_called_once_with(data, aps)


# ===========================================================================
# _check_deferred_update
# ===========================================================================


class TestCheckDeferredUpdate:
    def test_calls_schedule_when_threshold_met(self, coordinator):
        from custom_components.electrolux.const import TIME_ENTITIES_TO_UPDATE

        if not TIME_ENTITIES_TO_UPDATE:
            pytest.skip("No TIME_ENTITIES_TO_UPDATE defined")
        key = next(iter(TIME_ENTITIES_TO_UPDATE))
        with patch.object(coordinator, "_schedule_deferred_update") as mock_sched:
            coordinator._check_deferred_update(
                {PROPERTY_KEY: key, VALUE_KEY: 1}, "app1"
            )
            mock_sched.assert_called_once_with("app1")

    def test_does_not_call_schedule_when_threshold_not_met(self, coordinator):
        from custom_components.electrolux.const import TIME_ENTITIES_TO_UPDATE

        if not TIME_ENTITIES_TO_UPDATE:
            pytest.skip("No TIME_ENTITIES_TO_UPDATE defined")
        key = next(iter(TIME_ENTITIES_TO_UPDATE))
        with patch.object(coordinator, "_schedule_deferred_update") as mock_sched:
            coordinator._check_deferred_update(
                {PROPERTY_KEY: key, VALUE_KEY: 999}, "app1"
            )
            mock_sched.assert_not_called()


# ===========================================================================
# _schedule_deferred_update
# ===========================================================================


class TestScheduleDeferredUpdate:
    def test_creates_deferred_task(self, coordinator):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        coordinator.hass.async_create_task = MagicMock(return_value=mock_task)

        coordinator._schedule_deferred_update("app1")

        assert "app1" in coordinator._deferred_tasks_by_appliance
        assert mock_task in coordinator._deferred_tasks

    def test_cancels_existing_task_for_same_appliance(self, coordinator):
        old_task = MagicMock()
        old_task.done.return_value = False
        coordinator._deferred_tasks_by_appliance["app1"] = old_task

        new_task = MagicMock()
        new_task.done.return_value = False
        coordinator.hass.async_create_task = MagicMock(return_value=new_task)

        coordinator._schedule_deferred_update("app1")

        old_task.cancel.assert_called_once()
        assert coordinator._deferred_tasks_by_appliance["app1"] == new_task

    def test_skips_if_task_limit_reached(self, coordinator):
        # Fill up the deferred task set to limit
        for i in range(DEFERRED_TASK_LIMIT):
            t = MagicMock()
            t.done.return_value = False
            coordinator._deferred_tasks.add(t)

        coordinator.hass.async_create_task = MagicMock()
        coordinator._schedule_deferred_update("app99")

        coordinator.hass.async_create_task.assert_not_called()

    def test_cleanup_callback_removes_task(self, coordinator):
        """Test that the done callback removes the task from tracking."""
        captured_callbacks = []

        def capture_add_done_callback(cb):
            captured_callbacks.append(cb)

        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.add_done_callback.side_effect = capture_add_done_callback
        coordinator.hass.async_create_task = MagicMock(return_value=mock_task)

        coordinator._schedule_deferred_update("app1")
        # Simulate task completion callback
        assert len(captured_callbacks) == 1
        captured_callbacks[0](mock_task)
        # Task should be removed from by_appliance map
        assert "app1" not in coordinator._deferred_tasks_by_appliance


# ===========================================================================
# _process_bulk_update
# ===========================================================================


class TestProcessBulkUpdate:
    def test_updates_appliance_and_notifies(self, coordinator):
        ap = _make_appliance("app1")
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        data = {APPLIANCE_ID_KEY: "app1", "data": {"opMode": "auto"}}
        # Mark as changed
        ap.reported_state = {"opMode": "manual"}

        coordinator._process_bulk_update(data, aps)

        ap.update_reported_data.assert_called_once_with({"opMode": "auto"})
        coordinator.async_set_updated_data.assert_called_once()

    def test_skips_when_no_appliance_id(self, coordinator):
        aps = _make_appliances({})
        coordinator.async_set_updated_data = MagicMock()

        coordinator._process_bulk_update({"someOtherKey": "val"}, aps)

        coordinator.async_set_updated_data.assert_not_called()

    def test_skips_unknown_appliance(self, coordinator):
        aps = _make_appliances({})
        coordinator.async_set_updated_data = MagicMock()

        data = {APPLIANCE_ID_KEY: "unknown_id", "data": {"opMode": "auto"}}
        coordinator._process_bulk_update(data, aps)

        coordinator.async_set_updated_data.assert_not_called()

    def test_skips_duplicate_unchanged_data(self, coordinator):
        ap = _make_appliance("app1")
        ap.reported_state = {"opMode": "auto"}  # same as incoming
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        data = {APPLIANCE_ID_KEY: "app1", "data": {"opMode": "auto"}}
        coordinator._process_bulk_update(data, aps)

        ap.update_reported_data.assert_not_called()
        coordinator.async_set_updated_data.assert_not_called()

    def test_marks_appliance_connected_on_update(self, coordinator):
        ap = _make_appliance("app1")
        ap.reported_state = {}
        ap.state = {"connectivityState": "disconnected"}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        data = {APPLIANCE_ID_KEY: "app1", "data": {"opMode": "auto"}}
        coordinator._process_bulk_update(data, aps)

        assert ap.state["connectivityState"] == "connected"

    def test_handles_update_reported_data_exception(self, coordinator):
        ap = _make_appliance("app1")
        ap.reported_state = {"opMode": "manual"}
        ap.update_reported_data.side_effect = ValueError("bad value")
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        data = {APPLIANCE_ID_KEY: "app1", "data": {"opMode": "auto"}}
        # Should not raise
        coordinator._process_bulk_update(data, aps)
        coordinator.async_set_updated_data.assert_not_called()

    def test_uses_alt_appliance_id_key(self, coordinator):
        ap = _make_appliance("app1")
        ap.reported_state = {}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        data = {APPLIANCE_ID_ALT_KEY: "app1", "data": {"opMode": "auto"}}
        coordinator._process_bulk_update(data, aps)

        ap.update_reported_data.assert_called_once()


# ===========================================================================
# _process_incremental_update
# ===========================================================================


class TestProcessIncrementalUpdate:
    def _make_data(self, app_id="app1", prop="opMode", value="auto"):
        return {APPLIANCE_ID_KEY: app_id, PROPERTY_KEY: prop, VALUE_KEY: value}

    def test_updates_appliance_on_changed_value(self, coordinator):
        ap = _make_appliance("app1")
        ap.reported_state = {"opMode": "manual"}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        coordinator._process_incremental_update(
            self._make_data("app1", "opMode", "auto"), aps
        )

        ap.update_reported_data.assert_called_once_with({"opMode": "auto"})
        coordinator.async_set_updated_data.assert_called_once()

    def test_skips_duplicate_value(self, coordinator):
        ap = _make_appliance("app1")
        ap.reported_state = {"opMode": "auto"}  # same as incoming
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        coordinator._process_incremental_update(
            self._make_data("app1", "opMode", "auto"), aps
        )

        ap.update_reported_data.assert_not_called()

    def test_ignores_unknown_appliance(self, coordinator):
        aps = _make_appliances({})
        coordinator.async_set_updated_data = MagicMock()

        coordinator._process_incremental_update(
            self._make_data("unknown", "opMode", "auto"), aps
        )

        coordinator.async_set_updated_data.assert_not_called()

    def test_handles_update_reported_data_exception(self, coordinator):
        ap = _make_appliance("app1")
        ap.reported_state = {"opMode": "manual"}
        ap.update_reported_data.side_effect = KeyError("key")
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        coordinator._process_incremental_update(
            self._make_data("app1", "opMode", "auto"), aps
        )

        coordinator.async_set_updated_data.assert_not_called()

    def test_schedules_appliance_state_refresh_on_applianceState(self, coordinator):
        ap = _make_appliance("app1")
        ap.reported_state = {"applianceState": "running"}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()
        coordinator.hass.async_create_task = MagicMock()

        data = {
            APPLIANCE_ID_KEY: "app1",
            PROPERTY_KEY: "applianceState",
            VALUE_KEY: "standby",
        }
        coordinator._process_incremental_update(data, aps)

        coordinator.hass.async_create_task.assert_called()

    def test_marks_appliance_connected_on_non_disconnect(self, coordinator):
        ap = _make_appliance("app1")
        ap.reported_state = {"opMode": "manual"}
        ap.state = {"connectivityState": "disconnected"}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        coordinator._process_incremental_update(
            self._make_data("app1", "opMode", "auto"), aps
        )

        assert ap.state["connectivityState"] == "connected"

    def test_does_not_mark_connected_on_disconnect_event(self, coordinator):
        ap = _make_appliance("app1", connectivity="unknown")
        ap.reported_state = {"connectivityState": "connected"}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        data = {
            APPLIANCE_ID_KEY: "app1",
            PROPERTY_KEY: "connectivityState",
            VALUE_KEY: "disconnected",
        }
        coordinator._process_incremental_update(data, aps)

        # Disconnect event: the state should NOT be overwritten to "connected"
        assert ap.state.get("connectivityState") == "unknown"


# ===========================================================================
# _cleanup_appliance_tasks
# ===========================================================================


class TestCleanupApplianceTasks:
    @pytest.mark.asyncio
    async def test_cancels_pending_tasks(self, coordinator):
        task = MagicMock(spec=asyncio.Task)
        task.done.return_value = False

        with patch("asyncio.gather", new=AsyncMock(return_value=[])):
            with patch("asyncio.shield", new=AsyncMock(return_value=[])):
                await coordinator._cleanup_appliance_tasks([task], "app1")

        task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_already_done_tasks(self, coordinator):
        task = MagicMock(spec=asyncio.Task)
        task.done.return_value = True

        with patch("asyncio.gather", new=AsyncMock(return_value=[])):
            with patch("asyncio.shield", new=AsyncMock(return_value=[])):
                await coordinator._cleanup_appliance_tasks([task], "app1")

        task.cancel.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_empty_task_list(self, coordinator):
        # Should complete without error
        await coordinator._cleanup_appliance_tasks([], "app1")

    @pytest.mark.asyncio
    async def test_handles_shield_cancelled_error(self, coordinator):
        task = MagicMock(spec=asyncio.Task)
        task.done.return_value = False

        with patch("asyncio.shield", side_effect=asyncio.CancelledError):
            with patch("asyncio.gather", new=AsyncMock(return_value=[])):
                # Should not propagate the error
                await coordinator._cleanup_appliance_tasks([task], "app1")


# ===========================================================================
# deferred_update
# ===========================================================================


class TestDeferredUpdate:
    @pytest.mark.asyncio
    async def test_success_updates_appliance(self, coordinator):
        ap = _make_appliance("app1")
        ap.state = {"timeToEnd": 60}
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        status = {"timeToEnd": 0, "opMode": "idle"}
        coordinator.api.get_appliance_state = AsyncMock(return_value=status)
        coordinator.async_set_updated_data = MagicMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            await coordinator.deferred_update("app1", 1)

        ap.update.assert_called_once_with(status)
        coordinator.async_set_updated_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_nothing_when_data_is_none(self, coordinator):
        coordinator.data = None
        coordinator.api.get_appliance_state = AsyncMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            await coordinator.deferred_update("app1", 1)

        coordinator.api.get_appliance_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_nothing_when_appliances_empty(self, coordinator):
        aps = MagicMock()
        aps.get_appliance.return_value = None
        coordinator.data = {"appliances": None}
        coordinator.api.get_appliance_state = AsyncMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            await coordinator.deferred_update("app1", 1)

        coordinator.api.get_appliance_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_update_failed_on_connection_error(self, coordinator):
        from homeassistant.helpers.update_coordinator import UpdateFailed

        ap = _make_appliance("app1")
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=ConnectionError("network error")
        )

        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(UpdateFailed, match="Network error"):
                await coordinator.deferred_update("app1", 1)

    @pytest.mark.asyncio
    async def test_raises_cancelled_error_unchanged(self, coordinator):
        ap = _make_appliance("app1")
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=asyncio.CancelledError()
        )

        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(asyncio.CancelledError):
                await coordinator.deferred_update("app1", 1)

    @pytest.mark.asyncio
    async def test_raises_update_failed_on_value_error(self, coordinator):
        from homeassistant.helpers.update_coordinator import UpdateFailed

        ap = _make_appliance("app1")
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=ValueError("invalid data")
        )

        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(UpdateFailed, match="Invalid data"):
                await coordinator.deferred_update("app1", 1)


# ===========================================================================
# _refresh_after_appliance_state_change
# ===========================================================================


class TestRefreshAfterApplianceStateChange:
    @pytest.mark.asyncio
    async def test_updates_appliance_state(self, coordinator):
        ap = _make_appliance("app1")
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        status = {"opMode": "idle"}
        coordinator.api.get_appliance_state = AsyncMock(return_value=status)
        coordinator.async_set_updated_data = MagicMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            await coordinator._refresh_after_appliance_state_change("app1")

        ap.update.assert_called_once_with(status)
        coordinator.async_set_updated_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_early_when_data_is_none(self, coordinator):
        coordinator.data = None
        coordinator.api.get_appliance_state = AsyncMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            await coordinator._refresh_after_appliance_state_change("app1")

        coordinator.api.get_appliance_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_early_when_appliance_not_found(self, coordinator):
        aps = _make_appliances({})
        coordinator.data = {"appliances": aps}
        coordinator.api.get_appliance_state = AsyncMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            await coordinator._refresh_after_appliance_state_change("missing")

        coordinator.api.get_appliance_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(self, coordinator):
        ap = _make_appliance("app1")
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=Exception("API error")
        )
        coordinator.async_set_updated_data = MagicMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            # Should not raise
            await coordinator._refresh_after_appliance_state_change("app1")

        coordinator.async_set_updated_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancelled_error_propagated(self, coordinator):
        ap = _make_appliance("app1")
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=asyncio.CancelledError()
        )

        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(asyncio.CancelledError):
                await coordinator._refresh_after_appliance_state_change("app1")


# ===========================================================================
# _refresh_all_appliances
# ===========================================================================


class TestRefreshAllAppliances:
    @pytest.mark.asyncio
    async def test_updates_all_appliances(self, coordinator):
        ap1 = _make_appliance("app1")
        ap2 = _make_appliance("app2")
        aps = _make_appliances({"app1": ap1, "app2": ap2})
        coordinator.data = {"appliances": aps}
        status = {"connectivityState": "connected"}
        coordinator.api.get_appliance_state = AsyncMock(return_value=status)
        coordinator.async_set_updated_data = MagicMock()

        await coordinator._refresh_all_appliances()

        assert ap1.update.call_count == 1
        assert ap2.update.call_count == 1
        coordinator.async_set_updated_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_early_when_data_none(self, coordinator):
        coordinator.data = None
        coordinator.api.get_appliance_state = AsyncMock()

        await coordinator._refresh_all_appliances()

        coordinator.api.get_appliance_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_partial_failures(self, coordinator):
        ap1 = _make_appliance("app1")
        ap2 = _make_appliance("app2")
        aps = _make_appliances({"app1": ap1, "app2": ap2})
        coordinator.data = {"appliances": aps}
        coordinator.async_set_updated_data = MagicMock()

        call_count = 0

        async def mock_get_state(app_id):
            nonlocal call_count
            call_count += 1
            if app_id == "app1":
                raise Exception("app1 error")
            return {"connectivityState": "connected"}

        coordinator.api.get_appliance_state = mock_get_state

        # Should not raise even with partial failures
        await coordinator._refresh_all_appliances()

        # app2 should succeed
        ap2.update.assert_called_once()
        coordinator.async_set_updated_data.assert_called_once()


# ===========================================================================
# cleanup_removed_appliances
# ===========================================================================


class TestCleanupRemovedAppliances:
    @pytest.mark.asyncio
    async def test_returns_early_when_api_returns_empty(self, coordinator):
        coordinator.api.get_appliances_list = AsyncMock(return_value=[])
        coordinator.data = {"appliances": MagicMock(appliances={"app1": MagicMock()})}

        await coordinator.cleanup_removed_appliances()
        # No attempts to remove anything
        assert "app1" in coordinator.data["appliances"].appliances

    @pytest.mark.asyncio
    async def test_returns_early_when_api_returns_none(self, coordinator):
        coordinator.api.get_appliances_list = AsyncMock(return_value=None)

        await coordinator.cleanup_removed_appliances()  # Should not raise

    @pytest.mark.asyncio
    async def test_removes_truly_deleted_appliance(self, coordinator):
        ap = MagicMock()
        ap.state = {"connectivityState": "connected"}
        tracked = {
            "app1": ap,
            "app2": MagicMock(state={"connectivityState": "connected"}),
        }
        aps = MagicMock()
        aps.appliances = tracked
        coordinator.data = {"appliances": aps}
        coordinator.async_set_updated_data = MagicMock()
        coordinator.api.get_appliances_list = AsyncMock(
            return_value=[{"applianceId": "app1"}]  # only app1 in API
        )

        await coordinator.cleanup_removed_appliances()

        # app2 should be removed (connected but not in API → truly removed)
        assert "app2" not in tracked

    @pytest.mark.asyncio
    async def test_keeps_disconnected_appliances(self, coordinator):
        ap = MagicMock()
        ap.state = {"connectivityState": "disconnected"}
        tracked = {"app1": ap}
        aps = MagicMock()
        aps.appliances = tracked
        coordinator.data = {"appliances": aps}
        coordinator.async_set_updated_data = MagicMock()
        coordinator.api.get_appliances_list = AsyncMock(
            return_value=[{"applianceId": "other_id"}]  # app1 not in API
        )

        await coordinator.cleanup_removed_appliances()

        # Disconnected appliance should NOT be removed
        assert "app1" in tracked

    @pytest.mark.asyncio
    async def test_handles_api_exception_gracefully(self, coordinator):
        coordinator.api.get_appliances_list = AsyncMock(
            side_effect=Exception("API failure")
        )
        # Should not raise
        await coordinator.cleanup_removed_appliances()


# ===========================================================================
# perform_manual_sync
# ===========================================================================


class TestPerformManualSync:
    @pytest.mark.asyncio
    async def test_succeeds_with_capabilities(self, coordinator):
        coordinator.data = {"app1": {"capabilities": {"opMode": {}}}}
        coordinator.hass.loop.time.return_value = 1_000_000.0
        coordinator._last_manual_sync_time = 0.0
        coordinator.api.disconnect_websocket = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        coordinator.listen_websocket = AsyncMock()

        await coordinator.perform_manual_sync("app1", "Test Appliance")

        coordinator.api.disconnect_websocket.assert_called_once()
        coordinator.async_request_refresh.assert_called_once()
        coordinator.listen_websocket.assert_called()

    @pytest.mark.asyncio
    async def test_rejects_sync_within_cooldown(self, coordinator):
        from homeassistant.exceptions import HomeAssistantError

        coordinator.data = {"app1": {"capabilities": {"opMode": {}}}}
        coordinator.hass.loop.time.return_value = 1_000_000.0
        coordinator._last_manual_sync_time = 999_999.0  # 1 second ago → within cooldown

        with pytest.raises(HomeAssistantError, match="rate limited"):
            await coordinator.perform_manual_sync("app1", "Test Appliance")

    @pytest.mark.asyncio
    async def test_triggers_reload_when_no_capabilities(self, coordinator):
        coordinator.data = {"app1": {}}  # no capabilities
        config_entry = MagicMock()
        config_entry.entry_id = "entry1"
        coordinator.config_entry = config_entry
        coordinator.hass.config_entries.async_reload = AsyncMock()

        await coordinator.perform_manual_sync("app1", "Test Appliance")

        coordinator.hass.config_entries.async_reload.assert_called_once_with("entry1")

    @pytest.mark.asyncio
    async def test_raises_ha_error_when_no_config_entry_and_no_capabilities(
        self, coordinator
    ):
        from homeassistant.exceptions import HomeAssistantError

        coordinator.data = {"app1": {}}  # no capabilities
        coordinator.config_entry = None

        with pytest.raises(HomeAssistantError, match="Config entry is not available"):
            await coordinator.perform_manual_sync("app1", "Test Appliance")

    @pytest.mark.asyncio
    async def test_raises_ha_error_on_timeout(self, coordinator):
        from homeassistant.exceptions import HomeAssistantError

        coordinator.data = {"app1": {"capabilities": {"opMode": {}}}}
        coordinator.hass.loop.time.return_value = 1_000_000.0
        coordinator._last_manual_sync_time = 0.0
        coordinator.api.disconnect_websocket = AsyncMock(
            side_effect=asyncio.TimeoutError
        )
        coordinator.listen_websocket = AsyncMock()

        with pytest.raises(HomeAssistantError, match="timed out"):
            await coordinator.perform_manual_sync("app1", "Test Appliance")


# ===========================================================================
# setup_token_refresh_callback - additional edge cases
# ===========================================================================


class TestSetupTokenRefreshCallback:
    def test_returns_early_without_config_entry(self, coordinator):
        coordinator.config_entry = None
        # Should not raise, just return early
        coordinator.setup_token_refresh_callback()
        # API callback not set since we returned early
        coordinator.api.set_token_update_callback_with_expiry.assert_not_called()

    def test_registers_callback_with_config_entry(self, coordinator):
        config_entry = MagicMock()
        config_entry.entry_id = "test_id"
        config_entry.title = "Test"
        config_entry.data = {}
        coordinator.config_entry = config_entry

        coordinator.setup_token_refresh_callback()

        coordinator.api.set_token_update_callback_with_expiry.assert_called_once()

    def test_on_token_update_handles_exception(self, coordinator):
        """Test that on_token_update exception handler is triggered gracefully."""
        config_entry = MagicMock()
        config_entry.entry_id = "test_id"
        config_entry.title = "Test"
        config_entry.data = {}
        coordinator.config_entry = config_entry
        coordinator.hass.config_entries.async_update_entry.side_effect = RuntimeError(
            "Persist fail"
        )

        coordinator.setup_token_refresh_callback()

        # Get the registered callback
        captured_callback = (
            coordinator.api.set_token_update_callback_with_expiry.call_args[0][0]
        )

        import time as time_module

        future_time = int(time_module.time()) + 3600

        # Call the callback - should not raise even though async_update_entry throws
        captured_callback(
            "access_tok_123456789",
            "refresh_tok_12345678",
            "api_key_12345678",
            future_time,
        )

        # The exception was caught internally - the function should have called async_update_entry
        coordinator.hass.config_entries.async_update_entry.assert_called_once()

    def test_on_token_update_success(self, coordinator):
        """Test successful token update callback."""
        config_entry = MagicMock()
        config_entry.entry_id = "test_id"
        config_entry.title = "Test"
        config_entry.data = {"some_existing_key": "val"}
        coordinator.config_entry = config_entry

        coordinator.setup_token_refresh_callback()
        captured_callback = (
            coordinator.api.set_token_update_callback_with_expiry.call_args[0][0]
        )

        import time as time_module

        future_time = int(time_module.time()) + 3600

        captured_callback(
            "new_access_123456789",
            "new_refresh_12345678",
            "new_api_key_12345",
            future_time,
        )

        coordinator.hass.config_entries.async_update_entry.assert_called_once()


# ===========================================================================
# deferred_update - additional branches
# ===========================================================================


class TestDeferredUpdateAdditional:
    @pytest.mark.asyncio
    async def test_appliance_not_found_in_collection(self, coordinator):
        """Test deferred_update when appliance ID is not in appliances collection."""
        aps = _make_appliances({})  # empty – get_appliance returns None
        coordinator.data = {"appliances": aps}
        coordinator.api.get_appliance_state = AsyncMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            # Should return early without calling API
            await coordinator.deferred_update("missing_app", 1)

        coordinator.api.get_appliance_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_update_failed_on_unexpected_exception(self, coordinator):
        """Test deferred_update catch-all for RuntimeError."""
        from homeassistant.helpers.update_coordinator import UpdateFailed

        ap = _make_appliance("app1")
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        coordinator.api.get_appliance_state = AsyncMock(
            side_effect=RuntimeError("unexpected problem")
        )

        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(UpdateFailed, match="Unexpected error"):
                await coordinator.deferred_update("app1", 1)

    @pytest.mark.asyncio
    async def test_same_time_to_end_logs_no_change(self, coordinator):
        """Test the 'no change' debug branch when timeToEnd stays the same."""
        ap = _make_appliance("app1")
        ap.state = {"timeToEnd": 0}
        aps = _make_appliances({"app1": ap})
        coordinator.data = {"appliances": aps}
        # Return same timeToEnd value → no change branch
        status = {"timeToEnd": 0}
        coordinator.api.get_appliance_state = AsyncMock(return_value=status)
        coordinator.async_set_updated_data = MagicMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            await coordinator.deferred_update("app1", 1)

        ap.update.assert_called_once_with(status)


# ===========================================================================
# _refresh_after_appliance_state_change - empty appliances branch
# ===========================================================================


class TestRefreshAfterStateChangeAdditional:
    @pytest.mark.asyncio
    async def test_returns_early_when_appliances_falsy(self, coordinator):
        coordinator.data = {"appliances": None}
        coordinator.api.get_appliance_state = AsyncMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            await coordinator._refresh_after_appliance_state_change("app1")

        coordinator.api.get_appliance_state.assert_not_called()


# ===========================================================================
# _process_incremental_update - timeToEnd tracking branches
# ===========================================================================


class TestProcessIncrementalUpdateTimeToEnd:
    def _incremental_data(self, app_id, prop, value):
        return {APPLIANCE_ID_KEY: app_id, PROPERTY_KEY: prop, VALUE_KEY: value}

    def test_time_to_end_skip_detected(self, coordinator):
        """When old_value > 1 and new_value == 0 → skip detection log branch."""

        # timeToEnd is the key we need
        ap = _make_appliance("app1")
        ap.reported_state = {"timeToEnd": 60}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()
        coordinator._last_time_to_end["app1"] = 60  # old value > 1

        data = self._incremental_data("app1", "timeToEnd", 0)
        coordinator._process_incremental_update(data, aps)
        # Verify last_time_to_end was updated
        assert coordinator._last_time_to_end["app1"] == 0

    def test_time_to_end_normal_completion(self, coordinator):
        """When old_value <= 1 and new_value == 0 → normal completion log branch."""
        ap = _make_appliance("app1")
        ap.reported_state = {"timeToEnd": 1}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()
        coordinator._last_time_to_end["app1"] = 1  # old value at threshold

        data = self._incremental_data("app1", "timeToEnd", 0)
        coordinator._process_incremental_update(data, aps)
        assert coordinator._last_time_to_end["app1"] == 0

    def test_time_to_end_tracking_without_prior_value(self, coordinator):
        """When no prior timeToEnd value → just tracks without skip detection."""
        ap = _make_appliance("app1")
        ap.reported_state = {"timeToEnd": 5}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()
        # No prior value in _last_time_to_end

        data = self._incremental_data("app1", "timeToEnd", 3)
        coordinator._process_incremental_update(data, aps)
        assert coordinator._last_time_to_end["app1"] == 3

    def test_duplicate_value_updates_last_seen_time(self, coordinator):
        """Duplicate incremental value still updates _last_update_times."""
        ap = _make_appliance("app1")
        ap.reported_state = {"opMode": "auto"}  # same as incoming
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()
        coordinator.hass.loop.time.return_value = 99999.0

        data = self._incremental_data("app1", "opMode", "auto")
        coordinator._process_incremental_update(data, aps)

        # Even for duplicates, last_update_times should be updated
        assert coordinator._last_update_times.get("app1") == 99999.0
        coordinator.async_set_updated_data.assert_not_called()  # no update needed

    def test_marks_back_online_when_was_disconnected(self, coordinator):
        """When appliance state was 'disconnected', getting new data marks it connected."""
        ap = _make_appliance("app1", connectivity="disconnected")
        ap.reported_state = {"opMode": "manual"}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        data = self._incremental_data("app1", "opMode", "auto")
        coordinator._process_incremental_update(data, aps)

        assert ap.state["connectivityState"] == "connected"


# ===========================================================================
# _cleanup_appliance_tasks - Exception handler branch
# ===========================================================================


class TestCleanupApplianceTasksException:
    @pytest.mark.asyncio
    async def test_handles_generic_exception_from_shield(self, coordinator):
        task = MagicMock(spec=asyncio.Task)
        task.done.return_value = False

        with patch("asyncio.shield", side_effect=RuntimeError("unexpected")):
            with patch("asyncio.gather", new=AsyncMock(return_value=[])):
                # Should not raise
                await coordinator._cleanup_appliance_tasks([task], "app1")


# ===========================================================================
# _process_bulk_update - deferred update trigger branch
# ===========================================================================


class TestProcessBulkUpdateDeferred:
    def test_schedules_deferred_update_when_threshold_met(self, coordinator):
        from custom_components.electrolux.const import TIME_ENTITIES_TO_UPDATE

        if not TIME_ENTITIES_TO_UPDATE:
            pytest.skip("No TIME_ENTITIES_TO_UPDATE defined")

        # Use a time entity key that would hit the threshold
        time_key = next(iter(TIME_ENTITIES_TO_UPDATE))
        ap = _make_appliance("app1")
        ap.reported_state = {time_key: 999}  # different from incoming → changed
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        with patch.object(coordinator, "_schedule_deferred_update") as mock_sched:
            data = {APPLIANCE_ID_KEY: "app1", "data": {time_key: 1}}  # threshold = 1
            coordinator._process_bulk_update(data, aps)
            mock_sched.assert_called_once_with("app1")

    def test_no_deferred_when_threshold_not_met(self, coordinator):
        from custom_components.electrolux.const import TIME_ENTITIES_TO_UPDATE

        if not TIME_ENTITIES_TO_UPDATE:
            pytest.skip("No TIME_ENTITIES_TO_UPDATE defined")

        time_key = next(iter(TIME_ENTITIES_TO_UPDATE))
        ap = _make_appliance("app1")
        ap.reported_state = {time_key: 999}  # old value
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        with patch.object(coordinator, "_schedule_deferred_update") as mock_sched:
            data = {
                APPLIANCE_ID_KEY: "app1",
                "data": {time_key: 100},
            }  # not in threshold
            coordinator._process_bulk_update(data, aps)
            mock_sched.assert_not_called()


# ===========================================================================
# _refresh_all_appliances - empty app_dict branch
# ===========================================================================


class TestRefreshAllAppliancesEmptyDict:
    @pytest.mark.asyncio
    async def test_returns_early_when_no_appliances_in_dict(self, coordinator):
        aps = _make_appliances({})  # empty
        coordinator.data = {"appliances": aps}
        coordinator.api.get_appliance_state = AsyncMock()

        await coordinator._refresh_all_appliances()

        coordinator.api.get_appliance_state.assert_not_called()


# ===========================================================================
# _process_incremental_update - catch-all exception handler (lines 484-488)
# ===========================================================================


class TestProcessIncrementalUpdateCatchAll:
    def test_catch_all_exception_in_update_reported_data(self, coordinator):
        """RuntimeError hits the except Exception catch-all, not KeyError/ValueError."""
        ap = _make_appliance("app1")
        ap.reported_state = {"opMode": "manual"}
        ap.update_reported_data.side_effect = RuntimeError("catch me")
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        data = {APPLIANCE_ID_KEY: "app1", PROPERTY_KEY: "opMode", VALUE_KEY: "auto"}
        coordinator._process_incremental_update(data, aps)

        coordinator.async_set_updated_data.assert_not_called()


# ===========================================================================
# _process_bulk_update - flat data path (line 622 area) + catch-all (663-667)
# ===========================================================================


class TestProcessBulkUpdateFlatData:
    def test_processes_flat_data_without_data_key(self, coordinator):
        """When payload has no 'data' or 'state' key, extracts properties directly."""
        ap = _make_appliance("app1")
        ap.reported_state = {"opMode": "manual"}
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        # Data without a dedicated "data" sub-key - flat format
        data = {APPLIANCE_ID_KEY: "app1", "opMode": "auto"}
        coordinator._process_bulk_update(data, aps)

        ap.update_reported_data.assert_called_once()
        coordinator.async_set_updated_data.assert_called_once()

    def test_catch_all_exception_in_update_reported_data(self, coordinator):
        """RuntimeError hits the except Exception catch-all in bulk update."""
        ap = _make_appliance("app1")
        ap.reported_state = {"opMode": "manual"}
        ap.update_reported_data.side_effect = RuntimeError("unexpected bulk error")
        aps = _make_appliances({"app1": ap})
        coordinator.async_set_updated_data = MagicMock()

        data = {APPLIANCE_ID_KEY: "app1", "data": {"opMode": "auto"}}
        coordinator._process_bulk_update(data, aps)

        coordinator.async_set_updated_data.assert_not_called()


# ===========================================================================
# _async_update_data - data=None and empty app_dict branches (1397-1398, 1403)
# ===========================================================================


class TestAsyncUpdateDataEdgeCases:
    @pytest.mark.asyncio
    async def test_returns_empty_when_data_is_none(self, coordinator):
        """When coordinator.data is None, returns empty appliances dict."""
        coordinator.data = None
        from custom_components.electrolux.models import Appliances

        result = await coordinator._async_update_data()

        assert "appliances" in result
        assert isinstance(result["appliances"], Appliances)

    @pytest.mark.asyncio
    async def test_returns_data_when_no_appliances(self, coordinator):
        """When app_dict is empty, returns self.data unchanged."""
        aps = MagicMock()
        aps.get_appliances.return_value = {}  # empty dict
        coordinator.data = {"appliances": aps}

        result = await coordinator._async_update_data()

        assert result is coordinator.data


# ===========================================================================
# cleanup_removed_appliances - data=None mid-cleanup (1628-1629) and
# no tracked appliances (1632)
# ===========================================================================


class TestCleanupRemovedAppliancesEdgeCases:
    @pytest.mark.asyncio
    async def test_returns_when_data_is_none_mid_cleanup(self, coordinator):
        """When data is None by the time we check tracked appliances, returns early."""
        coordinator.data = None  # data is None from start
        coordinator.api.get_appliances_list = AsyncMock(
            return_value=[{"applianceId": "app1"}]  # non-empty list
        )

        await coordinator.cleanup_removed_appliances()  # Should not raise

    @pytest.mark.asyncio
    async def test_returns_when_no_tracked_appliances_data(self, coordinator):
        """When data exists but tracked_appliances is falsy, returns early."""
        # Data with no appliances key
        coordinator.data = {}  # no "appliances" key → tracked_appliances = None
        coordinator.api.get_appliances_list = AsyncMock(
            return_value=[{"applianceId": "app1"}]
        )

        await coordinator.cleanup_removed_appliances()  # Should not raise
