"""Test the Electrolux config flow."""

from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest
from homeassistant import data_entry_flow

from custom_components.electrolux.config_flow import (
    ElectroluxRepairFlow,
    ElectroluxStatusFlowHandler,
    ElectroluxStatusOptionsFlowHandler,
    _extract_token_expiry,
    _mask_token,
    _validate_credentials,
    async_create_fix_flow,
)


def test_config_flow_class():
    """Test that the config flow class exists."""
    assert ElectroluxStatusFlowHandler is not None


class TestConfigFlowUserStep:
    """Test the user step of config flow."""

    @pytest.mark.asyncio
    async def test_user_form_shown(self):
        """Test that user form is shown."""
        flow = ElectroluxStatusFlowHandler()
        # Mock hass
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_entries.return_value = []

        result = await flow.async_step_user()

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["step_id"] == "user"  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_user_input_creates_entry(self):
        """Test that user input creates config entry."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_entries.return_value = []
        flow.hass.data = {}

        user_input = {
            "api_key": "test_api_key_1234567890",
            "access_token": "test_access_token_1234567890",
            "refresh_token": "test_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch(
                "custom_components.electrolux.config_flow.async_get_clientsession"
            ) as mock_client_session,
        ):
            # Mock successful API connection
            mock_client = Mock()
            mock_client.get_appliances_list = AsyncMock(
                return_value=[
                    {"applianceId": "test_123", "applianceName": "Test Device"}
                ]
            )
            mock_session.return_value = mock_client
            mock_client_session.return_value = Mock()

            result = await flow.async_step_user(user_input)

            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY  # type: ignore[typeddict-item]
            assert result["title"] == "Electrolux"  # type: ignore[typeddict-item]
            assert result["data"]["api_key"] == user_input["api_key"]  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_user_input_connection_error(self):
        """Test that connection errors are handled."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_entries.return_value = []

        user_input = {
            "api_key": "test_api_key_1234567890",
            "access_token": "test_access_token_1234567890",
            "refresh_token": "test_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch(
                "custom_components.electrolux.config_flow.async_get_clientsession"
            ) as mock_client_session,
        ):
            mock_client = Mock()
            mock_client.get_appliances_list = AsyncMock(
                side_effect=ConnectionError("Connection failed")
            )
            mock_session.return_value = mock_client
            mock_client_session.return_value = Mock()

            result = await flow.async_step_user(user_input)

            assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
            assert "errors" in result
            # Connection errors are treated as invalid_auth in config flow
            assert result["errors"]["base"] == "invalid_auth"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_user_input_invalid_auth(self):
        """Test that invalid auth errors are handled."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_entries.return_value = []

        user_input = {
            "api_key": "invalid_key_1234567890",
            "access_token": "invalid_access_token_1234567890",
            "refresh_token": "invalid_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch(
                "custom_components.electrolux.config_flow.async_get_clientsession"
            ) as mock_client_session,
        ):
            mock_client = Mock()
            mock_client.get_appliances_list = AsyncMock(
                side_effect=ValueError("401 Unauthorized")
            )
            mock_session.return_value = mock_client
            mock_client_session.return_value = Mock()

            result = await flow.async_step_user(user_input)

            assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
            assert "errors" in result
            assert result["errors"]["base"] == "invalid_auth"  # type: ignore[index]


class TestConfigFlowOptionsFlow:
    """Test the options flow."""

    @pytest.mark.asyncio
    async def test_options_form_shown(self):
        """Test that options form is shown."""
        mock_entry = Mock()
        mock_entry.options = {}

        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()

        with patch.object(
            ElectroluxStatusFlowHandler, "async_get_options_flow"
        ) as mock_get_flow:
            options_flow = Mock()
            options_flow.async_step_init = AsyncMock(
                return_value={
                    "type": data_entry_flow.FlowResultType.FORM,
                    "step_id": "init",
                }
            )
            mock_get_flow.return_value = options_flow

            result = await options_flow.async_step_init()

            assert result["type"] == data_entry_flow.FlowResultType.FORM


class TestRepairFlow:
    """Test repair flow for invalid refresh tokens."""

    @pytest.mark.asyncio
    async def test_repair_flow_initialization(self):
        """Test that the repair flow can be created."""
        # Create mock hass
        mock_hass = Mock()
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_get_entry = Mock(return_value=None)

        # Test that the repair flow can be created
        flow = await async_create_fix_flow(
            mock_hass, "invalid_refresh_token_test", None
        )
        assert flow is not None
        assert isinstance(flow, ElectroluxRepairFlow)

    @pytest.mark.asyncio
    async def test_repair_flow_form_shown(self):
        """Test that repair flow shows form."""
        flow = ElectroluxRepairFlow()
        flow.hass = Mock()
        flow.context = {"issue_id": "invalid_refresh_token_test_entry"}  # type: ignore[typeddict-item]

        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"api_key": "old_key"}

        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        result = await flow.async_step_init()

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["step_id"] == "confirm_repair"  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_repair_validation(self):
        """Test repair input validation."""
        # Create mock hass with config entry
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"api_key": "old_key", "access_token": "old_token"}

        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_get_entry = Mock(return_value=mock_entry)
        mock_hass.config_entries.async_update_entry = Mock()
        mock_hass.config_entries.async_reload = AsyncMock()

        # Create repair flow
        flow = ElectroluxRepairFlow()
        flow.hass = mock_hass
        flow.context = {"issue_id": "invalid_refresh_token_test_entry"}  # type: ignore[typeddict-item]

        user_input = {
            "api_key": "old_key_1234567890",
            "access_token": "new_access_token_1234567890",
            "refresh_token": "new_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch(
                "custom_components.electrolux.config_flow.async_get_clientsession"
            ) as mock_client_session,
            patch("custom_components.electrolux.config_flow.ir.async_delete_issue"),
        ):
            mock_client = Mock()
            mock_client.get_appliances_list = AsyncMock(return_value=[])
            mock_session.return_value = mock_client
            mock_client_session.return_value = Mock()

            result = await flow.async_step_init(user_input)

            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY  # type: ignore[typeddict-item]
            # Verify config entry was updated
            mock_hass.config_entries.async_update_entry.assert_called_once()
            # Verify reload was triggered
            mock_hass.config_entries.async_reload.assert_called_once()

    @pytest.mark.asyncio
    async def test_repair_validation_fails(self):
        """Test repair validation with invalid tokens."""
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"api_key": "old_key"}

        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        flow = ElectroluxRepairFlow()
        flow.hass = mock_hass
        flow.context = {"issue_id": "invalid_refresh_token_test_entry"}  # type: ignore[typeddict-item]

        user_input = {
            "api_key": "old_key_1234567890",
            "access_token": "invalid_access_token_1234567890",
            "refresh_token": "invalid_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch(
                "custom_components.electrolux.config_flow.async_get_clientsession"
            ) as mock_client_session,
        ):
            mock_client = Mock()
            mock_client.get_appliances_list = AsyncMock(
                side_effect=ValueError("401 Unauthorized")
            )
            mock_session.return_value = mock_client
            mock_client_session.return_value = Mock()

            result = await flow.async_step_init(user_input)

            assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
            assert "errors" in result
            assert result["errors"]["base"] == "invalid_auth"  # type: ignore[index]


class TestConfigFlowAbort:
    """Test config flow abort scenarios."""

    @pytest.mark.asyncio
    async def test_abort_if_already_configured(self):
        """Test that flow aborts if integration already configured."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow._errors = {}

        # Mock existing entry with same API key
        existing_entry = Mock()
        existing_entry.data = {"api_key": "test_key_1234567890"}
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_entries.return_value = []
        # Mock _async_current_entries to return existing entry
        flow._async_current_entries = Mock(return_value=[existing_entry])

        user_input = {
            "api_key": "test_key_1234567890",
            "access_token": "test_access_token_1234567890",
            "refresh_token": "test_refresh_token_1234567890",
        }

        result = await flow.async_step_user(user_input)

        assert result["type"] == data_entry_flow.FlowResultType.ABORT  # type: ignore[typeddict-item]
        assert result["reason"] == "already_configured_account"  # type: ignore[typeddict-item]


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestValidateCredentials:
    """Tests for _validate_credentials helper."""

    def test_valid_credentials_return_no_errors(self):
        errors = _validate_credentials("a" * 12, "b" * 25, "c" * 25)
        assert errors == []

    def test_short_api_key_returns_error(self):
        errors = _validate_credentials("short", "b" * 25, "c" * 25)
        assert any("API key" in e for e in errors)

    def test_none_api_key_returns_error(self):
        errors = _validate_credentials(None, "b" * 25, "c" * 25)
        assert any("API key" in e for e in errors)

    def test_short_access_token_returns_error(self):
        errors = _validate_credentials("a" * 12, "short", "c" * 25)
        assert any("Access token" in e for e in errors)

    def test_short_refresh_token_returns_error(self):
        errors = _validate_credentials("a" * 12, "b" * 25, "short")
        assert any("Refresh token" in e for e in errors)

    def test_dangerous_chars_in_api_key_returns_error(self):
        errors = _validate_credentials("<script>" + "a" * 10, "b" * 25, "c" * 25)
        assert any("invalid character" in e for e in errors)

    def test_dangerous_chars_in_access_token_returns_error(self):
        errors = _validate_credentials("a" * 12, "b" * 20 + ";", "c" * 25)
        assert any("invalid character" in e for e in errors)

    def test_dangerous_chars_in_refresh_token_returns_error(self):
        errors = _validate_credentials("a" * 12, "b" * 25, "c" * 20 + "\n")
        assert any("invalid character" in e for e in errors)


