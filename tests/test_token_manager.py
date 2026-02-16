"""Test ElectroluxTokenManager token refresh with 401 Unauthorized response."""

import asyncio
import time
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

        # Create expired JWT payload (expired 1 hour ago)
        expired_time = int(time.time()) - 3600
        mock_jwt_payload = {"exp": expired_time, "sub": "test_user"}

        # Create token manager instance
        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        # Set the auth error callback
        token_manager.set_auth_error_callback(mock_callback)

        # Mock the request to raise a 401 Unauthorized error
        mock_exception = Exception("401 Unauthorized")
        with patch(
            "custom_components.electrolux.util.jwt.decode",
            return_value=mock_jwt_payload,
        ), patch(
            "custom_components.electrolux.util.request", side_effect=mock_exception
        ):
            # Call get_auth_data (this will trigger refresh due to expired token)
            # SDK raises exception when refresh fails
            with pytest.raises(Exception, match="Token expired and refresh failed"):
                await token_manager.get_auth_data()

            # Assert that the auth error callback was triggered with the error message
            mock_callback.assert_called_once()
            call_args = mock_callback.call_args[0][0]  # First positional argument
            assert "401 Unauthorized" in call_args

    @pytest.mark.asyncio
    async def test_get_auth_data_400_invalid_grant_triggers_callback(self):
        """Test that get_auth_data triggers auth error callback on 400 Bad Request with invalid_grant."""
        # Create mock callback to track if it's called
        mock_callback = AsyncMock()

        # Create expired JWT payload (expired 1 hour ago)
        expired_time = int(time.time()) - 3600
        mock_jwt_payload = {"exp": expired_time, "sub": "test_user"}

        # Create token manager instance
        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        # Set the auth error callback
        token_manager.set_auth_error_callback(mock_callback)

        # Mock the request to raise a 400 Bad Request with invalid_grant error
        mock_exception = Exception("400 Bad Request: invalid grant")
        with patch(
            "custom_components.electrolux.util.jwt.decode",
            return_value=mock_jwt_payload,
        ), patch(
            "custom_components.electrolux.util.request", side_effect=mock_exception
        ):
            # Call get_auth_data (this will trigger refresh)
            # SDK raises exception when refresh fails
            with pytest.raises(Exception, match="Token expired and refresh failed"):
                await token_manager.get_auth_data()

            # Assert that the auth error callback was triggered with the error message
            mock_callback.assert_called_once()
            call_args = mock_callback.call_args[0][0]  # First positional argument
            assert "invalid grant" in call_args

    @pytest.mark.asyncio
    async def test_get_auth_data_200_refreshes_token(self):
        """Test that get_auth_data successfully refreshes expired token."""
        # Create expired JWT payload (expired 1 hour ago)
        expired_time = int(time.time()) - 3600
        mock_expired_jwt = {"exp": expired_time, "sub": "test_user"}

        # Create fresh JWT payload (expires in 12 hours)
        fresh_time = int(time.time()) + 43200
        mock_fresh_jwt = {"exp": fresh_time, "sub": "test_user"}

        # Create token manager instance
        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        # Mock the request to return a successful 200 OK response
        mock_response = {
            "accessToken": "new_access_token",
            "refreshToken": "new_refresh_token",
            "expiresIn": 43200,
        }

        jwt_decode_call_count = [0]

        def mock_jwt_decode(token, **kwargs):
            jwt_decode_call_count[0] += 1
            # First calls check old token (expired), later calls check new token (fresh)
            if token == "test_access":
                return mock_expired_jwt
            else:
                return mock_fresh_jwt

        with patch(
            "custom_components.electrolux.util.jwt.decode", side_effect=mock_jwt_decode
        ), patch(
            "custom_components.electrolux.util.request", return_value=mock_response
        ):
            # Call get_auth_data (this will trigger refresh due to expired token)
            auth_data = await token_manager.get_auth_data()

            # Assert that the returned auth data has the new tokens
            assert auth_data.access_token == "new_access_token"
            assert auth_data.refresh_token == "new_refresh_token"
            assert auth_data.api_key == "test_api_key"

            # Verify token is now considered valid
            assert token_manager.is_token_valid() is True

    @pytest.mark.asyncio
    async def test_concurrent_sdk_refresh_calls(self):
        """Test concurrent refresh_token() calls don't cause race conditions."""
        fixed_time = 1000000000

        # Calculate times relative to the mocked time
        expired_time = fixed_time - 3600  # Expired 1 hour ago
        mock_expired_jwt = {"exp": expired_time, "sub": "test_user"}

        # Fresh token after refresh
        fresh_time = fixed_time + 43200  # Expires in 12 hours
        mock_fresh_jwt = {"exp": fresh_time, "sub": "test_user"}

        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        refresh_call_count = 0
        jwt_call_count = 0

        async def mock_request(method, url, json_body):
            nonlocal refresh_call_count
            refresh_call_count += 1
            await asyncio.sleep(0.1)  # Simulate network delay
            return {
                "accessToken": f"new_access_{refresh_call_count}",
                "refreshToken": f"new_refresh_{refresh_call_count}",
                "expiresIn": 43200,
            }

        def mock_jwt_decode(token, **kwargs):
            nonlocal jwt_call_count
            jwt_call_count += 1
            # First token is always expired to force refresh
            # After refresh, new tokens are fresh
            if "new_access" in token:
                return mock_fresh_jwt
            else:
                return mock_expired_jwt

        with patch(
            "custom_components.electrolux.util.jwt.decode", side_effect=mock_jwt_decode
        ), patch(
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

            # Should only make ONE actual HTTP request (others wait and skip due to lock)
            assert (
                refresh_call_count == 1
            ), f"Expected 1 HTTP request, got {refresh_call_count}"

            # Verify tokens were updated
            auth_data = await token_manager.get_auth_data()
            assert "new_access_1" in auth_data.access_token
            assert "new_refresh_1" in auth_data.refresh_token

    @pytest.mark.asyncio
    async def test_proactive_refresh_15_min_buffer(self):
        """Test that tokens are proactively refreshed 15 minutes before expiry."""
        current_time = int(time.time())
        # Token expires in 10 minutes (600 seconds) - should trigger refresh
        expiring_soon_time = current_time + 600
        mock_expiring_jwt = {"exp": expiring_soon_time, "sub": "test_user"}

        # Fresh token expires in 12 hours
        fresh_time = current_time + 43200
        mock_fresh_jwt = {"exp": fresh_time, "sub": "test_user"}

        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        mock_response = {
            "accessToken": "refreshed_token",
            "refreshToken": "refreshed_refresh",
            "expiresIn": 43200,
        }

        refresh_called = False

        async def mock_request(method, url, json_body):
            nonlocal refresh_called
            refresh_called = True
            return mock_response

        def mock_jwt_decode(token, **kwargs):
            if token == "test_access":
                return mock_expiring_jwt
            else:
                return mock_fresh_jwt

        with patch(
            "custom_components.electrolux.util.jwt.decode", side_effect=mock_jwt_decode
        ), patch("custom_components.electrolux.util.request", side_effect=mock_request):
            # SDK's get_auth_data() should trigger proactive refresh
            auth_data = await token_manager.get_auth_data()

            # Verify refresh was called proactively
            assert refresh_called, "Proactive refresh should have been triggered"
            assert auth_data.access_token == "refreshed_token"

    @pytest.mark.asyncio
    async def test_valid_token_no_refresh(self):
        """Test that valid tokens don't trigger unnecessary refresh."""
        current_time = int(time.time())
        # Token expires in 2 hours (7200 seconds) - should NOT trigger refresh
        valid_time = current_time + 7200
        mock_valid_jwt = {"exp": valid_time, "sub": "test_user"}

        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        refresh_called = False

        async def mock_request(method, url, json_body):
            nonlocal refresh_called
            refresh_called = True
            return {}

        with patch(
            "custom_components.electrolux.util.jwt.decode", return_value=mock_valid_jwt
        ), patch("custom_components.electrolux.util.request", side_effect=mock_request):
            # Should return auth data without refresh
            auth_data = await token_manager.get_auth_data()

            # Verify NO refresh was called
            assert not refresh_called, "Valid token should not trigger refresh"
            assert auth_data.access_token == "test_access"

    @pytest.mark.asyncio
    async def test_refresh_cooldown_after_failure(self):
        """Test that failed refresh sets up cooldown tracking.

        This verifies that _last_failed_refresh is set and _consecutive_failures
        is tracked correctly. The actual cooldown enforcement is tested in
        test_exponential_backoff_on_repeated_failures.
        """
        fixed_time = 1000000000
        # Token expires in 10 minutes (within 15-min buffer, so needs refresh)
        expiring_time = fixed_time + 600
        mock_expiring_jwt = {"exp": expiring_time, "sub": "test_user"}

        mock_exception = Exception("Network error")
        refresh_attempts = 0

        async def mock_request(method, url, json_body):
            nonlocal refresh_attempts
            refresh_attempts += 1
            raise mock_exception

        # Patch time.time() before creating TokenManager to avoid clock skew detection
        # during initialization
        with patch(
            "custom_components.electrolux.util.jwt.decode",
            return_value=mock_expiring_jwt,
        ), patch(
            "custom_components.electrolux.util.request", side_effect=mock_request
        ), patch(
            "custom_components.electrolux.util.time.time", return_value=fixed_time
        ):
            token_manager = ElectroluxTokenManager(
                access_token="test_access",
                refresh_token="test_refresh",
                api_key="test_api_key",
            )

            # Verify initial state
            assert token_manager._consecutive_failures == 0
            assert token_manager._last_failed_refresh == 0

            # First refresh fails (token is expiring, triggers refresh)
            result1 = await token_manager.refresh_token()
            assert result1 is False
            assert refresh_attempts == 1

            # Verify cooldown tracking is set up correctly
            assert token_manager._consecutive_failures == 1
            assert token_manager._last_failed_refresh == fixed_time

    @pytest.mark.asyncio
    async def test_token_update_callback_with_expiry(self):
        """Test that token update callback receives expiry timestamp."""
        fixed_time = 1000000000
        expired_time = fixed_time - 3600  # Expired 1 hour ago
        mock_expired_jwt = {"exp": expired_time, "sub": "test_user"}

        fresh_time = fixed_time + 43200  # Expires in 12 hours
        mock_fresh_jwt = {"exp": fresh_time, "sub": "test_user"}

        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        callback_data = {}

        def mock_callback_with_expiry(access_token, refresh_token, api_key, expires_at):
            callback_data["access_token"] = access_token
            callback_data["refresh_token"] = refresh_token
            callback_data["expires_at"] = expires_at

        token_manager.set_token_update_callback_with_expiry(mock_callback_with_expiry)

        mock_response = {
            "accessToken": "new_token",
            "refreshToken": "new_refresh",
            "expiresIn": 43200,
        }

        def mock_jwt_decode(token, **kwargs):
            if token == "test_access":
                return mock_expired_jwt
            elif "new_token" in token:
                return mock_fresh_jwt
            else:
                return mock_expired_jwt

        with patch(
            "custom_components.electrolux.util.jwt.decode", side_effect=mock_jwt_decode
        ), patch(
            "custom_components.electrolux.util.request", return_value=mock_response
        ), patch(
            "custom_components.electrolux.util.time.time", return_value=fixed_time
        ):
            # Trigger refresh via get_auth_data since token is expired
            await token_manager.get_auth_data()

            # Verify callback was called with expiry timestamp
            assert callback_data["access_token"] == "new_token"
            assert callback_data["refresh_token"] == "new_refresh"
            assert callback_data["expires_at"] == fixed_time + 43200

    @pytest.mark.asyncio
    async def test_jwt_decode_failure_forces_refresh(self):
        """Test that JWT decode failure marks token as invalid and forces refresh."""
        token_manager = ElectroluxTokenManager(
            access_token="malformed_token",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        # JWT decode raises exception for malformed token
        with patch(
            "custom_components.electrolux.util.jwt.decode",
            side_effect=Exception("Invalid JWT"),
        ):
            # is_token_valid should return False for malformed token
            assert token_manager.is_token_valid() is False

    @pytest.mark.asyncio
    async def test_missing_exp_claim_marks_invalid(self):
        """Test that JWT without exp claim is marked as invalid."""
        mock_jwt_no_exp = {"sub": "test_user"}  # Missing 'exp' claim

        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        with patch(
            "custom_components.electrolux.util.jwt.decode",
            return_value=mock_jwt_no_exp,
        ):
            # Token should be considered invalid without exp claim
            assert token_manager.is_token_valid() is False

    @pytest.mark.asyncio
    async def test_network_error_doesnt_trigger_reauth(self):
        """Test that network errors don't trigger reauth callback."""
        mock_callback = AsyncMock()

        expired_time = int(time.time()) - 3600
        mock_expired_jwt = {"exp": expired_time, "sub": "test_user"}

        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        token_manager.set_auth_error_callback(mock_callback)

        # Network error (not auth error)
        mock_exception = Exception("Connection timeout")

        with patch(
            "custom_components.electrolux.util.jwt.decode",
            return_value=mock_expired_jwt,
        ), patch(
            "custom_components.electrolux.util.request", side_effect=mock_exception
        ):
            result = await token_manager.refresh_token()

            # Refresh should fail but NOT trigger reauth
            assert result is False
            mock_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_exponential_backoff_on_repeated_failures(self):
        """Test that consecutive failures trigger exponential backoff (60→120→240→300s max)."""
        fixed_time = 1000000000
        expired_time = fixed_time - 3600
        mock_expired_jwt = {"exp": expired_time, "sub": "test_user"}

        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        mock_exception = Exception("Network error")
        refresh_attempts = 0

        async def mock_request(method, url, json_body):
            nonlocal refresh_attempts
            refresh_attempts += 1
            raise mock_exception

        current_time = fixed_time

        def mock_time():
            return current_time

        with patch(
            "custom_components.electrolux.util.jwt.decode",
            return_value=mock_expired_jwt,
        ), patch(
            "custom_components.electrolux.util.request", side_effect=mock_request
        ), patch(
            "custom_components.electrolux.util.time.time", side_effect=mock_time
        ):
            # First failure: cooldown = 60s
            result1 = await token_manager.refresh_token()
            assert result1 is False
            assert token_manager._consecutive_failures == 1
            assert refresh_attempts == 1

            # Advance time by 61 seconds (past first cooldown)
            current_time += 61

            # Second failure: cooldown = 120s
            result2 = await token_manager.refresh_token()
            assert result2 is False
            assert token_manager._consecutive_failures == 2
            assert refresh_attempts == 2

            # Advance time by 121 seconds (past second cooldown)
            current_time += 121

            # Third failure: cooldown = 240s
            result3 = await token_manager.refresh_token()
            assert result3 is False
            assert token_manager._consecutive_failures == 3
            assert refresh_attempts == 3

            # Advance time by 241 seconds (past third cooldown)
            current_time += 241

            # Fourth failure: cooldown = 300s (capped at max)
            result4 = await token_manager.refresh_token()
            assert result4 is False
            assert token_manager._consecutive_failures == 4
            assert refresh_attempts == 4

    @pytest.mark.asyncio
    async def test_cooldown_bypass_when_token_expired(self):
        """Test that _marked_needs_refresh bypasses cooldown for expired tokens."""
        fixed_time = 1000000000
        expired_time = fixed_time - 3600  # Expired 1 hour ago
        mock_expired_jwt = {"exp": expired_time, "sub": "test_user"}

        token_manager = ElectroluxTokenManager(
            access_token="test_access",
            refresh_token="test_refresh",
            api_key="test_api_key",
        )

        mock_exception = Exception("Network error")
        refresh_attempts = 0

        async def mock_request(method, url, json_body):
            nonlocal refresh_attempts
            refresh_attempts += 1
            raise mock_exception

        with patch(
            "custom_components.electrolux.util.jwt.decode",
            return_value=mock_expired_jwt,
        ), patch(
            "custom_components.electrolux.util.request", side_effect=mock_request
        ), patch(
            "custom_components.electrolux.util.time.time", return_value=fixed_time
        ):
            # First refresh fails, setting cooldown
            result1 = await token_manager.refresh_token()
            assert result1 is False
            assert refresh_attempts == 1

            # is_token_valid marks token as needing refresh
            is_valid = token_manager.is_token_valid()
            assert is_valid is False
            assert token_manager._marked_needs_refresh is True

            # Second refresh should bypass cooldown due to _marked_needs_refresh
            result2 = await token_manager.refresh_token()
            assert result2 is False
            assert (
                refresh_attempts == 2
            ), "Cooldown should be bypassed when token expired"

    @pytest.mark.asyncio
    async def test_clock_skew_detection_warning(self, caplog):
        """Test that clock skew >1 hour triggers warning log."""
        initial_time = 1000000000
        # Token expires in 2 hours (valid)
        valid_time = initial_time + 7200
        mock_valid_jwt = {"exp": valid_time, "sub": "test_user"}

        current_time = initial_time

        def mock_time():
            return current_time

        # Patch time before creating TokenManager to avoid initial clock skew
        with patch(
            "custom_components.electrolux.util.jwt.decode",
            return_value=mock_valid_jwt,
        ), patch(
            "custom_components.electrolux.util.time.time", side_effect=mock_time
        ), caplog.at_level(
            "WARNING"
        ):
            token_manager = ElectroluxTokenManager(
                access_token="test_access",
                refresh_token="test_refresh",
                api_key="test_api_key",
            )

            # First check sets baseline
            is_valid1 = token_manager.is_token_valid()
            assert is_valid1 is True

            # Jump time forward by 2 hours (>1 hour threshold)
            current_time += 7200

            # Second check should detect clock skew
            token_manager.is_token_valid()

            # Check for clock skew warning in logs
            assert any(
                "Large time jump detected" in record.message
                for record in caplog.records
            ), "Clock skew warning should be logged"
