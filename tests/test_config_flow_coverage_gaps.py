"""Tests for config_flow coverage gaps.

These tests specifically target uncovered code paths in config_flow.py to achieve 100% coverage.
Coverage targets:
- Line 122: None return when credentials are missing
- Lines 438-453: Exception handling in _test_credentials (reauth)
- Lines 523-538: Exception handling in _test_credentials (options flow)
- Lines 577, 581, 585: Notification settings in reconfigure
- Lines 764-779: Exception handling in _test_credentials (reconfigure)
"""

from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest
from homeassistant import data_entry_flow

from custom_components.electrolux.config_flow import (
    ElectroluxRepairFlow,
    ElectroluxStatusFlowHandler,
    ElectroluxStatusOptionsFlowHandler,
    _validate_credentials_and_capture_rotation,
)
from custom_components.electrolux.const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_NOTIFICATION_DEFAULT,
    CONF_NOTIFICATION_DIAG,
    CONF_NOTIFICATION_WARNING,
    CONF_REFRESH_TOKEN,
)


class TestConfigFlowCoverageGaps:
    """Tests targeting uncovered code paths in config_flow."""

    # =====================================================================
    # Line 122: _validate_credentials_and_capture_rotation returns None
    # when credentials missing
    # =====================================================================

    @pytest.mark.asyncio
    async def test_validate_creds_returns_none_with_missing_api_key(self):
        """Test _validate_credentials_and_capture_rotation returns None when api_key is None."""
        result = await _validate_credentials_and_capture_rotation(
            None, "token", "refresh"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_creds_returns_none_with_missing_access_token(self):
        """Test returns None when access_token is None."""
        result = await _validate_credentials_and_capture_rotation(
            "key", None, "refresh"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_creds_returns_none_with_missing_refresh_token(self):
        """Test returns None when refresh_token is None."""
        result = await _validate_credentials_and_capture_rotation("key", "token", None)
        assert result is None

    # =====================================================================
    # Lines 438-453: Exception in ReauthFlowHandler._test_credentials
    # =====================================================================

    @pytest.mark.asyncio
    async def test_reauth_test_credentials_exception_returns_false(self):
        """Test reauth _test_credentials returns False on exception."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow._errors = {}

        with patch(
            "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
            new=AsyncMock(side_effect=Exception("API Error")),
        ):
            result = await flow._test_credentials("key", "token", "refresh")

        assert result is False

    # =====================================================================
    # Lines 523-538: Exception in OptionsFlowHandler._test_credentials
    # =====================================================================

    @pytest.mark.asyncio
    async def test_options_flow_test_credentials_exception_returns_false(self):
        """Test options flow _test_credentials returns False on exception."""
        mock_config_entry = Mock()
        mock_config_entry.entry_id = "test_entry"
        mock_config_entry.data = {CONF_API_KEY: "key"}

        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()

        with (
            patch.object(flow, "_config_entry", mock_config_entry, create=True),
            patch.object(flow, "_errors", {}, create=True),
            patch(
                "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
                new=AsyncMock(side_effect=Exception("API Error")),
            ),
        ):
            result = await flow._test_credentials("key", "token", "refresh")

        assert result is False

    # =====================================================================
    # Lines 577, 581, 585: Notification settings in reconfigure
    # =====================================================================

    @pytest.mark.asyncio
    async def test_reconfigure_with_all_notification_settings(self):
        """Test reconfigure step handles all three notification settings."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        flow.context = {"entry_id": "test_entry"}  # type: ignore[assignment]

        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {CONF_API_KEY: "old_key"}
        mock_entry.options = {}
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        user_input = {
            CONF_API_KEY: "new_api_key_1234567890",
            CONF_ACCESS_TOKEN: "new_access_token_1234567890",
            CONF_REFRESH_TOKEN: "new_refresh_token_1234567890",
            CONF_NOTIFICATION_DEFAULT: True,
            CONF_NOTIFICATION_WARNING: False,
            CONF_NOTIFICATION_DIAG: True,
        }

        with (
            patch.object(
                type(flow),
                "show_advanced_options",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
                new=AsyncMock(
                    return_value={
                        CONF_API_KEY: "new_api_key_1234567890",
                        CONF_ACCESS_TOKEN: "new_access_token",
                        CONF_REFRESH_TOKEN: "new_refresh_token",
                    }
                ),
            ),
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            patch("custom_components.electrolux.config_flow.ir.async_delete_issue"),
            patch.object(
                flow,
                "async_update_reload_and_abort",
                return_value={"type": "abort", "reason": "reconfigure_successful"},
            ) as mock_update,
        ):
            result = await flow.async_step_reconfigure(user_input)

        assert result["reason"] == "reconfigure_successful"  # type: ignore[typeddict-item]
        # Verify async_update_reload_and_abort was called with data containing notification settings
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        data = call_args[1]["data"]
        assert data[CONF_NOTIFICATION_DEFAULT] is True
        assert data[CONF_NOTIFICATION_WARNING] is False
        assert data[CONF_NOTIFICATION_DIAG] is True

    @pytest.mark.asyncio
    async def test_reconfigure_with_default_notification_only(self):
        """Test reconfigure with only CONF_NOTIFICATION_DEFAULT."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        flow.context = {"entry_id": "test_entry"}  # type: ignore[assignment]

        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {CONF_API_KEY: "old_key"}
        mock_entry.options = {}
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        user_input = {
            CONF_API_KEY: "new_api_key_1234567890",
            CONF_ACCESS_TOKEN: "new_access_token_1234567890",
            CONF_REFRESH_TOKEN: "new_refresh_token_1234567890",
            CONF_NOTIFICATION_DEFAULT: False,
        }

        with (
            patch.object(
                type(flow),
                "show_advanced_options",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
                new=AsyncMock(
                    return_value={
                        CONF_API_KEY: "new_api_key_1234567890",
                        CONF_ACCESS_TOKEN: "new_access_token",
                        CONF_REFRESH_TOKEN: "new_refresh_token",
                    }
                ),
            ),
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            patch("custom_components.electrolux.config_flow.ir.async_delete_issue"),
            patch.object(
                flow,
                "async_update_reload_and_abort",
                return_value={"type": "abort", "reason": "reconfigure_successful"},
            ),
        ):
            result = await flow.async_step_reconfigure(user_input)

        assert result["reason"] == "reconfigure_successful"  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_reconfigure_with_warning_notification_only(self):
        """Test reconfigure with only CONF_NOTIFICATION_WARNING."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        flow.context = {"entry_id": "test_entry"}  # type: ignore[assignment]

        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {CONF_API_KEY: "old_key"}
        mock_entry.options = {}
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        user_input = {
            CONF_API_KEY: "new_api_key_1234567890",
            CONF_ACCESS_TOKEN: "new_access_token_1234567890",
            CONF_REFRESH_TOKEN: "new_refresh_token_1234567890",
            CONF_NOTIFICATION_WARNING: True,
        }

        with (
            patch.object(
                type(flow),
                "show_advanced_options",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
                new=AsyncMock(
                    return_value={
                        CONF_API_KEY: "new_api_key_1234567890",
                        CONF_ACCESS_TOKEN: "new_access_token",
                        CONF_REFRESH_TOKEN: "new_refresh_token",
                    }
                ),
            ),
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            patch("custom_components.electrolux.config_flow.ir.async_delete_issue"),
            patch.object(
                flow,
                "async_update_reload_and_abort",
                return_value={"type": "abort", "reason": "reconfigure_successful"},
            ),
        ):
            result = await flow.async_step_reconfigure(user_input)

        assert result["reason"] == "reconfigure_successful"  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_reconfigure_with_diag_notification_only(self):
        """Test reconfigure with only CONF_NOTIFICATION_DIAG."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        flow.context = {"entry_id": "test_entry"}  # type: ignore[assignment]

        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {CONF_API_KEY: "old_key"}
        mock_entry.options = {}
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        user_input = {
            CONF_API_KEY: "new_api_key_1234567890",
            CONF_ACCESS_TOKEN: "new_access_token_1234567890",
            CONF_REFRESH_TOKEN: "new_refresh_token_1234567890",
            CONF_NOTIFICATION_DIAG: False,
        }

        with (
            patch.object(
                type(flow),
                "show_advanced_options",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
                new=AsyncMock(
                    return_value={
                        CONF_API_KEY: "new_api_key_1234567890",
                        CONF_ACCESS_TOKEN: "new_access_token",
                        CONF_REFRESH_TOKEN: "new_refresh_token",
                    }
                ),
            ),
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            patch("custom_components.electrolux.config_flow.ir.async_delete_issue"),
            patch.object(
                flow,
                "async_update_reload_and_abort",
                return_value={"type": "abort", "reason": "reconfigure_successful"},
            ),
        ):
            result = await flow.async_step_reconfigure(user_input)

        assert result["reason"] == "reconfigure_successful"  # type: ignore[typeddict-item]

    # =====================================================================
    # Lines 523-538, 577, 581, 585: Options flow with notification settings
    # =====================================================================

    @pytest.mark.asyncio
    async def test_options_flow_with_all_notifications(self):
        """Test options flow handles all notification settings."""
        mock_config_entry = Mock()
        mock_config_entry.entry_id = "test_entry"
        mock_config_entry.data = {CONF_API_KEY: "old_key"}
        mock_config_entry.options = {}

        flow = ElectroluxStatusOptionsFlowHandler(mock_config_entry)
        flow.hass = Mock()

        user_input = {
            CONF_API_KEY: "new_api_key_1234567890",
            CONF_ACCESS_TOKEN: "new_access_token_1234567890",
            CONF_REFRESH_TOKEN: "new_refresh_token_1234567890",
            CONF_NOTIFICATION_DEFAULT: True,
            CONF_NOTIFICATION_WARNING: False,
            CONF_NOTIFICATION_DIAG: True,
        }

        with (
            patch.object(flow, "_errors", {}, create=True),
            patch(
                "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
                new=AsyncMock(
                    return_value={
                        CONF_API_KEY: "new_api_key_1234567890",
                        CONF_ACCESS_TOKEN: "new_access_token",
                        CONF_REFRESH_TOKEN: "new_refresh_token",
                    }
                ),
            ),
        ):
            result = await flow._validate_and_update_options(user_input)

        # Should return an entry creation result
        assert result is not None
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY  # type: ignore[typeddict-item]
        # Verify async_update_entry was called with notifications
        flow.hass.config_entries.async_update_entry.assert_called_once()
        call_args = flow.hass.config_entries.async_update_entry.call_args
        updated_data = call_args[1]["data"]
        assert updated_data[CONF_NOTIFICATION_DEFAULT] is True
        assert updated_data[CONF_NOTIFICATION_WARNING] is False
        assert updated_data[CONF_NOTIFICATION_DIAG] is True

    @pytest.mark.asyncio
    async def test_options_flow_notification_exception(self):
        """Test options flow _test_credentials exception (lines 523-538)."""
        mock_config_entry = Mock()
        mock_config_entry.entry_id = "test_entry"
        mock_config_entry.data = {CONF_API_KEY: "old_key"}

        flow = ElectroluxStatusOptionsFlowHandler(mock_config_entry)
        flow.hass = Mock()

        with (
            patch.object(flow, "_errors", {}, create=True),
            patch(
                "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
                new=AsyncMock(side_effect=Exception("API Error")),
            ),
        ):
            result = await flow._test_credentials("key", "token", "refresh")

        assert result is False

    # =====================================================================
    # Lines 764-779: Exception in RepairFlow._test_credentials
    # =====================================================================

    @pytest.mark.asyncio
    async def test_repair_flow_test_credentials_exception_returns_false(self):
        """Test repair flow _test_credentials returns False on exception."""
        flow = ElectroluxRepairFlow("test_issue")
        flow.hass = Mock()

        with patch(
            "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
            new=AsyncMock(side_effect=Exception("API Error")),
        ):
            result = await flow._test_credentials("key", "token", "refresh")

        assert result is False