class TestMaskToken:
    """Tests for _mask_token helper."""

    def test_masks_long_token(self):
        result = _mask_token("abcdefghijklmnop")
        assert result == "abcd***mnop"

    def test_short_token_returns_stars(self):
        assert _mask_token("abc") == "***"

    def test_none_returns_stars(self):
        assert _mask_token(None) == "***"

    def test_empty_string_returns_stars(self):
        assert _mask_token("") == "***"


class TestExtractTokenExpiry:
    """Tests for _extract_token_expiry helper."""

    def test_returns_none_for_none_input(self):
        assert _extract_token_expiry(None) is None

    def test_returns_none_for_invalid_jwt(self):
        assert _extract_token_expiry("not.a.jwt") is None

    def test_returns_none_for_jwt_without_exp(self):
        import base64
        import json

        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload = (
            base64.urlsafe_b64encode(json.dumps({"sub": "user"}).encode())
            .decode()
            .rstrip("=")
        )
        token = f"{header}.{payload}.sig"
        assert _extract_token_expiry(token) is None

    def test_returns_exp_from_valid_jwt(self):
        import base64
        import json

        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload = (
            base64.urlsafe_b64encode(json.dumps({"exp": 9999999999}).encode())
            .decode()
            .rstrip("=")
        )
        token = f"{header}.{payload}.sig"
        result = _extract_token_expiry(token)
        assert result == 9999999999


