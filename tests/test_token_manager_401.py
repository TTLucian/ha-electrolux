"""Test ElectroluxTokenManager token refresh with 401 Unauthorized response."""

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.electrolux.util import ElectroluxTokenManager


class TestElectroluxTokenManager401:
    """Test token refresh behavior with 401 Unauthorized response."""

    @pytest.mark.asyncio
    async def test_refresh_token_401_acquires_lock_and_triggers_callback(self):
        """Test that refresh_token acquires lock and triggers auth error callback on 401."""
        # Create mock callback to track if it's called
        mock_callback = AsyncMock()

        # Create token manager instance
        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        # Set the auth error callback
        token_manager.set_auth_error_callback(mock_callback)

        # Mock the refresh lock to track acquisition
        mock_lock = AsyncMock()
        token_manager._refresh_lock = mock_lock

        # Mock the request to raise a 401 Unauthorized error
        mock_exception = Exception("401 Unauthorized")
        with patch(
            "custom_components.electrolux.util.request", side_effect=mock_exception
        ):
            # Call refresh_token
            result = await token_manager.refresh_token()

            # Assert that refresh_token returned False (failure)
            assert result is False

            # Assert that the lock was acquired (entered)
            mock_lock.__aenter__.assert_called_once()
            mock_lock.__aexit__.assert_called_once()

            # Assert that the auth error callback was triggered with the error message
            mock_callback.assert_called_once()
            call_args = mock_callback.call_args[0][0]  # First positional argument
            assert "401 Unauthorized" in call_args

    @pytest.mark.asyncio
    async def test_refresh_token_400_invalid_grant_triggers_callback(self):
        """Test that refresh_token triggers auth error callback on 400 Bad Request with invalid_grant."""
        # Create mock callback to track if it's called
        mock_callback = AsyncMock()

        # Create token manager instance
        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        # Set the auth error callback
        token_manager.set_auth_error_callback(mock_callback)

        # Mock the refresh lock to track acquisition
        mock_lock = AsyncMock()
        token_manager._refresh_lock = mock_lock

        # Mock the request to raise a 400 Bad Request with invalid_grant error
        mock_exception = Exception("400 Bad Request: invalid grant")
        with patch(
            "custom_components.electrolux.util.request", side_effect=mock_exception
        ):
            # Call refresh_token
            result = await token_manager.refresh_token()

            # Assert that refresh_token returned False (failure)
            assert result is False

            # Assert that the lock was acquired (entered)
            mock_lock.__aenter__.assert_called_once()
            mock_lock.__aexit__.assert_called_once()

            # Assert that the auth error callback was triggered with the error message
            mock_callback.assert_called_once()
            call_args = mock_callback.call_args[0][0]  # First positional argument
            assert "invalid grant" in call_args

    @pytest.mark.asyncio
    async def test_refresh_token_200_updates_expires_at_and_releases_lock(self):
        """Test that refresh_token updates _expires_at to 12 hours future and releases lock on 200 OK."""
        # Create token manager instance
        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        # Mock the refresh lock to track acquisition/release
        mock_lock = AsyncMock()
        token_manager._refresh_lock = mock_lock

        # Mock time.time to return a fixed value for deterministic testing
        fixed_time = 1000000000
        expected_expires_at = fixed_time + 43200  # 12 hours = 43200 seconds

        # Mock the request to return a successful 200 OK response
        mock_response = {
            "accessToken": "new_access_token",
            "refreshToken": "new_refresh_token",
            "expiresIn": 43200,
        }
        with patch(
            "custom_components.electrolux.util.time.time", return_value=fixed_time
        ), patch(
            "custom_components.electrolux.util.request", return_value=mock_response
        ):
            # Call refresh_token
            result = await token_manager.refresh_token()

            # Assert that refresh_token returned True (success)
            assert result is True

            # Assert that _expires_at is updated to exactly 12 hours in the future
            assert token_manager._expires_at == expected_expires_at

            # Assert that the lock was acquired and released
            mock_lock.__aenter__.assert_called_once()
            mock_lock.__aexit__.assert_called_once()
