"""Tests for Electrolux diagnostic connectivity binary sensors and health monitors."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.electrolux.api_client import ElectroluxApiClient
from custom_components.electrolux.binary_sensor import (
    ElectroluxCloudApiBinarySensor,
    ElectroluxSseStreamBinarySensor,
    async_setup_entry,
)
from custom_components.electrolux.const import DOMAIN
from custom_components.electrolux.coordinator import ElectroluxCoordinator
from custom_components.electrolux.models import Appliance


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with diagnostic properties."""
    coordinator = MagicMock()
    coordinator.hass = MagicMock()
    coordinator.hass.loop = MagicMock()
    coordinator.hass.loop.time.return_value = 1000.0
    coordinator.api = MagicMock()
    coordinator.api_connected = True
    coordinator.last_api_success_time = time.time()
    coordinator.last_api_status_code = 200
    coordinator.last_api_error = None

    coordinator.sse_connected = True
    coordinator.sse_connection_state = "streaming"
    coordinator.last_sse_event_time = time.time()
    coordinator.last_sse_disconnect_reason = None
    coordinator.consecutive_sse_drops = 0
    coordinator.current_sse_backoff_seconds = 0.0
    coordinator._consecutive_sse_restarts = 0

    return coordinator


@pytest.fixture
def mock_appliance():
    """Create a mock appliance."""
    appliance = MagicMock(spec=Appliance)
    appliance.pnc_id = "TEST_PNC_123"
    appliance.name = "Washer Dryer 8000"
    appliance.model = "L9WEC166BC"
    appliance.mac_address = "AA:BB:CC:DD:EE:FF"
    appliance.entities = []
    return appliance


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    return entry