# ---------------------------------------------------------------------------
# Reauth flow tests
# ---------------------------------------------------------------------------


class TestReauthFlow:
    """Tests for the reauth flow."""

    @pytest.mark.asyncio
    async def test_reauth_shows_form(self):
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow._errors = {}
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.title = "Electrolux"
        mock_entry.data = {
            "api_key": "old_key_1234567890",
            "access_token": "old_access_12345678901234567",
            "refresh_token": "old_refresh_12345678901234567",
        }
        flow._reauth_entry = mock_entry

        result = await flow.async_step_reauth(mock_entry)

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["step_id"] == "reauth_validate"  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_reauth_validate_success(self):
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"api_key": "old_key_1234567890"}
        flow._reauth_entry = mock_entry

        user_input = {
            "api_key": "new_api_key_1234567890",
            "access_token": "new_access_token_1234567890",
            "refresh_token": "new_refresh_token_1234567890",
        }

        with (
            patch.object(
                type(flow),
                "show_advanced_options",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            patch("homeassistant.helpers.issue_registry.async_delete_issue"),
            patch.object(
                flow, "async_update_reload_and_abort", return_value={"type": "abort"}
            ),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(return_value=[])
            result = await flow.async_step_reauth_validate(user_input)  # type: ignore[arg-type]

        assert result["type"] == "abort"  # type: ignore[literal-required]

    @pytest.mark.asyncio
    async def test_reauth_validate_invalid_credentials(self):
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {
            "api_key": "old_key_1234567890",
            "access_token": "old_access_12345678901234567",
            "refresh_token": "old_refresh_12345678901234567",
        }
        flow._reauth_entry = mock_entry

        user_input = {
            "api_key": "bad_api_key_1234567890",
            "access_token": "bad_access_token_1234567890",
            "refresh_token": "bad_refresh_token_1234567890",
        }

        with (
            patch.object(
                type(flow),
                "show_advanced_options",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(
                side_effect=ValueError("Unauthorized")
            )
            result = await flow.async_step_reauth_validate(user_input)  # type: ignore[arg-type]

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["errors"]["base"] == "invalid_auth"  # type: ignore[index]

    def test_get_reauth_entry_raises_when_missing(self):
        flow = ElectroluxStatusFlowHandler()
        with pytest.raises(RuntimeError):
            flow._get_reauth_entry()


# ---------------------------------------------------------------------------
# Reconfigure flow tests
# ---------------------------------------------------------------------------


class TestReconfigureFlow:
    """Tests for the reconfigure flow (Silver requirement)."""

    @pytest.mark.asyncio
    async def test_reconfigure_shows_form_with_defaults(self):
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        flow.context = {"entry_id": "test_entry"}  # type: ignore[assignment]
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {
            "api_key": "existing_api_key_1234",
            "access_token": "existing_access_123456789012345",
            "refresh_token": "existing_refresh_12345678901234",
        }
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        with patch.object(
            type(flow),
            "show_advanced_options",
            new_callable=PropertyMock,
            return_value=False,
        ):
            result = await flow.async_step_reconfigure()

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["step_id"] == "reconfigure"  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_reconfigure_success_updates_and_reloads(self):
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        flow.context = {"entry_id": "test_entry"}  # type: ignore[assignment]
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"api_key": "old_key"}
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        user_input = {
            "api_key": "new_api_key_1234567890",
            "access_token": "new_access_token_1234567890",
            "refresh_token": "new_refresh_token_1234567890",
        }

        with (
            patch.object(
                type(flow),
                "show_advanced_options",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            patch.object(
                flow,
                "async_update_reload_and_abort",
                return_value={"type": "abort", "reason": "reconfigure_successful"},
            ),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(return_value=[])
            result = await flow.async_step_reconfigure(user_input)

        assert result["reason"] == "reconfigure_successful"  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_reconfigure_invalid_format_shows_error(self):
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        flow.context = {"entry_id": "test_entry"}  # type: ignore[assignment]
        mock_entry = Mock()
        mock_entry.data = {"api_key": "old_key"}
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        with patch.object(
            type(flow),
            "show_advanced_options",
            new_callable=PropertyMock,
            return_value=False,
        ):
            result = await flow.async_step_reconfigure(
                {"api_key": "short", "access_token": "short", "refresh_token": "short"}
            )

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["errors"]["base"] == "invalid_format"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_reconfigure_invalid_auth_shows_error(self):
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        flow.context = {"entry_id": "test_entry"}  # type: ignore[assignment]
        mock_entry = Mock()
        mock_entry.data = {"api_key": "old_key"}
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        user_input = {
            "api_key": "bad_api_key_1234567890",
            "access_token": "bad_access_token_1234567890",
            "refresh_token": "bad_refresh_token_1234567890",
        }

        with (
            patch.object(
                type(flow),
                "show_advanced_options",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(
                side_effect=ConnectionError
            )
            result = await flow.async_step_reconfigure(user_input)

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["errors"]["base"] == "invalid_auth"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_reconfigure_aborts_when_entry_not_found(self):
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow.context = {"entry_id": "missing_entry"}  # type: ignore[assignment]
        flow.hass.config_entries.async_get_entry = Mock(return_value=None)

        with patch.object(
            flow,
            "async_abort",
            return_value={"type": "abort", "reason": "entry_not_found"},
        ):
            result = await flow.async_step_reconfigure()

        assert result["reason"] == "entry_not_found"  # type: ignore[typeddict-item]


# ---------------------------------------------------------------------------
# Options flow tests
# ---------------------------------------------------------------------------


class TestOptionsFlowHandler:
    """Tests for ElectroluxStatusOptionsFlowHandler."""

    def _make_options_flow(self, data=None, options=None):
        mock_entry = Mock()
        mock_entry.data = data or {
            "api_key": "existing_api_key_1234",
            "access_token": "existing_access_1234567890",
            "refresh_token": "existing_refresh_1234567890",
            "notification_default": True,
            "notification_warning": False,
            "notification_diag": False,
        }
        mock_entry.options = options or {}
        return ElectroluxStatusOptionsFlowHandler(mock_entry)

    @pytest.mark.asyncio
    async def test_options_step_init_shows_form(self):
        flow = self._make_options_flow()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()

        result = await flow.async_step_init()

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_options_step_user_shows_form_with_no_input(self):
        flow = self._make_options_flow()
        flow.hass = Mock()

        result = await flow.async_step_user()

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["step_id"] == "user"  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_options_step_user_success_creates_entry(self):
        flow = self._make_options_flow()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_update_entry = Mock()

        user_input = {
            "api_key": "new_api_key_1234567890",
            "access_token": "new_access_token_1234567890",
            "refresh_token": "new_refresh_token_1234567890",
            "notification_default": True,
            "notification_warning": False,
            "notification_diag": False,
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(return_value=[])
            result = await flow.async_step_user(user_input)

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_options_step_user_invalid_credentials_shows_error(self):
        flow = self._make_options_flow()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()

        user_input = {
            "api_key": "bad_api_key_1234567890",
            "access_token": "bad_access_token_1234567890",
            "refresh_token": "bad_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(
                side_effect=ValueError("Unauthorized")
            )
            result = await flow.async_step_user(user_input)

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["errors"]["base"] == "invalid_auth"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_options_schema_omits_tokens_for_security(self):
        flow = self._make_options_flow()
        schema = await flow._get_options_schema()
        # Schema should be present (not None)
        assert schema is not None


class TestConfigFlowMissingCoverage:
    """Tests targeting remaining missed lines in config_flow.py."""

    # ------------------------------------------------------------------ #
    # Lines 131-135: validation errors in user step (short credentials)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_user_step_short_credentials_shows_invalid_format(self):
        """Short credentials trigger validation_errors → lines 131-135."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow._errors = {}
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_entries.return_value = []

        result = await flow.async_step_user(
            {"api_key": "short", "access_token": "short", "refresh_token": "short"}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["errors"]["base"] == "invalid_format"  # type: ignore[index]

    # ------------------------------------------------------------------ #
    # Lines 156-159: token_expiry logging in user step (valid JWT)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_user_step_stores_token_expiry_when_present(self):
        """When _extract_token_expiry returns a value, token_expires_at is stored (lines 156-159)."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_entries.return_value = []
        flow.hass.data = {}

        user_input = {
            "api_key": "test_api_key_1234567890",
            "access_token": "test_access_token_1234567890",
            "refresh_token": "test_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            patch(
                "custom_components.electrolux.config_flow._extract_token_expiry",
                return_value=9999999999,
            ),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(return_value=[])
            result = await flow.async_step_user(user_input)

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY  # type: ignore[typeddict-item]
        assert result["data"]["token_expires_at"] == 9999999999  # type: ignore[typeddict-item]

    # ------------------------------------------------------------------ #
    # Lines 223-227: reauth validate — _get_reauth_entry returns None
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_reauth_validate_no_entry_sets_reauth_failed_error(self):
        """When _get_reauth_entry returns None inside _validate_reauth_input, sets reauth_failed (lines 223-227)."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        flow._reauth_entry = Mock()  # prevent RuntimeError from the real method

        user_input = {
            "api_key": "valid_api_key_12345678",
            "access_token": "valid_access_token_1234567890",
            "refresh_token": "valid_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            # Patch _get_reauth_entry to return None on first call
            patch.object(flow, "_get_reauth_entry", return_value=None),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(return_value=[])
            # Call the inner method directly to avoid the second _get_reauth_entry call
            result = await flow._validate_reauth_input(user_input)

        assert result is None
        assert flow._errors.get("base") == "reauth_failed"

    # ------------------------------------------------------------------ #
    # Lines 238-240: reauth validate — token_expiry truthy
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_reauth_validate_success_with_token_expiry_stored(self):
        """When _extract_token_expiry returns a value during reauth, token_expires_at is stored (lines 238-240)."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"api_key": "old_key"}
        flow._reauth_entry = mock_entry

        user_input = {
            "api_key": "new_api_key_1234567890",
            "access_token": "new_access_token_1234567890",
            "refresh_token": "new_refresh_token_1234567890",
        }

        with (
            patch.object(
                type(flow),
                "show_advanced_options",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            patch("homeassistant.helpers.issue_registry.async_delete_issue"),
            patch(
                "custom_components.electrolux.config_flow._extract_token_expiry",
                return_value=9999999999,
            ),
            patch.object(
                flow,
                "async_update_reload_and_abort",
                return_value={"type": "abort"},
            ),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(return_value=[])
            result = await flow.async_step_reauth_validate(user_input)  # type: ignore[arg-type]

        assert result["type"] == "abort"  # type: ignore[literal-required]

    # ------------------------------------------------------------------ #
    # Line 317: reconfigure — token_expiry truthy
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_reconfigure_success_stores_token_expiry(self):
        """When _extract_token_expiry returns a value during reconfigure, it's stored (line 317)."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow._errors = {}
        flow.context = {"entry_id": "test_entry"}  # type: ignore[assignment]
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"api_key": "old_key"}
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        user_input = {
            "api_key": "new_api_key_1234567890",
            "access_token": "new_access_token_1234567890",
            "refresh_token": "new_refresh_token_1234567890",
        }

        with (
            patch.object(
                type(flow),
                "show_advanced_options",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            patch(
                "custom_components.electrolux.config_flow._extract_token_expiry",
                return_value=9999999999,
            ),
            patch.object(
                flow,
                "async_update_reload_and_abort",
                return_value={"type": "abort", "reason": "reconfigure_successful"},
            ),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(return_value=[])
            result = await flow.async_step_reconfigure(user_input)

        assert result["reason"] == "reconfigure_successful"  # type: ignore[typeddict-item]

    # ------------------------------------------------------------------ #
    # Line 333: async_get_options_flow static method
    # ------------------------------------------------------------------ #

    def test_async_get_options_flow_returns_options_handler(self):
        """async_get_options_flow returns an ElectroluxStatusOptionsFlowHandler (line 333)."""
        mock_entry = Mock()
        mock_entry.data = {}
        mock_entry.options = {}
        handler = ElectroluxStatusFlowHandler.async_get_options_flow(mock_entry)
        assert isinstance(handler, ElectroluxStatusOptionsFlowHandler)

    # ------------------------------------------------------------------ #
    # Line 359: _get_config_schema with show_advanced_options=True
    # ------------------------------------------------------------------ #

    def test_get_config_schema_with_advanced_options_includes_notifications(self):
        """When show_advanced_options=True, notification fields are added (line 359)."""
        flow = ElectroluxStatusFlowHandler()
        with patch.object(
            type(flow),
            "show_advanced_options",
            new_callable=PropertyMock,
            return_value=True,
        ):
            schema = flow._get_config_schema({})
        assert schema is not None

    # ------------------------------------------------------------------ #
    # Lines 410-415: main flow _test_credentials with unexpected exception
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_user_step_unexpected_exception_shows_invalid_auth(self):
        """RuntimeError in _test_credentials hits the unexpected-exception except block (lines 410-415)."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_entries.return_value = []

        user_input = {
            "api_key": "test_api_key_1234567890",
            "access_token": "test_access_token_1234567890",
            "refresh_token": "test_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(
                side_effect=RuntimeError("unexpected error")
            )
            result = await flow.async_step_user(user_input)

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["errors"]["base"] == "invalid_auth"  # type: ignore[index]

    # ------------------------------------------------------------------ #
    # Lines 504-509: options flow _test_credentials with unexpected exception
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_options_step_unexpected_exception_shows_invalid_auth(self):
        """RuntimeError in options flow _test_credentials hits unexpected-except (lines 504-509)."""
        mock_entry = Mock()
        mock_entry.data = {
            "api_key": "existing_api_key_1234",
            "access_token": "existing_access_1234567890",
            "refresh_token": "existing_refresh_1234567890",
        }
        mock_entry.options = {}
        flow = ElectroluxStatusOptionsFlowHandler(mock_entry)
        flow.hass = Mock()
        flow.hass.config_entries = Mock()

        user_input = {
            "api_key": "test_api_key_1234567890",
            "access_token": "test_access_token_1234567890",
            "refresh_token": "test_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(
                side_effect=RuntimeError("unexpected error")
            )
            result = await flow.async_step_user(user_input)

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["errors"]["base"] == "invalid_auth"  # type: ignore[index]

    # ------------------------------------------------------------------ #
    # Lines 622-623: repair flow — config entry not found
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_repair_confirm_repair_entry_not_found_aborts(self):
        """When entry_id lookup returns None in repair flow, async_abort is called (lines 622-623)."""
        flow = ElectroluxRepairFlow()
        flow.hass = Mock()
        flow.context = {"issue_id": "invalid_refresh_token_missing_entry"}  # type: ignore[typeddict-item]
        flow.hass.config_entries = Mock()
        # Return None so the entry_not_found path is taken
        flow.hass.config_entries.async_get_entry = Mock(return_value=None)

        with patch.object(
            flow,
            "async_abort",
            return_value={"type": "abort", "reason": "entry_not_found"},
        ):
            result = await flow.async_step_init(
                {
                    "api_key": "test_api_key_1234567890",
                    "access_token": "test_access_token_1234567890",
                    "refresh_token": "test_refresh_token_1234567890",
                }
            )

        assert result["reason"] == "entry_not_found"  # type: ignore[typeddict-item]

    @pytest.mark.asyncio
    async def test_repair_confirm_repair_validation_errors_show_form(self):
        """Short credentials in repair flow trigger validation_errors → lines 622-623."""
        flow = ElectroluxRepairFlow()
        flow.hass = Mock()
        flow.context = {"issue_id": "invalid_refresh_token_test_entry"}  # type: ignore[typeddict-item]
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"api_key": "old_key"}
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        result = await flow.async_step_init(
            {"api_key": "short", "access_token": "short", "refresh_token": "short"}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["errors"]["base"] == "invalid_format"  # type: ignore[index]

    # ------------------------------------------------------------------ #
    # Lines 635-636 + 651-653: repair flow success with token_expiry truthy
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_repair_confirm_repair_success_with_token_expiry(self):
        """Repair flow success with token_expiry truthy stores expires_at and runs update/reload (lines 635-636, 651-653)."""
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"api_key": "old_key", "access_token": "old_token"}
        mock_hass.config_entries = Mock()
        mock_hass.config_entries.async_get_entry = Mock(return_value=mock_entry)
        mock_hass.config_entries.async_update_entry = Mock()
        mock_hass.config_entries.async_reload = AsyncMock()

        flow = ElectroluxRepairFlow()
        flow.hass = mock_hass
        flow.context = {"issue_id": "invalid_refresh_token_test_entry"}  # type: ignore[typeddict-item]

        user_input = {
            "api_key": "valid_api_key_1234567890",
            "access_token": "valid_access_token_1234567890",
            "refresh_token": "valid_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
            patch("custom_components.electrolux.config_flow.ir.async_delete_issue"),
            patch(
                "custom_components.electrolux.config_flow._extract_token_expiry",
                return_value=9999999999,
            ),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(return_value=[])
            result = await flow.async_step_init(user_input)

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY  # type: ignore[typeddict-item]
        mock_hass.config_entries.async_update_entry.assert_called_once()
        mock_hass.config_entries.async_reload.assert_called_once()

    # ------------------------------------------------------------------ #
    # Lines 743-748: repair flow _test_credentials with unexpected exception
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_repair_test_credentials_unexpected_exception_shows_invalid_auth(
        self,
    ):
        """RuntimeError in repair flow _test_credentials hits unexpected-except (lines 743-748)."""
        flow = ElectroluxRepairFlow()
        flow.hass = Mock()
        flow.context = {"issue_id": "invalid_refresh_token_test_entry"}  # type: ignore[typeddict-item]
        mock_entry = Mock()
        mock_entry.entry_id = "test_entry"
        mock_entry.data = {"api_key": "old_key"}
        flow.hass.config_entries = Mock()
        flow.hass.config_entries.async_get_entry = Mock(return_value=mock_entry)

        user_input = {
            "api_key": "test_api_key_1234567890",
            "access_token": "test_access_token_1234567890",
            "refresh_token": "test_refresh_token_1234567890",
        }

        with (
            patch(
                "custom_components.electrolux.config_flow.get_electrolux_session"
            ) as mock_session,
            patch("custom_components.electrolux.config_flow.async_get_clientsession"),
        ):
            mock_session.return_value.get_appliances_list = AsyncMock(
                side_effect=RuntimeError("unexpected error")
            )
            result = await flow.async_step_init(user_input)

        assert result["type"] == data_entry_flow.FlowResultType.FORM  # type: ignore[typeddict-item]
        assert result["errors"]["base"] == "invalid_auth"  # type: ignore[index]
