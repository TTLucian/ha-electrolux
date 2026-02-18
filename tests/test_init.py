"""Test the Electrolux integration setup."""

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
