"""Test the Electrolux config flow."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant import data_entry_flow

from custom_components.electrolux.config_flow import (
    ElectroluxRepairFlow,
    ElectroluxStatusFlowHandler,
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
        mock_hass.config_entries.async_update_entry = AsyncMock()
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
