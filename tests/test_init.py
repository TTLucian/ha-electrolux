"""Test the Electrolux integration setup."""

import asyncio
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.electrolux.const import DOMAIN, PLATFORMS


def test_domain():
    """Test that the domain is correct."""
    assert DOMAIN == "electrolux"


def test_platforms_defined():
    """Test that all expected platforms are defined."""
    expected_platforms = [
        "sensor",
        "binary_sensor",
        "switch",
        "number",
        "select",
        "button",
        "text",
        "climate",
        "fan",
    ]
    # Convert Platform enums to strings for comparison
    platform_strings = [str(p).split(".")[-1] for p in PLATFORMS]
    assert set(platform_strings) == set(expected_platforms)


class TestValidateConfig:
    """Test configuration validation."""

    def test_validate_config_missing_api_key(self):
        """Test that validation fails with missing API key."""
        from homeassistant.exceptions import ConfigEntryError

        from custom_components.electrolux import _validate_config

        mock_entry = MagicMock()
        mock_entry.data = {}

        with pytest.raises(ConfigEntryError, match="API key is required"):
            _validate_config(mock_entry)

    def test_validate_config_with_api_key(self):
        """Test that validation passes with API key."""
        from custom_components.electrolux import _validate_config

        mock_entry = MagicMock()
        mock_entry.data = {"api_key": "test_key"}

        # Should not raise
        _validate_config(mock_entry)


class TestMaskToken:
    """Test token masking for logging."""

    def test_mask_token_normal(self):
        """Test masking of normal length token."""
        from custom_components.electrolux import _mask_token

        token = "abcdefgh12345678"
        masked = _mask_token(token)
        assert masked == "abcd***5678"
        assert "efgh" not in masked
        assert "1234" not in masked

    def test_mask_token_short(self):
        """Test masking of short token."""
        from custom_components.electrolux import _mask_token

        token = "short"
        masked = _mask_token(token)
        assert masked == "***"

    def test_mask_token_none(self):
        """Test masking of None token."""
        from custom_components.electrolux import _mask_token

        masked = _mask_token(None)
        assert masked == "***"


class TestAsyncSetup:
    """Test async_setup function."""

    @pytest.mark.asyncio
    async def test_async_setup_returns_true(self):
        """Test that async_setup returns True (YAML not supported)."""
        from custom_components.electrolux import async_setup

        mock_hass = MagicMock(spec=HomeAssistant)
        result = await async_setup(mock_hass, {})
        assert result is True


# ---------------------------------------------------------------------------
# Helpers for async_setup_entry tests
# ---------------------------------------------------------------------------


