"""Test the Electrolux config flow."""

from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.electrolux.config_flow import (
    ElectroluxRepairFlow,
    ElectroluxStatusFlowHandler,
    async_create_fix_flow,
)


def test_config_flow_class():
    """Test that the config flow class exists."""
    assert ElectroluxStatusFlowHandler is not None


@pytest.mark.asyncio
async def test_repair_flow_initialization():
    """Test that the repair flow can be created."""
    # Create mock hass
    mock_hass = Mock()
    mock_hass.config_entries = Mock()
    mock_hass.config_entries.async_get_entry = Mock(return_value=None)

    # Test that the repair flow can be created
    flow = await async_create_fix_flow(mock_hass, "invalid_refresh_token_test", None)
    assert flow is not None
    assert isinstance(flow, ElectroluxRepairFlow)


@pytest.mark.asyncio
async def test_repair_validation():
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
    # Mock the context dict
    flow.context = {"issue_id": "invalid_refresh_token_test_entry"}  # type: ignore[typeddict-item]

    # Mock _test_credentials to return True
    flow._test_credentials = AsyncMock(return_value=True)

    # Test validation with valid input
    user_input = {
        "api_key": "new_key",
        "access_token": "new_token",
        "refresh_token": "new_refresh",
    }

    # Mock async_create_entry to prevent actual entry creation
    flow.async_create_entry = Mock(return_value={"type": "create_entry"})
    flow.async_show_form = Mock(return_value={"type": "form"})

    result = await flow.async_step_confirm_repair(user_input)
    assert result is not None
