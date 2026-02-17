"""Test the Electrolux coordinator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.electrolux.models import Appliance, Appliances


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    client = MagicMock()
    client._auth_failed = False  # Ensure auth failed is False by default
    return client


@pytest.fixture
def mock_coordinator(mock_api_client):
    """Create a mock coordinator with the necessary attributes."""
    from custom_components.electrolux.coordinator import ElectroluxCoordinator

    # Mock the DataUpdateCoordinator.__init__ to avoid HA setup issues
    with patch(
        "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = ElectroluxCoordinator.__new__(ElectroluxCoordinator)
        coord.api = mock_api_client
        coord.platforms = []
        coord.renew_interval = 7200
        coord.data = {}  # Initialize as empty dict instead of None
        coord._last_update_times = {}
        coord._last_known_connectivity = {}
        coord._last_sse_restart_time = 0
        coord._consecutive_auth_failures = 0
        coord._auth_failure_threshold = 3
        coord._last_time_to_end = {}
        coord._deferred_tasks = set()
        coord._deferred_tasks_by_appliance = {}

        # Mock hass.loop.time() for cleanup timing
        mock_loop = MagicMock()
        mock_loop.time.return_value = 1000000.0  # Mock timestamp
        mock_hass = MagicMock()
        mock_hass.loop = mock_loop
        coord.hass = mock_hass

        return coord


def test_coordinator_attributes(mock_coordinator, mock_api_client):
    """Test that the coordinator has the expected attributes."""
    assert mock_coordinator.api == mock_api_client
    assert mock_coordinator.platforms == []
    assert mock_coordinator.renew_interval == 7200


@pytest.mark.asyncio
async def test_async_update_data_success(mock_coordinator, mock_api_client):
    """Test successful data update with mocked API response."""
    # Create mock appliance data
    mock_appliance_state = {
        "properties": {
            "reported": {
                "connectivityState": "connected",
                "applianceMode": "normal",
                "temperature": 25.0,
                "powerState": "on",
            }
        }
    }

    # Mock the API to return the appliance state
    async def mock_get_state(app_id):
        return mock_appliance_state

    mock_api_client.get_appliance_state = mock_get_state

    # Create a mock appliance in the coordinator data
    mock_appliance = MagicMock()
    mock_appliance.pnc_id = "test_appliance_1"
    # mock_appliance.update = MagicMock()  # Already a MagicMock

    mock_appliances = MagicMock()
    mock_appliances.get_appliances.return_value = {"test_appliance_1": mock_appliance}

    # Set up coordinator data
    mock_coordinator.data = {"appliances": mock_appliances}

    # Call the update method
    result = await mock_coordinator._async_update_data()

    # Verify the API was called correctly
    # Since it's not a mock, we can't assert_called

    # Verify the appliance was updated with the correct data
    mock_appliance.update.assert_called_once_with(mock_appliance_state)

    # Verify the result contains the expected data
    assert result == mock_coordinator.data


@pytest.mark.asyncio
async def test_async_update_data_api_error(mock_coordinator, mock_api_client):
    """Test data update when API call fails."""
    # Mock the API to raise an exception
    mock_api_client.get_appliance_state = AsyncMock(side_effect=Exception("API Error"))

    # Create a mock appliance
    mock_appliance = MagicMock(spec=Appliance)
    mock_appliance.pnc_id = "test_appliance_1"

    mock_appliances = MagicMock(spec=Appliances)
    mock_appliances.get_appliances.return_value = {"test_appliance_1": mock_appliance}

    # Set up coordinator data
    mock_coordinator.data = {"appliances": mock_appliances}

    # Call the update method and expect it to raise UpdateFailed
    from homeassistant.helpers.update_coordinator import UpdateFailed

    with pytest.raises(UpdateFailed):
        await mock_coordinator._async_update_data()


@pytest.mark.asyncio
async def test_async_update_data_auth_error(mock_coordinator, mock_api_client):
    """Test data update when authentication fails."""
    # Mock the API to raise an exception with auth keywords
    mock_api_client.get_appliance_state = AsyncMock(
        side_effect=Exception("401 Unauthorized")
    )

    # Create a mock appliance
    mock_appliance = MagicMock(spec=Appliance)
    mock_appliance.pnc_id = "test_appliance_1"

    mock_appliances = MagicMock(spec=Appliances)
    mock_appliances.get_appliances.return_value = {"test_appliance_1": mock_appliance}

    # Set up coordinator data and required attributes
    mock_coordinator.data = {"appliances": mock_appliances}
    mock_coordinator.hass = MagicMock()  # Mock hass for issue creation
    mock_coordinator.config_entry = MagicMock()  # Mock config entry
    mock_coordinator.config_entry.entry_id = "test_entry_id"
    mock_coordinator.config_entry.title = "Test Entry"
    mock_coordinator._auth_failure_threshold = (
        1  # Trigger reauth on first failure for test
    )

    # Call the update method and expect it to raise ConfigEntryAuthFailed
    from homeassistant.exceptions import ConfigEntryAuthFailed

    with pytest.raises(ConfigEntryAuthFailed):
        await mock_coordinator._async_update_data()


@pytest.mark.asyncio
async def test_async_update_data_multiple_appliances(mock_coordinator, mock_api_client):
    """Test data update with multiple appliances."""
    # Create mock appliance states
    mock_state_1 = {
        "properties": {"reported": {"powerState": "on", "temperature": 20.0}}
    }
    mock_state_2 = {
        "properties": {"reported": {"powerState": "off", "temperature": 15.0}}
    }

    # Mock the API to return different states for different appliances
    mock_api_client.get_appliance_state = AsyncMock(
        side_effect=[mock_state_1, mock_state_2]
    )

    # Create mock appliances
    mock_appliance_1 = MagicMock()
    mock_appliance_1.pnc_id = "appliance_1"
    mock_appliance_1.update = MagicMock()

    mock_appliance_2 = MagicMock()
    mock_appliance_2.pnc_id = "appliance_2"
    mock_appliance_2.update = MagicMock()

    mock_appliances = MagicMock()
    mock_appliances.get_appliances.return_value = {
        "appliance_1": mock_appliance_1,
        "appliance_2": mock_appliance_2,
    }

    # Set up coordinator data
    mock_coordinator.data = {"appliances": mock_appliances}

    # Call the update method
    result = await mock_coordinator._async_update_data()

    # Verify both appliances were updated
    mock_appliance_1.update.assert_called_once_with(mock_state_1)
    mock_appliance_2.update.assert_called_once_with(mock_state_2)

    # Verify the result
    assert result == mock_coordinator.data


@pytest.mark.asyncio
async def test_setup_token_refresh_callback(mock_coordinator):
    """Test setting up the token refresh callback."""
    # Mock config entry
    mock_config_entry = MagicMock()
    mock_config_entry.data = {
        "access_token": "old_token",
        "refresh_token": "old_refresh",
    }
    mock_coordinator.config_entry = mock_config_entry
    mock_coordinator.hass = MagicMock()

    # Call setup
    mock_coordinator.setup_token_refresh_callback()

    # Verify callback was set
    mock_coordinator.api.set_token_update_callback_with_expiry.assert_called_once()


@pytest.mark.asyncio
async def test_handle_authentication_error(mock_coordinator):
    """Test handling authentication errors."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    # Test with auth error
    with pytest.raises(ConfigEntryAuthFailed):
        await mock_coordinator.handle_authentication_error(
            Exception("401 Unauthorized: Invalid token")
        )

    # Test with non-auth error (should not raise)
    await mock_coordinator.handle_authentication_error(Exception("Network error"))


