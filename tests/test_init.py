"""Test the Electrolux integration setup."""

from custom_components.electrolux.const import DOMAIN


def test_domain():
    """Test that the domain is correct."""
    assert DOMAIN == "electrolux"
