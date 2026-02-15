"""Test the Electrolux config flow."""

from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.electrolux.config_flow import ElectroluxStatusFlowHandler


def test_config_flow_class():
    """Test that the config flow class exists."""
    assert ElectroluxStatusFlowHandler is not None


@pytest.mark.asyncio
async def test_repair_flow_step():
    """Test that the repair flow step exists and can be called."""
    # Create a mock config entry
    mock_entry = Mock()
    mock_entry.entry_id = "test_entry"
    mock_entry.data = {"access_token": "old_token", "refresh_token": "old_refresh"}

    # Create a flow handler
    flow = ElectroluxStatusFlowHandler()

    # Mock required methods
    flow._test_credentials = AsyncMock(return_value={"title": "Test"})
    flow._show_config_form = AsyncMock(
        return_value={"type": "form", "step_id": "repair"}
    )
    flow.hass = Mock()
    flow.hass.config_entries = Mock()
    flow.hass.config_entries.async_update_entry = AsyncMock()

    # Test that the repair method exists and can be called
    result = await flow.async_step_repair(mock_entry)
    assert result["type"] == "form"
    assert result["step_id"] == "repair"


@pytest.mark.asyncio
async def test_repair_validation():
    """Test repair input validation."""
    flow = ElectroluxStatusFlowHandler()

    # Mock required methods
    flow._test_credentials = AsyncMock(return_value={"title": "Test"})
    flow.hass = Mock()
    flow.hass.config_entries = Mock()
    flow.hass.config_entries.async_update_entry = AsyncMock()
    flow.hass.issue_registry = Mock()
    flow.hass.issue_registry.async_delete = AsyncMock()

    # Test validation with valid input
    user_input = {"access_token": "new_token", "refresh_token": "new_refresh"}
    result = await flow._validate_repair_input(user_input)
    assert result is None  # None means validation passed
