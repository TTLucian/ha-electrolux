"""Test ElectroluxTokenManager token refresh with 401 Unauthorized response."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.electrolux.util import ElectroluxTokenManager


class TestElectroluxTokenManager401:
    """Test token refresh behavior with 401 Unauthorized response."""

    @pytest.mark.asyncio
    async def test_get_auth_data_401_triggers_callback(self):
        """Test that get_auth_data triggers auth error callback on 401 during refresh."""
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

        # Set token to be expired (force refresh) - set to past time
        token_manager._expires_at = 100000000  # Far in the past

        # Mock the request to raise a 401 Unauthorized error
        mock_exception = Exception("401 Unauthorized")
        with patch(
            "custom_components.electrolux.util.request", side_effect=mock_exception
        ):
            # Call get_auth_data (this will trigger refresh)
            auth_data = await token_manager.get_auth_data()

            # Assert that the auth error callback was triggered with the error message
            mock_callback.assert_called_once()
            call_args = mock_callback.call_args[0][0]  # First positional argument
            assert "401 Unauthorized" in call_args

            # Should still return the old auth data
            assert auth_data.access_token == "test_access"
            assert auth_data.refresh_token == "test_refresh"

    @pytest.mark.asyncio
    async def test_get_auth_data_400_invalid_grant_triggers_callback(self):
        """Test that get_auth_data triggers auth error callback on 400 Bad Request with invalid_grant."""
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

        # Set token to be expired (force refresh) - set to past time
        token_manager._expires_at = 100000000  # Far in the past

        # Mock the request to raise a 400 Bad Request with invalid_grant error
        mock_exception = Exception("400 Bad Request: invalid grant")
        with patch(
            "custom_components.electrolux.util.request", side_effect=mock_exception
        ):
            # Call get_auth_data (this will trigger refresh)
            auth_data = await token_manager.get_auth_data()

            # Assert that the auth error callback was triggered with the error message
            mock_callback.assert_called_once()
            call_args = mock_callback.call_args[0][0]  # First positional argument
            assert "invalid grant" in call_args

            # Should still return the old auth data
            assert auth_data.access_token == "test_access"
            assert auth_data.refresh_token == "test_refresh"

    @pytest.mark.asyncio
    async def test_get_auth_data_200_updates_expires_at(self):
        """Test that get_auth_data updates _expires_at on successful refresh."""
        # Create token manager instance
        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        # Set token to be expired (force refresh) - set to past time
        token_manager._expires_at = 100000000  # Far in the past

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
            # Call get_auth_data (this will trigger refresh)
            auth_data = await token_manager.get_auth_data()

            # Assert that _expires_at is updated to exactly 12 hours in the future
            assert token_manager._expires_at == expected_expires_at

            # Assert that the returned auth data has the new tokens
            assert auth_data.access_token == "new_access_token"
            assert auth_data.refresh_token == "new_refresh_token"
            assert auth_data.api_key == "test_api_key"

    @pytest.mark.asyncio
    async def test_concurrent_sdk_refresh_calls(self):
        """Test concurrent refresh_token() calls don't cause race conditions."""
        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        # Force token expiration
        token_manager._expires_at = 100000000

        refresh_call_count = 0

        async def mock_request(method, url, json_body):
            nonlocal refresh_call_count
            refresh_call_count += 1
            await asyncio.sleep(0.1)  # Simulate network delay
            return {
                "accessToken": f"new_access_{refresh_call_count}",
                "refreshToken": f"new_refresh_{refresh_call_count}",
                "expiresIn": 43200,
            }

        with patch(
            "custom_components.electrolux.util.request", side_effect=mock_request
        ), patch(
            "custom_components.electrolux.util.time.time", return_value=1000000000
        ):

            # Simulate SDK calling refresh_token() directly from 3 concurrent 401 responses
            results = await asyncio.gather(
                token_manager.refresh_token(),
                token_manager.refresh_token(),
                token_manager.refresh_token(),
            )

        # All should succeed (no "Invalid grant")
        assert all(results), "All concurrent refresh calls should succeed"

        # Should only make ONE actual HTTP request (others wait and skip)
        assert (
            refresh_call_count == 1
        ), f"Expected 1 HTTP request, got {refresh_call_count}"

        # Verify tokens were updated
        auth_data = await token_manager.get_auth_data()
        assert "new_access_1" in auth_data.access_token
        assert "new_refresh_1" in auth_data.refresh_token