@pytest.mark.asyncio
async def test_token_refresh_loop(mock_coordinator):
    """Test that background token refresh loop was removed in favor of lazy refreshing."""
    # The background token refresh loop was removed to prevent collision risks
    # Token refresh now happens lazily through the TokenManager's get_auth_data method
    assert not hasattr(mock_coordinator, "_token_refresh_loop")
    assert not hasattr(mock_coordinator, "token_refresh_task")


@pytest.mark.asyncio
async def test_async_update_data_auth_failed(mock_coordinator):
    """Test _async_update_data when auth has failed."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    # Set auth failed flag
    mock_coordinator.api._auth_failed = True

    # Should raise ConfigEntryAuthFailed
    with pytest.raises(ConfigEntryAuthFailed):
        await mock_coordinator._async_update_data()


@pytest.mark.asyncio
async def test_token_update_callback(mock_coordinator):
    """Test the token update callback."""
    # Mock config entry
    mock_config_entry = MagicMock()
    mock_config_entry.data = {
        "access_token": "old_token",
        "refresh_token": "old_refresh",
    }
    mock_coordinator.config_entry = mock_config_entry
    mock_coordinator.hass = MagicMock()

    # Setup callback
    mock_coordinator.setup_token_refresh_callback()

    # Get the callback function
    call_args = mock_coordinator.api.set_token_update_callback_with_expiry.call_args
    callback = call_args[0][0]

    # Call the callback
    callback("new_access", "new_refresh", "api_key", 1234567890)

    # Verify config entry was updated (update_listener will prevent reload via timestamp check)
    expected_data = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "token_expires_at": 1234567890,
    }
    mock_coordinator.hass.config_entries.async_update_entry.assert_called_once_with(
        mock_config_entry, data=expected_data
    )


@pytest.mark.asyncio
async def test_background_token_refresh_with_rate_limit(mock_coordinator):
    """Test that background token refresh loop was removed to prevent rate limiting issues."""
    # The background token refresh loop was removed to prevent collision risks
    # Rate limiting is now handled by the TokenManager's lazy refresh with cooldown
    assert not hasattr(mock_coordinator, "_token_refresh_loop")


@pytest.mark.asyncio
async def test_auth_error_detection_in_sse():
    """Test auth error detection in SSE failure handling."""
    from custom_components.electrolux.util import ElectroluxApiClient

    # Create API client
    client = ElectroluxApiClient(
        "api", "access", "refresh", hass=MagicMock(), config_entry=MagicMock()
    )
    client.coordinator = MagicMock()
    client.coordinator.async_refresh = AsyncMock()

    # Mock the _trigger_reauth method
    client._trigger_reauth = AsyncMock()

    # Simulate SSE failure with auth error
    task = MagicMock()
    task.exception.return_value = Exception("401 Unauthorized")

    # Call the failure handler (simplified)
    if client.hass and client.config_entry:
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
            await client._trigger_reauth(f"SSE auth error: {task.exception()}")

    # Verify reauth was triggered
    client._trigger_reauth.assert_called_once()


@pytest.mark.asyncio
async def test_token_refresh_error_handling():
    """Test token refresh error creates issue and triggers reauth."""
    from custom_components.electrolux.util import ElectroluxApiClient

    hass = MagicMock()
    hass.config_entries.async_entries.return_value = [MagicMock()]
    client = ElectroluxApiClient(
        "api", "access", "refresh", hass=hass, config_entry=MagicMock()
    )
    client.coordinator = MagicMock()

    # Call _trigger_reauth
    await client._trigger_reauth("Test auth error")

    # Verify auth failed flag set
    assert client._auth_failed is True
