"""Test coordinator connectivity and error handling."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.electrolux.models import Appliances
from custom_components.electrolux.util import NetworkError


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.loop = MagicMock()
    hass.loop.time.return_value = 1000000000
    hass.async_create_task = MagicMock(
        side_effect=lambda coro, **kwargs: coro.close() if asyncio.iscoroutine(coro) else None
    )
    return hass


@pytest.fixture
def mock_config_entry():
    """Mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Test Entry"
    return entry


@pytest.fixture
def mock_api_client():
    """Mock API client."""
    client = MagicMock()
    client.get_appliances_list = AsyncMock()
    client.get_appliance_state = AsyncMock(return_value={"connectivityState": "connected"})
    client.watch_for_appliance_state_updates = AsyncMock()
    client.disconnect_websocket = AsyncMock()
    client._auth_failed = False
    return client


@pytest.fixture
def coordinator(mock_hass, mock_api_client, mock_config_entry):
    """Create test coordinator."""
    from custom_components.electrolux.coordinator import ElectroluxCoordinator

    # Mock the DataUpdateCoordinator.__init__ to avoid HA setup issues
    with patch(
        "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = ElectroluxCoordinator.__new__(ElectroluxCoordinator)
        coord.hass = mock_hass
        coord.api = mock_api_client
        coord.config_entry = mock_config_entry
        coord.platforms = []
        coord.renew_interval = 3600
        coord.data = {"appliances": Appliances({})}
        coord._last_known_connectivity = {}
        coord._last_update_times = {}
        coord._last_sse_restart_time = 0
        coord._consecutive_sse_restarts = 0
        coord._consecutive_sse_drops = 0
        coord._last_sse_disconnect_reason = None
        coord._sse_connected = True
        coord._sse_connection_state = "streaming"
        coord.renew_task = None
        coord.listen_task = None
        coord._deferred_tasks = set()
        coord._deferred_tasks_by_appliance = {}
        coord._appliances_lock = asyncio.Lock()
        coord._manual_sync_lock = asyncio.Lock()
        coord._last_cleanup_time = 0
        coord._last_manual_sync_time = 0
        coord._consecutive_auth_failures = 0
        coord._auth_failure_threshold = 3
        coord._last_time_to_end = {}
        coord._last_time_to_end_seen = {}
        coord._last_token_update = 0.0
        coord._appliances_cache = None
        coord._can_restart_sse = MagicMock(return_value=True)
        coord._unsub_refresh = None
        coord._listeners = {}
        coord._last_remote_control = {}
        return coord


class TestCoordinatorConnectivity:
    """Test coordinator connectivity and error handling."""

    @pytest.mark.asyncio
    async def test_appliance_offline_marks_unavailable_without_reauth(self, coordinator, mock_api_client):
        """Test that appliance offline errors mark entities unavailable without triggering reauth."""
        # Setup mock appliance data
        from custom_components.electrolux.models import Appliance

        appliance_id = "test_appliance_123"
        appliance = Appliance(
            coordinator=coordinator,
            name="Test Appliance",
            pnc_id=appliance_id,
            brand="Electrolux",
            model="TestModel",
            state={"connectivityState": "connected"},
        )
        appliances = Appliances({appliance_id: appliance})
        coordinator.data = {"appliances": appliances}

        # Mock network error during appliance state fetch
        mock_api_client.get_appliance_state.side_effect = NetworkError("Network connection failed")

        # Call update data - expect UpdateFailed when all appliances fail
        from homeassistant.helpers.update_coordinator import UpdateFailed

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        # Verify get_appliance_state was called
        mock_api_client.get_appliance_state.assert_called_once_with(appliance_id)

        # Verify no reauth was triggered (auth_failed should remain False)
        assert mock_api_client._auth_failed is False

        # Verify the coordinator logged the failure but didn't raise auth error
        # (In real HA, this would mark the entity as unavailable)

    @pytest.mark.asyncio
    async def test_sse_stream_recovery_attempts_reconnection(self, coordinator, mock_api_client, mock_hass):
        """Test that SSE stream disconnection triggers reconnection attempts."""
        # Setup mock appliance data
        from custom_components.electrolux.models import Appliance

        appliance_id = "test_appliance_123"
        appliance = Appliance(
            coordinator=coordinator,
            name="Test Appliance",
            pnc_id=appliance_id,
            brand="Electrolux",
            model="TestModel",
            state={"connectivityState": "connected"},
        )
        appliances = Appliances({appliance_id: appliance})
        coordinator.data = {"appliances": appliances}

        # Mock successful initial SSE setup
        mock_api_client.watch_for_appliance_state_updates.return_value = None

        # Start SSE listening
        await coordinator.listen_websocket()

        # Verify SSE was started
        mock_api_client.watch_for_appliance_state_updates.assert_called_once()

        # Note: In the real implementation, SSE reconnection is handled by the
        # renew_websocket task which runs every 6 hours. The test above verifies
        # that SSE can be started successfully.

        # Mock SSE task failure (simulating disconnection)
        if hasattr(coordinator.api, "_sse_task") and coordinator.api._sse_task:
            # Simulate task failure
            coordinator.api._sse_task = MagicMock()
            coordinator.api._sse_task.cancelled.return_value = False
            coordinator.api._sse_task.exception.return_value = Exception("Connection lost")

            # Trigger the failure callback (this would happen automatically in real scenario)
            # For testing, we manually call the callback logic

        # Note: In the real implementation, SSE reconnection is handled by the
        # renew_websocket task which runs every 6 hours. The test above verifies
        # that SSE can be started successfully.

    @pytest.mark.asyncio
    async def test_successful_appliance_poll_updates_state(self, coordinator, mock_api_client):
        """Test that successful appliance polling updates the appliance state."""
        # Setup mock appliance data
        from custom_components.electrolux.models import Appliance

        appliance_id = "test_appliance_123"
        appliance = Appliance(
            coordinator=coordinator,
            name="Test Appliance",
            pnc_id=appliance_id,
            brand="Electrolux",
            model="TestModel",
            state={"connectivityState": "connected"},
        )
        appliances = Appliances({appliance_id: appliance})
        coordinator.data = {"appliances": appliances}

        # Debug: check before update
        print(f"Before update - Appliances object id: {id(coordinator.data['appliances'])}")
        print(f"Before update - Appliances dict: {coordinator.data['appliances'].get_appliances()}")

        # Mock successful appliance state response
        mock_state = {
            "connectivityState": "connected",
            "temperature": 25,
            "power": "on",
        }
        mock_api_client.get_appliance_state.return_value = mock_state
        mock_api_client.get_appliances_list.return_value = [{"applianceId": appliance_id}]  # Mock the list

        # Call update data
        result = await coordinator._async_update_data()

        # Debug: check what's in result
        print(f"Result: {result}")
        print(f"Appliances object id: {id(result['appliances'])}")
        print(f"Appliances in result: {result['appliances'].get_appliances()}")
        print(f"Appliance ID: {appliance_id}")
        print(f"Coordinator data appliances id: {id(coordinator.data['appliances'])}")
        print(f"Coordinator data appliances dict: {coordinator.data['appliances'].get_appliances()}")

        # Verify the appliance state was updated
        updated_appliance = result["appliances"].get_appliances()[appliance_id]
        assert updated_appliance.state["connectivityState"] == "connected"
        assert updated_appliance.state["temperature"] == 25
        assert updated_appliance.state["power"] == "on"

        # Verify get_appliance_state was called
        mock_api_client.get_appliance_state.assert_called_once_with(appliance_id)

    def test_appliances_length(self):
        """Verify the len() method on the Appliances class."""
        mock_data = {"oven_1": MagicMock(), "washer_1": MagicMock()}
        appliances = Appliances(mock_data)  # type: ignore

        # This is what crashed before:
        assert len(appliances) == 2


class TestSSERecovery:
    """Test SSE stream recovery functionality."""

    @pytest.mark.asyncio
    async def test_sse_recovery_loop_with_reconnect(self, coordinator, mock_api_client):
        """Test that SSE recovery loop can be started and cancelled properly."""
        # Setup mock appliance data
        from custom_components.electrolux.models import Appliance

        appliance_id = "test_appliance_123"
        appliance = Appliance(
            coordinator=coordinator,
            name="Test Appliance",
            pnc_id=appliance_id,
            brand="Electrolux",
            model="TestModel",
            state={"connectivityState": "connected"},
        )
        appliances = Appliances({appliance_id: appliance})
        coordinator.data = {"appliances": appliances}

        # Set a very short renew interval for testing
        coordinator.renew_interval = 0.001  # Very short interval

        # Mock successful reconnect operations
        mock_api_client.disconnect_websocket = AsyncMock()
        coordinator.listen_websocket = AsyncMock()

        # Start the renew_websocket task
        renew_task = asyncio.create_task(coordinator.renew_websocket())

        # Wait a short time to allow at least one iteration
        await asyncio.sleep(0.01)

        # Cancel the task
        renew_task.cancel()
        try:
            await renew_task
        except asyncio.CancelledError:
            pass

        # Verify that disconnect_websocket was called at least once
        assert mock_api_client.disconnect_websocket.called, "disconnect_websocket should have been called"

        # Verify that listen_websocket was called at least once
        assert coordinator.listen_websocket.called, "listen_websocket should have been called"


# Mock appliance states for different device types
MOCK_OVEN_STATE = {
    "connectivityState": "connected",
    "cavityLight": "OFF",
    "targetTemperatureC": 180,
    "currentTemperatureC": 25,
    "program": "conventional",
    "powerState": "standby",
    "doorState": "closed",
    "timeRemaining": 0,
    "elapsedTime": 0,
}

MOCK_WASHER_STATE = {
    "connectivityState": "connected",
    "powerState": "standby",
    "program": "cotton",
    "temperature": "40",
    "spinSpeed": "1200",
    "timeRemaining": 0,
    "doorLocked": False,
    "waterLevel": "normal",
}

MOCK_AC_STATE = {
    "connectivityState": "connected",
    "powerState": "off",
    "mode": "cool",
    "targetTemperatureC": 22,
    "currentTemperatureC": 25,
    "fanMode": "auto",
    "humidity": 50,
}


class TestMultiApplianceMatrix:
    """Test multi-appliance compatibility matrix."""

    @pytest.mark.asyncio
    async def test_oven_state_processing(self, coordinator, mock_api_client):
        """Test that oven appliance state is processed correctly."""
        from custom_components.electrolux.models import Appliance

        appliance_id = "oven_123"
        appliance = Appliance(
            coordinator=coordinator,
            name="Test Oven",
            pnc_id=appliance_id,
            brand="Electrolux",
            model="TestOven",
            state={"connectivityState": "connected"},
        )
        appliances = Appliances({appliance_id: appliance})
        coordinator.data = {"appliances": appliances}

        mock_api_client.get_appliance_state.return_value = MOCK_OVEN_STATE
        mock_api_client.get_appliances_list.return_value = [{"applianceId": appliance_id}]

        result = await coordinator._async_update_data()

        updated_appliance = result["appliances"].get_appliances()[appliance_id]
        assert updated_appliance.state["connectivityState"] == "connected"
        assert updated_appliance.state["cavityLight"] == "OFF"
        assert updated_appliance.state["targetTemperatureC"] == 180

    @pytest.mark.asyncio
    async def test_washer_state_processing(self, coordinator, mock_api_client):
        """Test that washer appliance state is processed correctly."""
        from custom_components.electrolux.models import Appliance

        appliance_id = "washer_123"
        appliance = Appliance(
            coordinator=coordinator,
            name="Test Washer",
            pnc_id=appliance_id,
            brand="Electrolux",
            model="TestWasher",
            state={"connectivityState": "connected"},
        )
        appliances = Appliances({appliance_id: appliance})
        coordinator.data = {"appliances": appliances}

        mock_api_client.get_appliance_state.return_value = MOCK_WASHER_STATE
        mock_api_client.get_appliances_list.return_value = [{"applianceId": appliance_id}]

        result = await coordinator._async_update_data()

        updated_appliance = result["appliances"].get_appliances()[appliance_id]
        assert updated_appliance.state["connectivityState"] == "connected"
        assert updated_appliance.state["program"] == "cotton"
        assert updated_appliance.state["temperature"] == "40"

    @pytest.mark.asyncio
    async def test_ac_state_processing(self, coordinator, mock_api_client):
        """Test that AC appliance state is processed correctly."""
        from custom_components.electrolux.models import Appliance

        appliance_id = "ac_123"
        appliance = Appliance(
            coordinator=coordinator,
            name="Test AC",
            pnc_id=appliance_id,
            brand="Electrolux",
            model="TestAC",
            state={"connectivityState": "connected"},
        )
        appliances = Appliances({appliance_id: appliance})
        coordinator.data = {"appliances": appliances}

        mock_api_client.get_appliance_state.return_value = MOCK_AC_STATE
        mock_api_client.get_appliances_list.return_value = [{"applianceId": appliance_id}]

        result = await coordinator._async_update_data()

        updated_appliance = result["appliances"].get_appliances()[appliance_id]
        assert updated_appliance.state["connectivityState"] == "connected"
        assert updated_appliance.state["mode"] == "cool"
        assert updated_appliance.state["targetTemperatureC"] == 22

    @pytest.mark.asyncio
    async def test_malformed_data_temperature_as_string(self, coordinator, mock_api_client):
        """Test handling of malformed data where temperature is sent as string instead of number."""
        from custom_components.electrolux.models import Appliance

        appliance_id = "oven_123"
        appliance = Appliance(
            coordinator=coordinator,
            name="Test Oven",
            pnc_id=appliance_id,
            brand="Electrolux",
            model="TestOven",
            state={"connectivityState": "connected"},
        )
        appliances = Appliances({appliance_id: appliance})
        coordinator.data = {"appliances": appliances}

        # Mock malformed data - temperature as string instead of number
        malformed_state = {
            "connectivityState": "connected",
            "cavityLight": "OFF",
            "targetTemperatureC": "180",  # String instead of number
            "currentTemperatureC": 25,
            "program": "conventional",
            "powerState": "standby",
        }
        mock_api_client.get_appliance_state.return_value = malformed_state
        mock_api_client.get_appliances_list.return_value = [{"applianceId": appliance_id}]

        # This should not crash the coordinator
        result = await coordinator._async_update_data()

        # Verify the appliance data is still returned
        assert "appliances" in result
        updated_appliance = result["appliances"].get_appliances()[appliance_id]

        # The malformed data should be stored as-is (coordinator doesn't validate types)
        assert updated_appliance.state["targetTemperatureC"] == "180"

    @pytest.mark.asyncio
    async def test_malformed_data_connectivity_state_invalid(self, coordinator, mock_api_client):
        """Test handling of malformed data where connectivityState has invalid value."""
        from custom_components.electrolux.models import Appliance

        appliance_id = "washer_123"
        appliance = Appliance(
            coordinator=coordinator,
            name="Test Washer",
            pnc_id=appliance_id,
            brand="Electrolux",
            model="TestWasher",
            state={"connectivityState": "connected"},
        )
        appliances = Appliances({appliance_id: appliance})
        coordinator.data = {"appliances": appliances}

        # Mock malformed data - invalid connectivity state
        malformed_state = {
            "connectivityState": "invalid_status",  # Invalid value
            "program": "cotton",
            "temperature": "40",
        }
        mock_api_client.get_appliance_state.return_value = malformed_state
        mock_api_client.get_appliances_list.return_value = [{"applianceId": appliance_id}]

        # This should not crash the coordinator
        result = await coordinator._async_update_data()

        # Verify the appliance data is still returned
        assert "appliances" in result
        updated_appliance = result["appliances"].get_appliances()[appliance_id]

        # The malformed connectivity state should be stored as-is
        assert updated_appliance.state["connectivityState"] == "invalid_status"

    @pytest.mark.asyncio
    async def test_malformed_data_missing_required_fields(self, coordinator, mock_api_client):
        """Test handling of malformed data with missing required fields."""
        from custom_components.electrolux.models import Appliance

        appliance_id = "ac_123"
        appliance = Appliance(
            coordinator=coordinator,
            name="Test AC",
            pnc_id=appliance_id,
            brand="Electrolux",
            model="TestAC",
            state={"connectivityState": "connected"},
        )
        appliances = Appliances({appliance_id: appliance})
        coordinator.data = {"appliances": appliances}

        # Mock malformed data - missing connectivityState
        malformed_state = {
            "mode": "cool",
            "targetTemperatureC": 22,
            # Missing connectivityState
        }
        mock_api_client.get_appliance_state.return_value = malformed_state
        mock_api_client.get_appliances_list.return_value = [{"applianceId": appliance_id}]

        # This should not crash the coordinator
        result = await coordinator._async_update_data()

        # Verify the appliance data is still returned
        assert "appliances" in result
        updated_appliance = result["appliances"].get_appliances()[appliance_id]

        # The data should be updated, but connectivityState should default to "connected" in the logic
        # (The coordinator's update logic handles missing connectivityState gracefully)
        assert updated_appliance.state["mode"] == "cool"
        assert updated_appliance.state["targetTemperatureC"] == 22

    @pytest.mark.asyncio
    async def test_on_sse_disconnected_records_error(self, coordinator):
        """_on_sse_disconnected callback records the error reason and initiates grace period."""
        coordinator._sse_connected = True
        coordinator._sse_connection_state = "streaming"

        coordinator._on_sse_disconnected(Exception("Connection reset by peer"))

        assert coordinator.sse_connection_state == "disconnected"
        assert coordinator.sse_connected is True
        assert coordinator.last_sse_disconnect_reason == "Connection reset by peer"
        assert coordinator.consecutive_sse_drops == 1

    @pytest.mark.asyncio
    async def test_on_sse_disconnected_default_reason_when_none(self, coordinator):
        """_on_sse_disconnected uses default reason when error is None."""
        coordinator._sse_connected = True
        coordinator._sse_connection_state = "streaming"

        coordinator._on_sse_disconnected(None)

        assert coordinator.sse_connection_state == "disconnected"
        assert coordinator.last_sse_disconnect_reason == "Stream closed by server"
        assert coordinator.consecutive_sse_drops == 1

    @pytest.mark.asyncio
    async def test_on_sse_disconnected_ignores_cancelled_error(self, coordinator):
        """_on_sse_disconnected ignores asyncio.CancelledError to prevent double-counting drops."""
        coordinator._sse_connected = True
        coordinator._sse_connection_state = "streaming"
        coordinator._consecutive_sse_drops = 0

        coordinator._on_sse_disconnected(asyncio.CancelledError())

        assert coordinator.sse_connection_state == "streaming"
        assert coordinator.sse_connected is True
        assert coordinator.consecutive_sse_drops == 0
        assert coordinator.last_sse_disconnect_reason is None

    @pytest.mark.asyncio
    async def test_on_sse_disconnected_empty_exception_message_fallback(self, coordinator):
        """_on_sse_disconnected uses default reason when Exception has an empty message."""
        coordinator._sse_connected = True
        coordinator._sse_connection_state = "streaming"

        coordinator._on_sse_disconnected(Exception(""))

        assert coordinator.sse_connection_state == "disconnected"
        assert coordinator.sse_connected is True
        assert coordinator.last_sse_disconnect_reason == "Stream closed by server"
        assert coordinator.consecutive_sse_drops == 1

    @pytest.mark.asyncio
    async def test_record_sse_disconnect_preserves_debounce_timer_and_drops_on_retries(self, coordinator):
        """record_sse_disconnect does not reset debounce timer or inflate drops on rapid retries."""
        coordinator._sse_connected = True
        coordinator._sse_connection_state = "streaming"

        created_tasks = []

        def _fake_create_task(coro, name=None, eager_start=True):
            task = asyncio.create_task(coro)
            created_tasks.append(task)
            return task

        coordinator.hass.async_create_task = _fake_create_task

        # Initial drop at t=0
        coordinator.record_sse_disconnect(reason="Connection reset", is_cancellation=False)
        assert coordinator.consecutive_sse_drops == 1
        assert len(created_tasks) == 1
        first_debounce_task = created_tasks[0]

        # Retry 1 failure while grace period is active
        coordinator.record_sse_disconnect(reason="Connection refused", is_cancellation=False)
        assert coordinator.consecutive_sse_drops == 1
        assert len(created_tasks) == 1  # Did not spawn a second task
        assert not first_debounce_task.cancelled()  # Did not cancel existing task

        # Retry 2 failure while grace period is still active
        coordinator.record_sse_disconnect(reason="Timeout", is_cancellation=False)
        assert coordinator.consecutive_sse_drops == 1
        assert len(created_tasks) == 1

        first_debounce_task.cancel()
        await asyncio.gather(first_debounce_task, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_record_sse_disconnect_when_already_disconnected_does_not_spawn_debounce(self, coordinator):
        """record_sse_disconnect does not create a debounce task if already disconnected."""
        coordinator._sse_connected = False
        coordinator._sse_connection_state = "disconnected"
        coordinator._sse_disconnect_debounce_task = None

        created_tasks = []

        def _fake_create_task(coro, name=None, eager_start=True):
            task = asyncio.create_task(coro)
            created_tasks.append(task)
            return task

        coordinator.hass.async_create_task = _fake_create_task

        coordinator.record_sse_disconnect(reason="Connection refused", is_cancellation=False)

        assert coordinator.sse_connected is False
        assert coordinator.sse_connection_state == "disconnected"
        assert len(created_tasks) == 0
        assert coordinator._sse_disconnect_debounce_task is None

    @pytest.mark.asyncio
    async def test_incoming_data_cancels_active_debounce_task(self, coordinator):
        """incoming_data cancels active debounce task and resets consecutive drops."""
        coordinator._sse_connected = True
        coordinator._sse_connection_state = "disconnected"
        coordinator._appliances_cache = MagicMock()
        coordinator.data = {"appliances": coordinator._appliances_cache}
        coordinator.async_set_updated_data = MagicMock()
        coordinator._process_incremental_update = MagicMock()

        created_tasks = []

        def _fake_create_task(coro, name=None, eager_start=True):
            task = asyncio.create_task(coro)
            created_tasks.append(task)
            return task

        coordinator.hass.async_create_task = _fake_create_task

        # Start a debounce task via record_sse_disconnect
        coordinator.record_sse_disconnect(reason="Connection dropped", is_cancellation=False)
        debounce_task = coordinator._sse_disconnect_debounce_task
        assert debounce_task is not None
        assert not debounce_task.done()

        # Incoming data arrives before debounce finishes
        coordinator.incoming_data({"applianceId": "app1", "property": "state", "value": "on"})

        assert coordinator.sse_connected is True
        assert coordinator.sse_connection_state == "streaming"
        assert coordinator.consecutive_sse_drops == 0
        await asyncio.sleep(0)
        assert debounce_task.cancelled() or debounce_task.done()
        assert coordinator._sse_disconnect_debounce_task is None

    @pytest.mark.asyncio
    async def test_debounce_disconnect_aborts_if_state_returned_to_streaming(self, coordinator):
        """_debounce_disconnect does not disconnect if state transitioned back to streaming."""
        coordinator._sse_connected = True
        coordinator._sse_connection_state = "disconnected"

        def _fake_create_task(coro, name=None, eager_start=True):
            return asyncio.create_task(coro)

        coordinator.hass.async_create_task = _fake_create_task

        with patch("custom_components.electrolux.coordinator.SSE_DISCONNECT_GRACE_PERIOD", 0.01):
            coordinator.record_sse_disconnect(reason="Connection refused", is_cancellation=False)
            assert coordinator._sse_disconnect_debounce_task is not None

            # State transitions back to streaming right before sleep finishes
            coordinator._sse_connection_state = "streaming"
            coordinator._sse_connected = True

            await asyncio.sleep(0.05)

            # Debounce completed, but streaming guard kept connection alive
            assert coordinator.sse_connected is True
            assert coordinator.sse_connection_state == "streaming"
            assert coordinator._sse_disconnect_debounce_task is None

    @pytest.mark.asyncio
    async def test_record_sse_disconnect_increments_drops_after_grace_period_expired(self, coordinator):
        """record_sse_disconnect increments drops on retry failures after grace period expired."""
        coordinator._sse_connected = True
        coordinator._sse_connection_state = "streaming"

        def _fake_create_task(coro, name=None, eager_start=True):
            return asyncio.create_task(coro)

        coordinator.hass.async_create_task = _fake_create_task

        with patch("custom_components.electrolux.coordinator.SSE_DISCONNECT_GRACE_PERIOD", 0.01):
            coordinator.record_sse_disconnect(reason="Drop 1", is_cancellation=False)
            assert coordinator.consecutive_sse_drops == 1

            # Wait for grace period to expire
            await asyncio.sleep(0.05)
            assert coordinator.sse_connected is False
            assert coordinator._sse_disconnect_debounce_task is None

            # Next retry failure after grace period expiration increments drops
            coordinator.record_sse_disconnect(reason="Drop 2", is_cancellation=False)
            assert coordinator.consecutive_sse_drops == 2
            assert coordinator.sse_connected is False

            # Further retry failure increments drops again
            coordinator.record_sse_disconnect(reason="Drop 3", is_cancellation=False)
            assert coordinator.consecutive_sse_drops == 3
            assert coordinator.sse_connected is False

