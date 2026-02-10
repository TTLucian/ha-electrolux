"""Test the Electrolux config flow."""

from custom_components.electrolux.config_flow import ElectroluxStatusFlowHandler


def test_config_flow_class():
    """Test that the config flow class exists."""
    assert ElectroluxStatusFlowHandler is not None
