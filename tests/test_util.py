"""Tests for Electrolux util helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.util import (
    ApplianceOfflineError,
    AuthenticationError,
    CommandError,
    CommandValidationError,
    ElectroluxApiClient,
    NetworkError,
    RateLimitError,
    RemoteControlDisabledError,
    format_command_for_appliance,
    string_to_boolean,
)


@pytest.mark.asyncio
async def test_report_token_refresh_creates_issue(monkeypatch):
    """Assert an HA issue is created when token refresh fails and hass is available."""

    captured = {}

    def fake_create_issue(hass_arg, domain, issue_id, **kwargs):
        captured["args"] = (hass_arg, domain, issue_id)
        captured["kwargs"] = kwargs

    monkeypatch.setattr(
        "custom_components.electrolux.util.issue_registry.async_create_issue",
        fake_create_issue,
    )

    from custom_components.electrolux.util import DOMAIN

    hass = MagicMock()
    # Mock config_entries to return empty list so issue_id doesn't include entry_id
    hass.config_entries.async_entries.return_value = []

    client = ElectroluxApiClient("api", "access", "refresh", hass, config_entry=None)

    await client._report_token_refresh_error("Refresh token is invalid.")

    assert "args" in captured
    assert captured["args"][0] is hass
    assert captured["args"][1] == DOMAIN
    assert captured["args"][2] == "invalid_refresh_token"
    assert (
        captured["kwargs"]["translation_placeholders"]["message"]
        == "Refresh token is invalid."
    )
    assert captured["kwargs"]["is_fixable"] is True


@pytest.mark.asyncio
async def test_report_token_refresh_no_hass_does_not_create_issue(monkeypatch):
    """Assert no issue is created if hass is not provided."""

    called = {}

    def fake_create_issue(*args, **kwargs):
        called["called"] = True

    monkeypatch.setattr(
        "custom_components.electrolux.util.issue_registry.async_create_issue",
        fake_create_issue,
    )

    client = ElectroluxApiClient(
        "api", "access", "refresh", hass=None, config_entry=None
    )

    await client._report_token_refresh_error("No HA available")

    assert "called" not in called


class TestExecuteCommandWithErrorHandling:
    """Test execute_command_with_error_handling function."""

    @pytest.mark.asyncio
    async def test_command_success(self):
        """Test successful command execution."""
        from custom_components.electrolux.util import (
            execute_command_with_error_handling,
        )

        mock_client = MagicMock()
        mock_client.execute_appliance_command = AsyncMock(return_value={"status": "ok"})
        mock_logger = MagicMock()

        result = await execute_command_with_error_handling(
            client=mock_client,
            pnc_id="test_appliance_123",
            command={"targetTemperatureC": 180},
            entity_attr="targetTemperatureC",
            logger=mock_logger,
        )

        assert result == {"status": "ok"}
        mock_client.execute_appliance_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_command_remote_control_disabled(self):
        """Test command fails with remote control disabled error."""
        from custom_components.electrolux.util import (
            execute_command_with_error_handling,
        )

        mock_client = MagicMock()
        mock_client.execute_appliance_command = AsyncMock(
            side_effect=Exception("Remote control disabled")
        )
        mock_logger = MagicMock()

        with pytest.raises(HomeAssistantError, match="Remote control is disabled"):
            await execute_command_with_error_handling(
                client=mock_client,
                pnc_id="test_appliance_123",
                command={"targetTemperatureC": 180},
                entity_attr="targetTemperatureC",
                logger=mock_logger,
            )

    @pytest.mark.asyncio
    async def test_command_appliance_disconnected(self):
        """Test command fails with appliance disconnected error."""
        from custom_components.electrolux.util import (
            execute_command_with_error_handling,
        )

        mock_client = MagicMock()
        mock_client.execute_appliance_command = AsyncMock(
            side_effect=Exception("Appliance disconnected")
        )
        mock_logger = MagicMock()

        with pytest.raises(HomeAssistantError, match="disconnected"):
            await execute_command_with_error_handling(
                client=mock_client,
                pnc_id="test_appliance_123",
                command={"targetTemperatureC": 180},
                entity_attr="targetTemperatureC",
                logger=mock_logger,
            )

    @pytest.mark.asyncio
    async def test_command_authentication_error(self):
        """Test command fails with authentication error."""
        from custom_components.electrolux.util import (
            AuthenticationError,
            execute_command_with_error_handling,
        )

        mock_client = MagicMock()
        mock_client.execute_appliance_command = AsyncMock(
            side_effect=Exception("401 Unauthorized")
        )
        mock_logger = MagicMock()

        with pytest.raises(AuthenticationError):
            await execute_command_with_error_handling(
                client=mock_client,
                pnc_id="test_appliance_123",
                command={"targetTemperatureC": 180},
                entity_attr="targetTemperatureC",
                logger=mock_logger,
            )


class TestStringToBoolean:
    """Test string_to_boolean function."""

    def test_none_returns_none(self):
        """Test that None input returns None."""
        assert string_to_boolean(None) is None

    def test_on_values(self):
        """Test values that should return True."""
        on_values = [
            "on",
            "ON",
            "enabled",
            "ENABLED",
            "running",
            "true",
            "yes",
            "motion",
            "detected",
        ]
        for value in on_values:
            assert string_to_boolean(value) is True, f"Failed for {value}"

    def test_off_values(self):
        """Test values that should return False."""
        off_values = [
            "off",
            "OFF",
            "disabled",
            "DISABLED",
            "stopped",
            "false",
            "no",
            "clear",
            "normal",
        ]
        for value in off_values:
            assert string_to_boolean(value) is False, f"Failed for {value}"

    def test_unknown_value_with_fallback(self):
        """Test unknown value returns original with fallback=True."""
        result = string_to_boolean("unknown_value", fallback=True)
        assert result == "unknown_value"

    def test_unknown_value_without_fallback(self):
        """Test unknown value returns False with fallback=False."""
        result = string_to_boolean("unknown_value", fallback=False)
        assert result is False

    def test_whitespace_normalization(self):
        """Test that whitespace is normalized."""
        assert string_to_boolean("  running  ") is True
        assert string_to_boolean("stopped  ") is False

    def test_underscore_to_space(self):
        """Test that underscores are converted to spaces."""
        assert string_to_boolean("no_motion") is False
        assert string_to_boolean("no_problem") is False


class TestFormatCommandForAppliance:
    """Test format_command_for_appliance function."""

    def test_boolean_capability(self):
        """Test formatting boolean values."""
        capability = {"type": "boolean"}

        # Test bool True
        assert format_command_for_appliance(capability, "cavityLight", True) is True
        # Test bool False
        assert format_command_for_appliance(capability, "cavityLight", False) is False
        # Test string "on"
        assert format_command_for_appliance(capability, "cavityLight", "on") is True
        # Test string "off"
        assert format_command_for_appliance(capability, "cavityLight", "off") is False

    def test_numeric_capability_with_step(self):
        """Test formatting numeric values with step constraint."""
        capability = {"type": "number", "min": 30, "max": 250, "step": 5}

        # Test value on step boundary
        assert (
            format_command_for_appliance(capability, "targetTemperatureC", 180) == 180
        )
        # Test value not on step boundary (should round to nearest)
        assert (
            format_command_for_appliance(capability, "targetTemperatureC", 182) == 180
        )
        assert (
            format_command_for_appliance(capability, "targetTemperatureC", 183) == 185
        )

    def test_numeric_capability_min_max_clamping(self):
        """Test that numeric values are clamped to min/max."""
        capability = {"type": "number", "min": 30, "max": 250}

        # Test value below min
        assert format_command_for_appliance(capability, "targetTemperatureC", 20) == 30
        # Test value above max
        assert (
            format_command_for_appliance(capability, "targetTemperatureC", 300) == 250
        )
        # Test value within range
        assert (
            format_command_for_appliance(capability, "targetTemperatureC", 150) == 150
        )

    def test_string_capability_with_values(self):
        """Test formatting string/enum values."""
        capability = {
            "type": "string",
            "values": {
                "COOL": {"label": "Cool"},
                "HEAT": {"label": "Heat"},
                "AUTO": {"label": "Auto"},
            },
        }

        # Test exact match
        assert format_command_for_appliance(capability, "mode", "COOL") == "COOL"
        # Test case-insensitive match
        assert format_command_for_appliance(capability, "mode", "cool") == "COOL"
        assert format_command_for_appliance(capability, "mode", "auto") == "AUTO"

    def test_string_capability_invalid_value(self):
        """Test formatting with invalid enum value."""
        capability = {
            "type": "string",
            "values": {
                "COOL": {"label": "Cool"},
                "HEAT": {"label": "Heat"},
            },
        }

        # Invalid value should be passed through (let API handle)
        result = format_command_for_appliance(capability, "mode", "INVALID")
        assert result == "INVALID"

    def test_temperature_attribute_auto_detection(self):
        """Test that temperature attributes are detected by name."""
        capability = {"type": "number", "min": 15, "max": 30}

        # Should be treated as numeric even without explicit type
        result = format_command_for_appliance(capability, "targetTemperatureC", 25.5)
        assert result == 25.5

    def test_no_capability_fallback_boolean(self):
        """Test fallback behavior with no capability for boolean."""
        result = format_command_for_appliance(None, "cavityLight", True)  # type: ignore[arg-type]
        assert result == "ON"

        result = format_command_for_appliance(None, "cavityLight", False)  # type: ignore[arg-type]
        assert result == "OFF"

    def test_no_capability_fallback_other(self):
        """Test fallback behavior with no capability for non-boolean."""
        result = format_command_for_appliance(None, "targetTemp", 180)  # type: ignore[arg-type]
        assert result == 180

        result = format_command_for_appliance(None, "mode", "COOL")  # type: ignore[arg-type]
        assert result == "COOL"

    def test_empty_capability_dict(self):
        """Test with empty capability dictionary."""
        capability = {}

        # Should use fallback behavior
        result = format_command_for_appliance(capability, "cavityLight", True)
        assert result == "ON"


class TestCommandErrorClasses:
    """Test command error exception classes."""

    def test_command_error_base(self):
        """Test CommandError base exception."""
        error = CommandError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_remote_control_disabled_error(self):
        """Test RemoteControlDisabledError."""
        error = RemoteControlDisabledError("Remote control disabled")
        assert isinstance(error, CommandError)

    def test_appliance_offline_error(self):
        """Test ApplianceOfflineError."""
        error = ApplianceOfflineError("Appliance disconnected")
        assert isinstance(error, CommandError)

    def test_command_validation_error(self):
        """Test CommandValidationError."""
        error = CommandValidationError("Invalid step")
        assert isinstance(error, CommandError)

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("Too many requests")
        assert isinstance(error, CommandError)

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Token expired")
        assert isinstance(error, CommandError)

    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError("Connection failed")
        assert isinstance(error, CommandError)
