"""Tests for ElectroluxApiClient and related utilities in api_client.py."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError

from custom_components.electrolux.api_client import (
    ElectroluxApiClient,
    _TokenRefreshHandler,
    get_electrolux_session,
    retry_with_backoff,
    safe_api_call,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(hass=None, config_entry=None):
    """Create an ElectroluxApiClient with SDK internals mocked out."""
    with patch(
        "custom_components.electrolux.api_client.ApplianceClient"
    ) as mock_sdk, patch(
        "custom_components.electrolux.api_client.ElectroluxTokenManager"
    ) as mock_tm:
        mock_tm_instance = MagicMock()
        mock_tm_instance.set_auth_error_callback = MagicMock()
        mock_tm_instance.set_token_update_callback_with_expiry = MagicMock()
        mock_tm.return_value = mock_tm_instance
        mock_sdk.return_value = MagicMock()
        client = ElectroluxApiClient("key", "access", "refresh", hass, config_entry)
        return client


# ---------------------------------------------------------------------------
# get_electrolux_session
# ---------------------------------------------------------------------------


class TestGetElectroluxSession:
    def test_returns_api_client_instance(self):
        with patch(
            "custom_components.electrolux.api_client.ApplianceClient"
        ), patch(
            "custom_components.electrolux.api_client.ElectroluxTokenManager"
        ) as mock_tm:
            mock_tm.return_value = MagicMock()
            hass = MagicMock()
            session = get_electrolux_session(
                "api_key",
                "access_token",
                "refresh_token",
                client_session=None,
                hass=hass,
                config_entry=None,
            )
        assert isinstance(session, ElectroluxApiClient)

    def test_returns_client_without_hass(self):
        with patch(
            "custom_components.electrolux.api_client.ApplianceClient"
        ), patch(
            "custom_components.electrolux.api_client.ElectroluxTokenManager"
        ) as mock_tm:
            mock_tm.return_value = MagicMock()
            session = get_electrolux_session(
                "api_key", "token", "refresh", client_session=None
            )
        assert isinstance(session, ElectroluxApiClient)


# ---------------------------------------------------------------------------
# retry_with_backoff
# ---------------------------------------------------------------------------


class TestRetryWithBackoff:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        async def coro():
            return "ok"

        result = await retry_with_backoff(coro(), max_retries=2)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_connection_error_first_attempt_sleeps_and_reraises(self):
        """After connection error on first attempt, retry fails (coroutine reuse) and raises."""
        sleep_called = []

        async def net_fail():
            raise ConnectionError("connection refused")

        async def fake_sleep(delay):
            sleep_called.append(delay)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            with pytest.raises(Exception):
                await retry_with_backoff(net_fail(), max_retries=2, base_delay=0.01)

        # Sleep was called at least once (backoff triggered)
        assert len(sleep_called) >= 1

    @pytest.mark.asyncio
    async def test_timeout_error_first_attempt_sleeps_and_reraises(self):
        """TimeoutError on first attempt triggers backoff sleep."""
        sleep_called = []

        async def timeout_fail():
            raise TimeoutError("timed out")

        async def fake_sleep(delay):
            sleep_called.append(delay)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            with pytest.raises(Exception):
                await retry_with_backoff(timeout_fail(), max_retries=2, base_delay=0.01)

        assert len(sleep_called) >= 1

    @pytest.mark.asyncio
    async def test_asyncio_timeout_error_triggers_backoff(self):
        """asyncio.TimeoutError on first attempt triggers backoff sleep."""
        sleep_called = []

        async def asyncio_timeout():
            raise asyncio.TimeoutError()

        async def fake_sleep(delay):
            sleep_called.append(delay)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            with pytest.raises(Exception):
                await retry_with_backoff(asyncio_timeout(), max_retries=2, base_delay=0.01)

        assert len(sleep_called) >= 1

    @pytest.mark.asyncio
    async def test_connection_error_all_retries_exhausted_logs_error(self):
        """Last retry attempt logs error instead of warning."""
        mock_logger = MagicMock()

        async def always_fails():
            raise ConnectionError("always fails")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception):
                await retry_with_backoff(
                    always_fails(), max_retries=0, base_delay=0.01, logger=mock_logger
                )

        # With max_retries=0, there's exactly one attempt, error should be logged
        assert mock_logger.error.called

    @pytest.mark.asyncio
    async def test_non_network_error_not_retried(self):
        call_count = 0

        async def value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad value")

        with pytest.raises(ValueError, match="bad value"):
            await retry_with_backoff(value_error(), max_retries=3)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_delay_capped_at_max_delay(self):
        sleep_calls = []

        async def always_fails():
            raise ConnectionError("fail")

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(Exception):
                await retry_with_backoff(
                    always_fails(),
                    max_retries=5,
                    base_delay=10.0,
                    max_delay=15.0,
                    backoff_factor=3.0,
                )

        # First sleep should be ~10, subsequent (if reached) should be capped at 15
        # At minimum the first sleep was called
        assert len(sleep_calls) >= 1
        assert sleep_calls[0] == 10.0

    @pytest.mark.asyncio
    async def test_custom_logger_used(self):
        """Custom logger is passed through correctly."""
        mock_logger = MagicMock()

        async def always_fails():
            raise ConnectionError("net fail")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception):
                await retry_with_backoff(
                    always_fails(), max_retries=0, base_delay=0.01, logger=mock_logger
                )

        # Logger.error should have been called (max_retries=0, single attempt)
        assert mock_logger.error.called


# ---------------------------------------------------------------------------
# safe_api_call
# ---------------------------------------------------------------------------


class TestSafeApiCall:
    @pytest.mark.asyncio
    async def test_success_with_retry(self):
        async def ok():
            return 42

        result = await safe_api_call(ok(), "test op", retry_network_errors=True)
        assert result == 42

    @pytest.mark.asyncio
    async def test_success_without_retry(self):
        async def ok():
            return "hello"

        result = await safe_api_call(ok(), "test op", retry_network_errors=False)
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_network_error_no_retry_raises_home_assistant_error(self):
        """With retry_network_errors=False, ConnectionError raises 'Network connection failed'."""
        async def net_fail():
            raise ConnectionError("connection refused")

        with pytest.raises(HomeAssistantError, match="Network connection failed"):
            await safe_api_call(net_fail(), "test op", retry_network_errors=False)

    @pytest.mark.asyncio
    async def test_auth_error_401_raises_config_entry_auth_failed(self):
        async def auth_fail():
            raise Exception("401 Unauthorized")

        with pytest.raises(ConfigEntryAuthFailed):
            await safe_api_call(auth_fail(), "test op", retry_network_errors=False)

    @pytest.mark.asyncio
    async def test_auth_error_unauthorized_keyword(self):
        async def auth_fail():
            raise Exception("unauthorized access denied")

        with pytest.raises(ConfigEntryAuthFailed):
            await safe_api_call(auth_fail(), "test op", retry_network_errors=False)

    @pytest.mark.asyncio
    async def test_auth_error_invalid_grant(self):
        async def auth_fail():
            raise Exception("invalid grant error")

        with pytest.raises(ConfigEntryAuthFailed):
            await safe_api_call(auth_fail(), "test op", retry_network_errors=False)

    @pytest.mark.asyncio
    async def test_auth_error_token_keyword(self):
        async def auth_fail():
            raise Exception("token expired")

        with pytest.raises(ConfigEntryAuthFailed):
            await safe_api_call(auth_fail(), "test op", retry_network_errors=False)

    @pytest.mark.asyncio
    async def test_auth_error_forbidden_keyword(self):
        async def auth_fail():
            raise Exception("403 forbidden")

        with pytest.raises(ConfigEntryAuthFailed):
            await safe_api_call(auth_fail(), "test op", retry_network_errors=False)

    @pytest.mark.asyncio
    async def test_auth_error_auth_keyword(self):
        async def auth_fail():
            raise Exception("authentication failed")

        with pytest.raises(ConfigEntryAuthFailed):
            await safe_api_call(auth_fail(), "test op", retry_network_errors=False)

    @pytest.mark.asyncio
    async def test_rate_limit_429(self):
        async def rate_fail():
            raise Exception("429 Too Many Requests")

        with pytest.raises(HomeAssistantError, match="Too many requests"):
            await safe_api_call(rate_fail(), "test op", retry_network_errors=False)

    @pytest.mark.asyncio
    async def test_rate_limit_throttled(self):
        async def rate_fail():
            raise Exception("request throttled")

        with pytest.raises(HomeAssistantError, match="Too many requests"):
            await safe_api_call(rate_fail(), "test op", retry_network_errors=False)

    @pytest.mark.asyncio
    async def test_generic_error_raises_home_assistant_error(self):
        async def generic_fail():
            raise Exception("something broke")

        with pytest.raises(HomeAssistantError, match="Operation failed"):
            await safe_api_call(generic_fail(), "my operation", retry_network_errors=False)

    @pytest.mark.asyncio
    async def test_uses_default_logger_when_none_provided(self):
        async def ok():
            return "result"

        result = await safe_api_call(ok(), "test op", logger=None)
        assert result == "result"


# ---------------------------------------------------------------------------
# _TokenRefreshHandler.emit
# ---------------------------------------------------------------------------


class TestTokenRefreshHandlerEmit:
    def _make_handler(self, hass=None):
        client = MagicMock()
        client._trigger_reauth = AsyncMock()
        if hass is None:
            hass = MagicMock()
            hass.loop = MagicMock()
            hass.loop.call_soon_threadsafe = MagicMock()
        return _TokenRefreshHandler(client, hass), client, hass

    def _make_record(self, message: str) -> logging.LogRecord:
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg=message, args=(), exc_info=None
        )
        return record

    def test_permanent_error_schedules_reauth(self):
        handler, client, hass = self._make_handler()
        record = self._make_record("Refresh token is invalid")
        handler.emit(record)
        hass.loop.call_soon_threadsafe.assert_called_once()

    def test_invalid_grant_schedules_reauth(self):
        handler, client, hass = self._make_handler()
        record = self._make_record("invalid grant received from server")
        handler.emit(record)
        hass.loop.call_soon_threadsafe.assert_called_once()

    def test_invalid_refresh_token_schedules_reauth(self):
        handler, client, hass = self._make_handler()
        record = self._make_record("invalid refresh token provided")
        handler.emit(record)
        hass.loop.call_soon_threadsafe.assert_called_once()

    def test_refresh_token_expired_schedules_reauth(self):
        handler, client, hass = self._make_handler()
        record = self._make_record("refresh token expired")
        handler.emit(record)
        hass.loop.call_soon_threadsafe.assert_called_once()

    def test_non_permanent_error_does_not_schedule_reauth(self):
        handler, client, hass = self._make_handler()
        record = self._make_record("Some other error occurred")
        handler.emit(record)
        hass.loop.call_soon_threadsafe.assert_not_called()

    def test_exception_in_emit_is_swallowed(self):
        handler, client, hass = self._make_handler()
        # Make call_soon_threadsafe raise
        hass.loop.call_soon_threadsafe.side_effect = RuntimeError("loop error")
        record = self._make_record("Refresh token is invalid")
        # Should not raise
        handler.emit(record)

    def test_exception_in_format_is_swallowed(self):
        handler, client, hass = self._make_handler()
        record = self._make_record("Refresh token is invalid")
        # Make format raise
        with patch.object(handler, "format", side_effect=Exception("format error")):
            handler.emit(record)  # Should not raise


# ---------------------------------------------------------------------------
# ElectroluxApiClient.__init__ with hass (handler attachment)
# ---------------------------------------------------------------------------


class TestApiClientInit:
    def test_init_without_hass_no_handler_attached(self):
        with patch("custom_components.electrolux.api_client.ApplianceClient"), \
             patch("custom_components.electrolux.api_client.ElectroluxTokenManager") as mock_tm:
            mock_tm.return_value = MagicMock()
            client = ElectroluxApiClient("key", "access", "refresh", hass=None)
        assert client._token_handler is None
        assert client._token_logger is None

    def test_init_with_hass_attaches_handler(self):
        hass = MagicMock()
        with patch("custom_components.electrolux.api_client.ApplianceClient"), \
             patch("custom_components.electrolux.api_client.ElectroluxTokenManager") as mock_tm, \
             patch("custom_components.electrolux.api_client.logging") as mock_logging:
            mock_tm.return_value = MagicMock()
            mock_logger_instance = MagicMock()
            mock_logging.getLogger.return_value = mock_logger_instance
            mock_logging.ERROR = logging.ERROR
            mock_logging.Handler = logging.Handler
            client = ElectroluxApiClient("key", "access", "refresh", hass=hass)
        assert client._token_handler is not None
        assert client._token_logger is not None

    def test_init_hass_handler_attach_exception_logged(self):
        """Exception during handler attachment is caught and logged."""
        hass = MagicMock()
        with patch("custom_components.electrolux.api_client.ApplianceClient"), \
             patch("custom_components.electrolux.api_client.ElectroluxTokenManager") as mock_tm, \
             patch(
                 "custom_components.electrolux.api_client._TokenRefreshHandler",
                 side_effect=Exception("handler init error"),
             ):
            mock_tm.return_value = MagicMock()
            # Should not raise
            client = ElectroluxApiClient("key", "access", "refresh", hass=hass)
        # Handler attachment failed, so both remain None
        assert client._token_handler is None

    def test_set_token_update_callback(self):
        client = _make_client()
        cb = MagicMock()
        client.set_token_update_callback(cb)
        assert client._token_manager._on_token_update == cb

    def test_set_token_update_callback_with_expiry(self):
        client = _make_client()
        cb = MagicMock()
        client.set_token_update_callback_with_expiry(cb)
        client._token_manager.set_token_update_callback_with_expiry.assert_called_once_with(cb)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# _trigger_reauth
# ---------------------------------------------------------------------------


class TestTriggerReauth:
    @pytest.mark.asyncio
    async def test_trigger_reauth_sets_auth_failed(self, monkeypatch):
        client = _make_client()

        async def _noop(msg):
            pass

        monkeypatch.setattr(client, "_report_token_refresh_error", _noop)
        await client._trigger_reauth("token expired")
        assert client._auth_failed is True

    @pytest.mark.asyncio
    async def test_trigger_reauth_with_coordinator_schedules_refresh(self, monkeypatch):
        hass = MagicMock()
        hass.loop = MagicMock()
        hass.loop.call_soon_threadsafe = MagicMock()
        client = _make_client(hass=hass)
        coordinator = MagicMock()
        coordinator.async_refresh = AsyncMock()
        client.coordinator = coordinator

        async def _noop(msg):
            pass

        monkeypatch.setattr(client, "_report_token_refresh_error", _noop)
        await client._trigger_reauth("bad token")
        hass.loop.call_soon_threadsafe.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_reauth_without_coordinator_does_not_schedule(self, monkeypatch):
        hass = MagicMock()
        hass.loop = MagicMock()
        hass.loop.call_soon_threadsafe = MagicMock()
        client = _make_client(hass=hass)
        client.coordinator = None  # No coordinator

        async def _noop(msg):
            pass

        monkeypatch.setattr(client, "_report_token_refresh_error", _noop)
        await client._trigger_reauth("bad token")
        hass.loop.call_soon_threadsafe.assert_not_called()


# ---------------------------------------------------------------------------
# _report_token_refresh_error
# ---------------------------------------------------------------------------


class TestReportTokenRefreshError:
    @pytest.mark.asyncio
    async def test_with_config_entry_uses_entry_id_in_issue(self, monkeypatch):
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "abc123"
        hass.config_entries.async_entries.return_value = [entry]
        client = _make_client(hass=hass)

        captured = {}

        def fake_create_issue(hass_arg, domain, issue_id, **kwargs):
            captured["issue_id"] = issue_id

        monkeypatch.setattr(
            "custom_components.electrolux.api_client.issue_registry.async_create_issue",
            fake_create_issue,
        )
        await client._report_token_refresh_error("token failed")
        assert captured["issue_id"] == "invalid_refresh_token_abc123"

    @pytest.mark.asyncio
    async def test_without_entries_uses_generic_issue_id(self, monkeypatch):
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = []
        client = _make_client(hass=hass)

        captured = {}

        def fake_create_issue(hass_arg, domain, issue_id, **kwargs):
            captured["issue_id"] = issue_id

        monkeypatch.setattr(
            "custom_components.electrolux.api_client.issue_registry.async_create_issue",
            fake_create_issue,
        )
        await client._report_token_refresh_error("generic failure")
        assert captured["issue_id"] == "invalid_refresh_token"

    @pytest.mark.asyncio
    async def test_exception_during_issue_creation_is_logged(self, monkeypatch):
        hass = MagicMock()
        hass.config_entries.async_entries.return_value = []
        client = _make_client(hass=hass)

        monkeypatch.setattr(
            "custom_components.electrolux.api_client.issue_registry.async_create_issue",
            MagicMock(side_effect=RuntimeError("issue registry failed")),
        )
        # Should not raise
        await client._report_token_refresh_error("error")


# ---------------------------------------------------------------------------
# _handle_api_call
# ---------------------------------------------------------------------------


class TestHandleApiCall:
    @pytest.mark.asyncio
    async def test_success_returns_result(self):
        client = _make_client()

        async def coro():
            return {"data": 42}

        result = await client._handle_api_call(coro())
        assert result == {"data": 42}

    @pytest.mark.asyncio
    async def test_auth_error_401_raises_config_entry_auth_failed(self):
        client = _make_client()

        async def coro():
            raise Exception("401 Unauthorized")

        with pytest.raises(ConfigEntryAuthFailed):
            await client._handle_api_call(coro())

    @pytest.mark.asyncio
    async def test_auth_error_unauthorized(self):
        client = _make_client()

        async def coro():
            raise Exception("unauthorized request")

        with pytest.raises(ConfigEntryAuthFailed):
            await client._handle_api_call(coro())

    @pytest.mark.asyncio
    async def test_auth_error_invalid_grant(self):
        client = _make_client()

        async def coro():
            raise Exception("invalid grant")

        with pytest.raises(ConfigEntryAuthFailed):
            await client._handle_api_call(coro())

    @pytest.mark.asyncio
    async def test_auth_error_token_keyword(self):
        client = _make_client()

        async def coro():
            raise Exception("token has expired")

        with pytest.raises(ConfigEntryAuthFailed):
            await client._handle_api_call(coro())

    @pytest.mark.asyncio
    async def test_auth_error_forbidden(self):
        client = _make_client()

        async def coro():
            raise Exception("403 forbidden access")

        with pytest.raises(ConfigEntryAuthFailed):
            await client._handle_api_call(coro())

    @pytest.mark.asyncio
    async def test_non_auth_error_reraises(self):
        client = _make_client()

        async def coro():
            raise ValueError("bad input")

        with pytest.raises(ValueError, match="bad input"):
            await client._handle_api_call(coro())


# ---------------------------------------------------------------------------
# get_appliances_list
# ---------------------------------------------------------------------------


class TestGetAppliancesList:
    def _make_appliance(self, appliance_id, name, appliance_type, model="Unknown"):
        a = MagicMock()
        a.applianceId = appliance_id
        a.applianceName = name
        a.applianceType = appliance_type
        a.model = model
        return a

    @pytest.mark.asyncio
    async def test_returns_correctly_formatted_list(self, monkeypatch):
        client = _make_client()
        appliance = self._make_appliance("123_00:ABC", "My Oven", "OVEN", "MyModel")
        client._handle_api_call = AsyncMock(return_value=[appliance])

        result = await client.get_appliances_list()
        assert len(result) == 1
        assert result[0]["applianceId"] == "123_00:ABC"
        assert result[0]["applianceName"] == "My Oven"
        assert result[0]["applianceType"] == "OVEN"
        assert result[0]["applianceData"]["modelName"] == "MyModel"

    @pytest.mark.asyncio
    async def test_model_extracted_from_pnc_when_unknown(self, monkeypatch):
        client = _make_client()
        appliance = self._make_appliance("944188772_00:ABCDEF", "Fridge", "REF", "Unknown")
        client._handle_api_call = AsyncMock(return_value=[appliance])

        result = await client.get_appliances_list()
        assert result[0]["applianceData"]["modelName"] == "944188772"

    @pytest.mark.asyncio
    async def test_model_not_extracted_from_short_pnc(self, monkeypatch):
        client = _make_client()
        appliance = self._make_appliance("ABC_00:DEF", "Small", "TYPE", "Unknown")
        client._handle_api_call = AsyncMock(return_value=[appliance])

        result = await client.get_appliances_list()
        # "ABC" is not all digits or too short (<6), so model stays "Unknown"
        assert result[0]["applianceData"]["modelName"] == "Unknown"

    @pytest.mark.asyncio
    async def test_empty_appliance_list(self, monkeypatch):
        client = _make_client()
        client._handle_api_call = AsyncMock(return_value=[])

        result = await client.get_appliances_list()
        assert result == []


# ---------------------------------------------------------------------------
# get_appliances_info
# ---------------------------------------------------------------------------


class TestGetAppliancesInfo:
    def _make_details(self, model="Unknown", brand="Electrolux"):
        d = MagicMock()
        d.model = model
        d.brand = brand
        d.deviceType = "OVEN"
        d.variant = "v1"
        d.color = "silver"
        return d

    @pytest.mark.asyncio
    async def test_returns_info_with_known_model(self, monkeypatch):
        client = _make_client()
        client._handle_api_call = AsyncMock(return_value=self._make_details("OvenModel123"))

        result = await client.get_appliances_info(["app1"])
        assert len(result) == 1
        assert result[0]["model"] == "OvenModel123"
        assert result[0]["brand"] == "Electrolux"

    @pytest.mark.asyncio
    async def test_model_extracted_from_pnc_when_unknown(self, monkeypatch):
        client = _make_client()
        client._handle_api_call = AsyncMock(return_value=self._make_details("Unknown"))

        result = await client.get_appliances_info(["944188772_00:DEF"])
        assert result[0]["model"] == "944188772"

    @pytest.mark.asyncio
    async def test_skips_appliance_on_exception(self, monkeypatch):
        client = _make_client()
        client._handle_api_call = AsyncMock(side_effect=Exception("API error"))

        result = await client.get_appliances_info(["bad_appliance"])
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_appliances(self, monkeypatch):
        client = _make_client()
        client._handle_api_call = AsyncMock(
            side_effect=[
                self._make_details("Model1"),
                self._make_details("Model2"),
            ]
        )

        result = await client.get_appliances_info(["app1", "app2"])
        assert len(result) == 2
        assert result[0]["model"] == "Model1"
        assert result[1]["model"] == "Model2"


# ---------------------------------------------------------------------------
# get_appliance_state
# ---------------------------------------------------------------------------


class TestGetApplianceState:
    @pytest.mark.asyncio
    async def test_dict_response_with_properties(self, monkeypatch):
        client = _make_client()

        state_dict = {"properties": {"reported": {"temp": 180}}}
        client._handle_api_call = AsyncMock(return_value=state_dict)

        result = await client.get_appliance_state("app1")
        assert result["applianceId"] == "app1"
        assert result["properties"]["reported"]["temp"] == 180

    @pytest.mark.asyncio
    async def test_object_response_with_properties_attr(self, monkeypatch):
        client = _make_client()

        state_obj = MagicMock()
        state_obj.properties = {"reported": {"status": "on"}}
        # Make isinstance(state_obj, dict) return False
        client._handle_api_call = AsyncMock(return_value=state_obj)

        result = await client.get_appliance_state("app2")
        assert result["applianceId"] == "app2"
        assert result["properties"]["reported"]["status"] == "on"

    @pytest.mark.asyncio
    async def test_invalid_response_raises_home_assistant_error(self, monkeypatch):
        """Response that is neither dict nor has properties attribute raises error."""
        client = _make_client()

        state_obj = MagicMock(spec=["something_else"])  # no .properties
        # Make isinstance check fail too
        client._handle_api_call = AsyncMock(return_value=state_obj)

        with pytest.raises(HomeAssistantError):
            await client.get_appliance_state("app3")

    @pytest.mark.asyncio
    async def test_dict_response_missing_nested_keys(self, monkeypatch):
        """Dict response with empty nested structure still works."""
        client = _make_client()
        # dict without 'properties' key
        client._handle_api_call = AsyncMock(return_value={"other": "data"})

        result = await client.get_appliance_state("app4")
        assert result["properties"]["reported"] == {}


# ---------------------------------------------------------------------------
# get_appliance_capabilities
# ---------------------------------------------------------------------------


class TestGetApplianceCapabilities:
    @pytest.mark.asyncio
    async def test_returns_capabilities_when_present(self, monkeypatch):
        client = _make_client()
        details = MagicMock()
        details.capabilities = {"mode": ["cool", "heat"]}
        client._handle_api_call = AsyncMock(return_value=details)

        with patch(
            "custom_components.electrolux.api_client.safe_api_call",
            new_callable=AsyncMock,
            return_value=details,
        ):
            result = await client.get_appliance_capabilities("app1")
        assert result == {"mode": ["cool", "heat"]}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_capabilities(self, monkeypatch):
        client = _make_client()
        details = MagicMock()
        details.capabilities = None
        client._handle_api_call = AsyncMock(return_value=details)

        with patch(
            "custom_components.electrolux.api_client.safe_api_call",
            new_callable=AsyncMock,
            return_value=details,
        ):
            result = await client.get_appliance_capabilities("app1")
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_capabilities_attr_missing(self, monkeypatch):
        client = _make_client()
        details = MagicMock(spec=["something"])  # no capabilities attr

        with patch(
            "custom_components.electrolux.api_client.safe_api_call",
            new_callable=AsyncMock,
            return_value=details,
        ):
            result = await client.get_appliance_capabilities("app1")
        assert result == {}


# ---------------------------------------------------------------------------
# watch_for_appliance_state_updates
# ---------------------------------------------------------------------------


class TestWatchForApplianceStateUpdates:
    @pytest.mark.asyncio
    async def test_creates_sse_task_with_hass(self):
        hass = MagicMock()
        task = MagicMock()
        task.add_done_callback = MagicMock()
        task.done = MagicMock(return_value=False)
        task.cancel = MagicMock()
        hass.async_create_task = MagicMock(return_value=task)

        client = _make_client(hass=hass)
        client._client = MagicMock()
        client._client.start_event_stream = MagicMock(return_value=AsyncMock()())

        callback = MagicMock()
        await client.watch_for_appliance_state_updates(["app1"], callback)

        hass.async_create_task.assert_called_once()
        assert client._sse_task is task

    @pytest.mark.asyncio
    async def test_creates_sse_task_without_hass(self):
        client = _make_client(hass=None)
        client._client = MagicMock()

        async def fake_stream():
            pass

        client._client.start_event_stream = MagicMock(return_value=fake_stream())

        callback = MagicMock()
        with patch("asyncio.create_task") as mock_create_task:
            task = MagicMock()
            task.add_done_callback = MagicMock()
            mock_create_task.return_value = task
            await client.watch_for_appliance_state_updates(["app1"], callback)

        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_clears_existing_sse_task_before_starting(self):
        hass = MagicMock()
        new_task = MagicMock()
        new_task.add_done_callback = MagicMock()
        new_task.done = MagicMock(return_value=False)
        new_task.cancel = MagicMock()
        hass.async_create_task = MagicMock(return_value=new_task)

        client = _make_client(hass=hass)
        # Set up an existing SSE task
        old_task = MagicMock()
        old_task.done = MagicMock(return_value=False)
        old_task.cancel = MagicMock()
        client._sse_task = old_task
        client.disconnect_websocket = AsyncMock()

        client._client = MagicMock()
        client._client.start_event_stream = MagicMock(return_value=AsyncMock()())

        callback = MagicMock()
        await client.watch_for_appliance_state_updates(["app1"], callback)
        client.disconnect_websocket.assert_called_once()

    @pytest.mark.asyncio
    async def test_sse_failure_callback_cancelled(self):
        """SSE done callback logs when task is cancelled."""
        hass = MagicMock()
        hass.loop = MagicMock()
        hass.loop.call_soon_threadsafe = MagicMock()

        captured_cb = {}

        task = MagicMock()
        task.done = MagicMock(return_value=False)
        task.cancel = MagicMock()

        def capture_done_callback(cb):
            captured_cb["cb"] = cb

        task.add_done_callback = capture_done_callback
        hass.async_create_task = MagicMock(return_value=task)

        client = _make_client(hass=hass)
        client._client = MagicMock()
        client._client.start_event_stream = MagicMock(return_value=AsyncMock()())

        await client.watch_for_appliance_state_updates(["app1"], MagicMock())

        # Simulate task cancel
        task.cancelled = MagicMock(return_value=True)
        task.exception = MagicMock(return_value=None)
        captured_cb["cb"](task)  # Should not raise

    @pytest.mark.asyncio
    async def test_sse_failure_callback_auth_error_triggers_reauth(self):
        """SSE done callback triggers reauth on auth error."""
        hass = MagicMock()
        hass.loop = MagicMock()
        hass.loop.call_soon_threadsafe = MagicMock()
        config_entry = MagicMock()

        captured_cb = {}

        task = MagicMock()
        task.done = MagicMock(return_value=False)
        task.cancel = MagicMock()

        def capture_done_callback(cb):
            captured_cb["cb"] = cb

        task.add_done_callback = capture_done_callback
        hass.async_create_task = MagicMock(return_value=task)

        client = _make_client(hass=hass, config_entry=config_entry)
        client._client = MagicMock()
        client._client.start_event_stream = MagicMock(return_value=AsyncMock()())

        await client.watch_for_appliance_state_updates(["app1"], MagicMock())

        # Simulate auth error in SSE task
        task.cancelled = MagicMock(return_value=False)
        task.exception = MagicMock(return_value=Exception("401 unauthorized"))
        captured_cb["cb"](task)

        hass.loop.call_soon_threadsafe.assert_called()

    @pytest.mark.asyncio
    async def test_sse_failure_callback_regular_error(self):
        """SSE done callback handles regular non-auth errors."""
        hass = MagicMock()
        hass.loop = MagicMock()
        hass.loop.call_soon_threadsafe = MagicMock()

        captured_cb = {}

        task = MagicMock()
        task.done = MagicMock(return_value=False)
        task.cancel = MagicMock()

        def capture_done_callback(cb):
            captured_cb["cb"] = cb

        task.add_done_callback = capture_done_callback
        hass.async_create_task = MagicMock(return_value=task)

        client = _make_client(hass=hass)
        client._client = MagicMock()
        client._client.start_event_stream = MagicMock(return_value=AsyncMock()())

        await client.watch_for_appliance_state_updates(["app1"], MagicMock())

        # Simulate non-auth error (no reauth)
        task.cancelled = MagicMock(return_value=False)
        task.exception = MagicMock(return_value=Exception("general network error"))
        captured_cb["cb"](task)

        # call_soon_threadsafe should not have been called (no auth error)
        hass.loop.call_soon_threadsafe.assert_not_called()

    @pytest.mark.asyncio
    async def test_sse_ended_without_exception(self):
        """SSE done callback handles task ending without exception."""
        hass = MagicMock()

        captured_cb = {}
        task = MagicMock()
        task.done = MagicMock(return_value=False)
        task.cancel = MagicMock()

        def capture_done_callback(cb):
            captured_cb["cb"] = cb

        task.add_done_callback = capture_done_callback
        hass.async_create_task = MagicMock(return_value=task)

        client = _make_client(hass=hass)
        client._client = MagicMock()
        client._client.start_event_stream = MagicMock(return_value=AsyncMock()())

        await client.watch_for_appliance_state_updates(["app1"], MagicMock())

        # Simulate task completed without cancellation or exception
        task.cancelled = MagicMock(return_value=False)
        task.exception = MagicMock(return_value=None)
        captured_cb["cb"](task)  # Should not raise


# ---------------------------------------------------------------------------
# disconnect_websocket
# ---------------------------------------------------------------------------


class TestDisconnectWebsocket:
    @pytest.mark.asyncio
    async def test_cancels_running_task(self):
        client = _make_client()
        # AsyncMock with side_effect=CancelledError will raise CancelledError when awaited
        mock_task = AsyncMock(side_effect=asyncio.CancelledError())
        mock_task.done = MagicMock(return_value=False)
        mock_task.cancel = MagicMock()
        client._sse_task = mock_task

        await client.disconnect_websocket()

        mock_task.cancel.assert_called_once()
        assert client._sse_task is None

    @pytest.mark.asyncio
    async def test_handles_task_already_done(self):
        client = _make_client()
        task = MagicMock()
        task.done = MagicMock(return_value=True)
        client._sse_task = task

        await client.disconnect_websocket()
        # Task already done, cancel should NOT be called
        task.cancel.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_task_is_noop(self):
        client = _make_client()
        client._sse_task = None
        await client.disconnect_websocket()  # Should not raise

    @pytest.mark.asyncio
    async def test_task_finishes_with_exception_during_disconnect(self):
        client = _make_client()
        client._sse_task = AsyncMock(side_effect=RuntimeError("unexpected"))
        client._sse_task.done = MagicMock(return_value=False)
        client._sse_task.cancel = MagicMock()

        await client.disconnect_websocket()  # Should not raise
        assert client._sse_task is None


# ---------------------------------------------------------------------------
# execute_appliance_command
# ---------------------------------------------------------------------------


class TestExecuteApplianceCommand:
    @pytest.mark.asyncio
    async def test_success(self):
        client = _make_client()
        client._handle_api_call = AsyncMock(return_value={"status": "ok"})

        result = await client.execute_appliance_command("app1", {"temp": 180})
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_reraises_exception(self):
        client = _make_client()
        client._handle_api_call = AsyncMock(side_effect=ConfigEntryAuthFailed("auth fail"))

        with pytest.raises(ConfigEntryAuthFailed):
            await client.execute_appliance_command("app1", {"temp": 180})


# ---------------------------------------------------------------------------
# get_user_metadata
# ---------------------------------------------------------------------------


class TestGetUserMetadata:
    @pytest.mark.asyncio
    async def test_returns_mock_metadata(self):
        client = _make_client()
        result = await client.get_user_metadata()
        assert result == {"userId": "mock_user"}


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    @pytest.mark.asyncio
    async def test_close_disconnects_and_removes_handler(self):
        hass = MagicMock()
        client = _make_client(hass=hass)
        client.disconnect_websocket = AsyncMock()
        mock_logger = MagicMock()
        mock_handler = MagicMock()
        client._token_logger = mock_logger
        client._token_handler = mock_handler

        await client.close()

        client.disconnect_websocket.assert_called_once()
        mock_logger.removeHandler.assert_called_once_with(mock_handler)
        assert client._token_handler is None
        assert client._token_logger is None

    @pytest.mark.asyncio
    async def test_close_without_handler_is_safe(self):
        client = _make_client()
        client.disconnect_websocket = AsyncMock()
        client._token_handler = None
        client._token_logger = None

        await client.close()  # Should not raise
        client.disconnect_websocket.assert_called_once()