def _make_coordinator():
    """Instantiate a real ElectroluxCoordinator object with mocked internals."""
    mock_loop = MagicMock()
    mock_loop.time.return_value = 1_000_000.0
    hass = MagicMock()
    hass.loop = mock_loop
    client = MagicMock()

    with patch(
        "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = ElectroluxCoordinator.__new__(ElectroluxCoordinator)
        coord.hass = hass
        coord.api = client
        coord.platforms = []
        coord.data = {}
        coord.renew_task = None
        coord.listen_task = None
        coord._deferred_tasks = set()
        coord._deferred_tasks_by_appliance = {}
        coord._pending_state_refresh_tasks = {}
        coord._listeners = {}
        coord._api_connected = True
        coord._last_api_success_time = 1000.0
        coord._last_api_status_code = 200
        coord._last_api_error = None
        coord._api_health_monitor_task = None
        coord._sse_stall_monitor_task = None
        coord._time_to_end_monitor_task = None
        coord._sse_connected = False
        coord._sse_connection_state = "disconnected"
        coord._last_sse_event_time = 0.0
        coord._last_sse_disconnect_reason = None
        coord._consecutive_sse_drops = 0
        coord._consecutive_sse_restarts = 0
        coord._last_sse_message_time = 0.0
        coord._sse_data_received_since_connect = False
        coord._last_sse_resync_time = 0.0
        coord._pending_sse_resync_task = None
        coord._last_sse_restart_log_count = 0
        coord.async_update_listeners = MagicMock()
        return coord


def _make_client(coordinator=None):
    """Create an ElectroluxApiClient with SDK internals mocked out."""
    with (
        patch("custom_components.electrolux.api_client.ApplianceClient") as mock_sdk,
        patch("custom_components.electrolux.api_client.ElectroluxTokenManager") as mock_tm,
    ):
        mock_tm_instance = MagicMock()
        mock_tm.return_value = mock_tm_instance
        mock_sdk.return_value = MagicMock()
        client = ElectroluxApiClient("key", "access", "refresh", MagicMock(), MagicMock())
        client.coordinator = coordinator
        return client


class TestElectroluxCloudApiBinarySensor:
    """Test ElectroluxCloudApiBinarySensor."""

    def test_sensor_properties_connected(self, mock_coordinator, mock_config_entry):
        """Test entity properties when API is connected."""
        sensor = ElectroluxCloudApiBinarySensor(mock_coordinator, mock_config_entry)

        assert sensor.name == "API"
        assert sensor.unique_id == "test_entry_123_cloud_api"
        assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.is_on is True
        assert sensor.icon == "mdi:cloud-check"

        device_info = sensor.device_info
        assert device_info["identifiers"] == {(DOMAIN, "test_entry_123")}
        assert device_info["name"] == "Electrolux Cloud"
        assert device_info["entry_type"] == DeviceEntryType.SERVICE

        attrs = sensor.extra_state_attributes
        assert attrs["endpoint"] == "api.developer.electrolux.one"
        assert attrs["last_status_code"] == 200
        assert "last_success_time" in attrs
        assert "last_error" not in attrs

    def test_sensor_properties_disconnected(self, mock_coordinator, mock_config_entry):
        """Test entity properties when API is failing."""
        mock_coordinator.api_connected = False
        mock_coordinator.last_api_status_code = 500
        mock_coordinator.last_api_error = "HTTP 500 Internal Server Error"

        sensor = ElectroluxCloudApiBinarySensor(mock_coordinator, mock_config_entry)

        assert sensor.is_on is False
        assert sensor.icon == "mdi:cloud-alert"
        attrs = sensor.extra_state_attributes
        assert attrs["last_status_code"] == 500
        assert attrs["last_error"] == "HTTP 500 Internal Server Error"

    def test_sensor_properties_no_prior_success(self, mock_coordinator, mock_config_entry):
        """Test extra_state_attributes when last_api_success_time is 0."""
        mock_coordinator.last_api_success_time = 0.0
        sensor = ElectroluxCloudApiBinarySensor(mock_coordinator, mock_config_entry)
        attrs = sensor.extra_state_attributes
        assert "last_success_time" not in attrs


class TestElectroluxSseStreamBinarySensor:
    """Test ElectroluxSseStreamBinarySensor."""

    def test_sensor_properties_streaming(self, mock_coordinator, mock_config_entry):
        """Test entity properties when SSE stream is active."""
        sensor = ElectroluxSseStreamBinarySensor(mock_coordinator, mock_config_entry)

        assert sensor.name == "Live Stream"
        assert sensor.unique_id == "test_entry_123_sse_stream"
        assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.is_on is True
        assert sensor.icon == "mdi:broadcast"

        device_info = sensor.device_info
        assert device_info["identifiers"] == {(DOMAIN, "test_entry_123")}
        assert device_info["name"] == "Electrolux Cloud"
        assert device_info["entry_type"] == DeviceEntryType.SERVICE

        attrs = sensor.extra_state_attributes
        assert attrs["endpoint"] == "live.eu.developer.electrolux.one"
        assert attrs["connection_state"] == "streaming"
        assert attrs["consecutive_drops"] == 0
        assert attrs["backoff_seconds"] == 0.0
        assert "last_event_time" in attrs

    def test_sensor_properties_dropped(self, mock_coordinator, mock_config_entry):
        """Test entity properties when SSE stream dropped."""
        mock_coordinator.sse_connected = False
        mock_coordinator.sse_connection_state = "reconnecting"
        mock_coordinator.consecutive_sse_drops = 3
        mock_coordinator.current_sse_backoff_seconds = 60.0
        mock_coordinator.last_sse_disconnect_reason = "TransferEncodingError: 400"

        sensor = ElectroluxSseStreamBinarySensor(mock_coordinator, mock_config_entry)

        assert sensor.is_on is False
        assert sensor.icon == "mdi:broadcast-off"

        attrs = sensor.extra_state_attributes
        assert attrs["connection_state"] == "reconnecting"
        assert attrs["consecutive_drops"] == 3
        assert attrs["backoff_seconds"] == 60.0
        assert attrs["disconnect_reason"] == "TransferEncodingError: 400"

    def test_sensor_properties_no_events_yet(self, mock_coordinator, mock_config_entry):
        """Test extra_state_attributes when last_sse_event_time is 0."""
        mock_coordinator.last_sse_event_time = 0.0
        mock_coordinator.last_sse_disconnect_reason = None
        sensor = ElectroluxSseStreamBinarySensor(mock_coordinator, mock_config_entry)
        attrs = sensor.extra_state_attributes
        assert "last_event_time" not in attrs
        assert "disconnect_reason" not in attrs


class TestCoordinatorDiagnosticMethods:
    """Test coordinator health monitor and state tracking methods."""

    @pytest.mark.asyncio
    async def test_check_api_health_success(self):
        """Test _check_api_health when /ping returns HTTP 200."""
        mock_response = AsyncMock()
        mock_response.status = 200

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch(
            "custom_components.electrolux.coordinator.async_get_clientsession",
            return_value=mock_session,
        ):
            coordinator = _make_coordinator()
            await coordinator._check_api_health()

            assert coordinator.api_connected is True
            assert coordinator.last_api_status_code == 200
            assert coordinator.last_api_error is None
            assert coordinator.last_api_success_time > 0
            coordinator.async_update_listeners.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_api_health_500_error(self):
        """Test _check_api_health when /ping returns HTTP 500."""
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch(
            "custom_components.electrolux.coordinator.async_get_clientsession",
            return_value=mock_session,
        ):
            coordinator = _make_coordinator()
            await coordinator._check_api_health()

            assert coordinator.api_connected is False
            assert coordinator.last_api_status_code == 500
            assert coordinator.last_api_error == "HTTP 500"

    @pytest.mark.asyncio
    async def test_check_api_health_network_exception(self):
        """Test _check_api_health when request encounters network error."""
        mock_session = MagicMock()
        mock_session.get.side_effect = aiohttp.ClientError("DNS resolution failed")

        with patch(
            "custom_components.electrolux.coordinator.async_get_clientsession",
            return_value=mock_session,
        ):
            coordinator = _make_coordinator()
            await coordinator._check_api_health()

            assert coordinator.api_connected is False
            assert coordinator.last_api_status_code is None
            assert "DNS resolution failed" in coordinator.last_api_error

    @pytest.mark.asyncio
    async def test_on_sse_connected_resets_diagnostic_state(self):
        """Test _on_sse_connected updates coordinator SSE properties."""
        coordinator = _make_coordinator()

        coordinator._sse_connected = False
        coordinator._sse_connection_state = "disconnected"
        coordinator._consecutive_sse_drops = 5
        coordinator._last_sse_disconnect_reason = "Server closed connection"

        # Mock appliances to avoid get_appliances error during state resync
        coordinator.data = {"appliances": MagicMock()}
        coordinator.data["appliances"].get_appliances.return_value = {}

        await coordinator._on_sse_connected()

        assert coordinator.sse_connected is True
        assert coordinator.sse_connection_state == "streaming"
        assert coordinator.consecutive_sse_drops == 0
        assert coordinator.last_sse_disconnect_reason is None
        coordinator.async_update_listeners.assert_called()

    def test_current_sse_backoff_calculation(self):
        """Test current_sse_backoff_seconds when restarts occur."""
        coordinator = _make_coordinator()

        assert coordinator.current_sse_backoff_seconds == 0.0

        coordinator._consecutive_sse_restarts = 1
        with patch.object(ElectroluxCoordinator, "_sse_backoff_seconds", return_value=15.0):
            assert coordinator.current_sse_backoff_seconds == 15.0

    @pytest.mark.asyncio
    async def test_close_websocket_cleans_up_api_health_task(self):
        """Test close_websocket cancels the API health monitor task."""
        async def _dummy_loop():
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                pass

        real_task = asyncio.create_task(_dummy_loop())
        coordinator = _make_coordinator()
        coordinator._api_health_monitor_task = real_task
        coordinator.api = AsyncMock()

        await coordinator.close_websocket()

        assert real_task.cancelled() or real_task.done()
        assert coordinator._api_health_monitor_task is None
        assert coordinator.sse_connected is False
        assert coordinator.sse_connection_state == "disconnected"


class TestApiClientDiagnosticHook:
    """Test api_client integration with coordinator diagnostic state."""

    @pytest.mark.asyncio
    async def test_handle_api_call_success_records_state(self):
        """Test _handle_api_call records 200 OK on successful calls."""
        mock_coordinator = MagicMock()
        mock_coordinator._listeners = {}
        client = _make_client(coordinator=mock_coordinator)

        coro = AsyncMock(return_value={"status": "ok"})()
        result = await client._handle_api_call(coro)

        assert result == {"status": "ok"}
        assert mock_coordinator._api_connected is True
        assert mock_coordinator._last_api_status_code == 200
        assert mock_coordinator._last_api_error is None

    @pytest.mark.asyncio
    async def test_handle_api_call_failure_records_error(self):
        """Test _handle_api_call records failure on exception."""
        mock_coordinator = MagicMock()
        mock_coordinator._listeners = {}
        client = _make_client(coordinator=mock_coordinator)

        err = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=503,
            message="Service Unavailable",
        )

        async def _failing_coro():
            raise err

        with pytest.raises(aiohttp.ClientResponseError):
            await client._handle_api_call(_failing_coro())

        assert mock_coordinator._api_connected is False
        assert mock_coordinator._last_api_status_code == 503
        assert "503" in mock_coordinator._last_api_error


@pytest.mark.asyncio
async def test_async_setup_entry_adds_service_diagnostic_sensors(mock_coordinator, mock_appliance, mock_config_entry):
    """Test async_setup_entry creates service-level diagnostic sensors."""
    hass = MagicMock()
    mock_coordinator.data = {"appliances": MagicMock()}
    mock_coordinator.data["appliances"].appliances = {"TEST_PNC_123": mock_appliance}
    mock_config_entry.runtime_data = mock_coordinator

    mock_add_entities = MagicMock()
    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    mock_add_entities.assert_called_once()
    added_entities = mock_add_entities.call_args[0][0]

    api_sensors = [e for e in added_entities if isinstance(e, ElectroluxCloudApiBinarySensor)]
    sse_sensors = [e for e in added_entities if isinstance(e, ElectroluxSseStreamBinarySensor)]

    assert len(api_sensors) == 1
    assert len(sse_sensors) == 1
    assert api_sensors[0].unique_id == "test_entry_123_cloud_api"
    assert sse_sensors[0].unique_id == "test_entry_123_sse_stream"