def _make_mock_entry(data=None):
    """Return a minimal mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Test Electrolux"
    entry.data = (
        {
            "api_key": "test_api_key_12345",
            "access_token": "test_access_token_long",
            "refresh_token": "test_refresh_token_long",
        }
        if data is None
        else data
    )
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    return entry


def _make_mock_coordinator():
    """Return a minimal mock coordinator."""
    from unittest.mock import AsyncMock

    coord = MagicMock()
    coord.async_login = AsyncMock(return_value=True)
    coord.setup_entities = AsyncMock()
    coord.async_config_entry_first_refresh = AsyncMock()
    coord.last_update_success = True
    coord.platforms = []
    coord.data = {}
    coord._last_token_update = 0.0
    coord.listen_websocket = AsyncMock()
    coord.renew_websocket = AsyncMock()
    return coord


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    @pytest.mark.asyncio
    async def test_setup_entry_success(self):
        """Successful full setup returns True."""
        from unittest.mock import AsyncMock, patch

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = True
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        mock_hass.async_create_task = MagicMock(
            side_effect=lambda coro, **kw: (asyncio.iscoroutine(coro) and coro.close())
            or MagicMock()
        )

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
        ):
            result = await async_setup_entry(mock_hass, mock_entry)

        assert result is True
        mock_coordinator.async_login.assert_awaited_once()
        mock_coordinator.setup_entities.assert_awaited_once()
        mock_hass.config_entries.async_forward_entry_setups.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_setup_entry_auth_failure_raises_not_ready(self):
        """ConfigEntryAuthFailed from async_login is converted to ConfigEntryNotReady."""
        from unittest.mock import AsyncMock, patch

        from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = False

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()
        mock_coordinator.async_login = AsyncMock(
            side_effect=ConfigEntryAuthFailed("bad creds")
        )

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
            pytest.raises(ConfigEntryNotReady),
        ):
            await async_setup_entry(mock_hass, mock_entry)

    @pytest.mark.asyncio
    async def test_setup_entry_network_error_raises_not_ready(self):
        """ConfigEntryNotReady from async_login propagates unchanged."""
        from unittest.mock import AsyncMock, patch

        from homeassistant.exceptions import ConfigEntryNotReady

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = False

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()
        mock_coordinator.async_login = AsyncMock(
            side_effect=ConfigEntryNotReady("network down")
        )

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
            pytest.raises(ConfigEntryNotReady),
        ):
            await async_setup_entry(mock_hass, mock_entry)

    @pytest.mark.asyncio
    async def test_setup_entry_missing_api_key_raises(self):
        """Missing api_key raises ConfigEntryError before any network calls."""
        from homeassistant.exceptions import ConfigEntryError

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_entry = _make_mock_entry(data={})

        with pytest.raises(ConfigEntryError, match="API key is required"):
            await async_setup_entry(mock_hass, mock_entry)


# ---------------------------------------------------------------------------
# async_unload_entry
# ---------------------------------------------------------------------------


class TestAsyncUnloadEntry:
    @pytest.mark.asyncio
    async def test_unload_entry_success(self):
        """async_unload_entry closes client and unloads platforms."""
        from unittest.mock import AsyncMock

        from custom_components.electrolux import async_unload_entry

        mock_hass = MagicMock()
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        mock_client = MagicMock()
        mock_client.close = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.api = mock_client

        mock_entry = _make_mock_entry()
        mock_entry.runtime_data = mock_coordinator

        result = await async_unload_entry(mock_hass, mock_entry)

        assert result is True
        mock_client.close.assert_awaited_once()
        mock_hass.config_entries.async_unload_platforms.assert_awaited_once()


# ---------------------------------------------------------------------------
# update_listener
# ---------------------------------------------------------------------------


class TestUpdateListener:
    @pytest.mark.asyncio
    async def test_skips_reload_on_recent_token_update(self):
        """update_listener should skip reload if tokens were just refreshed."""
        import time

        from custom_components.electrolux import update_listener

        mock_hass = MagicMock()
        mock_coordinator = MagicMock()
        mock_coordinator._last_token_update = time.time()  # just now

        mock_entry = _make_mock_entry()
        mock_entry.runtime_data = mock_coordinator

        await update_listener(mock_hass, mock_entry)

        mock_hass.config_entries.async_reload.assert_not_called()

    @pytest.mark.asyncio
    async def test_reloads_when_options_changed(self):
        """update_listener should reload when last token update was long ago."""
        from unittest.mock import AsyncMock

        from custom_components.electrolux import update_listener

        mock_hass = MagicMock()
        mock_hass.config_entries.async_reload = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator._last_token_update = 0.0  # very old

        mock_entry = _make_mock_entry()
        mock_entry.runtime_data = mock_coordinator

        await update_listener(mock_hass, mock_entry)

        mock_hass.config_entries.async_reload.assert_awaited_once_with(
            mock_entry.entry_id
        )


class TestAsyncSetupEntryAdditional:
    """Tests for additional async_setup_entry paths (missed lines)."""

    @pytest.mark.asyncio
    async def test_setup_entry_with_token_expires_at(self):
        """Lines 90-96: when token_expires_at is set, expiry info is logged."""
        import asyncio
        import time
        from unittest.mock import AsyncMock, patch

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = True
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        mock_hass.async_create_task = MagicMock(
            side_effect=lambda coro, **kw: (asyncio.iscoroutine(coro) and coro.close())
            or MagicMock()
        )

        mock_entry = _make_mock_entry(
            data={
                "api_key": "test_api_key_12345",
                "access_token": "test_access_token_long",
                "refresh_token": "test_refresh_token_long",
                "token_expires_at": time.time() + 3600,
            }
        )
        mock_coordinator = _make_mock_coordinator()

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
        ):
            result = await async_setup_entry(mock_hass, mock_entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_setup_entry_login_returns_false_raises_not_ready(self):
        """Lines 130-133: async_login returns False → ConfigEntryNotReady."""
        from unittest.mock import AsyncMock, patch

        from homeassistant.exceptions import ConfigEntryNotReady

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = False

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()
        mock_coordinator.async_login = AsyncMock(return_value=False)

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
            pytest.raises(ConfigEntryNotReady),
        ):
            await async_setup_entry(mock_hass, mock_entry)

    @pytest.mark.asyncio
    async def test_setup_entry_first_refresh_timeout_continues(self):
        """Lines 177-183: TimeoutError from first refresh is caught → setup continues."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = True
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        mock_hass.async_create_task = MagicMock(
            side_effect=lambda coro, **kw: (asyncio.iscoroutine(coro) and coro.close())
            or MagicMock()
        )

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )
        mock_coordinator.last_update_success = True

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
        ):
            result = await async_setup_entry(mock_hass, mock_entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_setup_entry_last_update_failure_raises_not_ready(self):
        """Lines 186-189: last_update_success=False → ConfigEntryNotReady."""
        from unittest.mock import patch

        from homeassistant.exceptions import ConfigEntryNotReady

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = False

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()
        mock_coordinator.last_update_success = False

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
            pytest.raises(ConfigEntryNotReady),
        ):
            await async_setup_entry(mock_hass, mock_entry)

    @pytest.mark.asyncio
    async def test_setup_entry_ha_not_running_registers_started_listener(self):
        """Lines 261-264: hass.is_running=False → registers EVENT_HOMEASSISTANT_STARTED listener."""
        from unittest.mock import AsyncMock, patch

        from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = False
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
        ):
            result = await async_setup_entry(mock_hass, mock_entry)

        assert result is True
        # Check that async_listen_once was called with EVENT_HOMEASSISTANT_STARTED
        started_calls = [
            call
            for call in mock_hass.bus.async_listen_once.call_args_list
            if call[0][0] == EVENT_HOMEASSISTANT_STARTED
        ]
        assert len(started_calls) == 1

    @pytest.mark.asyncio
    async def test_setup_entry_cleanup_tasks_cancels_listen_and_renew(self):
        """Lines 236-247: cleanup_tasks() cancels listen_task and renew_task."""
        from unittest.mock import AsyncMock, patch

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = True
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        mock_hass.async_create_task = MagicMock(
            side_effect=lambda coro, **kw: (asyncio.iscoroutine(coro) and coro.close())
            or MagicMock()
        )

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()
        mock_listen_task = MagicMock()
        mock_renew_task = MagicMock()
        mock_coordinator.listen_task = mock_listen_task
        mock_coordinator.renew_task = mock_renew_task

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
        ):
            await async_setup_entry(mock_hass, mock_entry)

        # Find and invoke the cleanup_tasks function (synchronous callable registered with async_on_unload)
        import asyncio as _asyncio

        cleanup_fn = None
        for call in mock_entry.async_on_unload.call_args_list:
            fn = call[0][0]
            if callable(fn) and not _asyncio.iscoroutinefunction(fn):
                cleanup_fn = fn
                break

        assert (
            cleanup_fn is not None
        ), "cleanup_tasks not found in async_on_unload calls"
        cleanup_fn()

        mock_coordinator.listen_task.cancel.assert_called()
        mock_coordinator.renew_task.cancel.assert_called()

    @pytest.mark.asyncio
    async def test_setup_entry_close_coordinator_on_stop_event(self):
        """Lines 268-275: _close_coordinator closes websocket on HA stop."""
        from unittest.mock import AsyncMock, patch

        from homeassistant.const import EVENT_HOMEASSISTANT_STOP

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = True
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        mock_hass.async_create_task = MagicMock(
            side_effect=lambda coro, **kw: (asyncio.iscoroutine(coro) and coro.close())
            or MagicMock()
        )

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()
        mock_coordinator.close_websocket = AsyncMock()

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
        ):
            await async_setup_entry(mock_hass, mock_entry)

        # Find _close_coordinator callback registered for EVENT_HOMEASSISTANT_STOP
        stop_callback = None
        for call in mock_hass.bus.async_listen_once.call_args_list:
            if call[0][0] == EVENT_HOMEASSISTANT_STOP:
                stop_callback = call[0][1]
                break

        assert (
            stop_callback is not None
        ), "_close_coordinator not registered for STOP event"
        await stop_callback(None)
        mock_coordinator.close_websocket.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_setup_entry_close_coordinator_exception_swallowed(self):
        """Lines 274-275: exception in close_websocket is caught silently."""
        from unittest.mock import AsyncMock, patch

        from homeassistant.const import EVENT_HOMEASSISTANT_STOP

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = True
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        mock_hass.async_create_task = MagicMock(
            side_effect=lambda coro, **kw: (asyncio.iscoroutine(coro) and coro.close())
            or MagicMock()
        )

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()
        mock_coordinator.close_websocket = AsyncMock(
            side_effect=Exception("websocket close failed")
        )

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
        ):
            await async_setup_entry(mock_hass, mock_entry)

        stop_callback = None
        for call in mock_hass.bus.async_listen_once.call_args_list:
            if call[0][0] == EVENT_HOMEASSISTANT_STOP:
                stop_callback = call[0][1]
                break

        assert stop_callback is not None
        # Should NOT raise
        await stop_callback(None)

    @pytest.mark.asyncio
    async def test_setup_entry_background_task_creation_failure(self):
        """Lines 249-251: when async_create_task raises, exception re-raises."""
        from unittest.mock import AsyncMock, patch

        from custom_components.electrolux import async_setup_entry

        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.is_running = True
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

        def _create_task_fail(coro, **kw):
            if asyncio.iscoroutine(coro):
                coro.close()
            raise RuntimeError("task creation failed")

        mock_hass.async_create_task = MagicMock(side_effect=_create_task_fail)

        mock_entry = _make_mock_entry()
        mock_coordinator = _make_mock_coordinator()

        with (
            patch("custom_components.electrolux.async_get_clientsession"),
            patch(
                "custom_components.electrolux.get_electrolux_session",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.ElectroluxCoordinator",
                return_value=mock_coordinator,
            ),
            pytest.raises(RuntimeError, match="task creation failed"),
        ):
            await async_setup_entry(mock_hass, mock_entry)


class TestAsyncReloadEntry:
    """Tests for async_reload_entry."""

    @pytest.mark.asyncio
    async def test_async_reload_entry_calls_unload_then_setup(self):
        """Lines 334-336: async_reload_entry calls unload then setup."""
        from unittest.mock import AsyncMock, patch

        from custom_components.electrolux import async_reload_entry

        mock_hass = MagicMock()
        mock_entry = _make_mock_entry()

        with (
            patch(
                "custom_components.electrolux.async_unload_entry",
                new_callable=AsyncMock,
            ) as mock_unload,
            patch(
                "custom_components.electrolux.async_setup_entry",
                new_callable=AsyncMock,
            ) as mock_setup,
        ):
            await async_reload_entry(mock_hass, mock_entry)

        mock_unload.assert_awaited_once_with(mock_hass, mock_entry)
        mock_setup.assert_awaited_once_with(mock_hass, mock_entry)
