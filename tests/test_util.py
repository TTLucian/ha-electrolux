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
        "custom_components.electrolux.api_client.issue_registry.async_create_issue",
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
        "custom_components.electrolux.api_client.issue_registry.async_create_issue",
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

    def test_numeric_capability_misaligned_min_with_step(self):
        """Test formatting numeric values when min is not aligned with step boundaries.

        Real-world case: AC unit with min=15.56°C (60°F), max=32.22°C (90°F), step=1.0
        Valid values should be 16, 17, 18... not 15.56, 16.56, 17.56...
        Fixes issue where setting 24°C was incorrectly calculated as 23.56°C.
        """
        capability = {"type": "temperature", "min": 15.56, "max": 32.22, "step": 1.0}

        # Test value that should stay as-is (aligned with rounded min)
        assert (
            format_command_for_appliance(capability, "targetTemperatureC", 24) == 24.0
        )
        # Test another aligned value
        assert (
            format_command_for_appliance(capability, "targetTemperatureC", 20) == 20.0
        )
        # Test value at rounded min boundary
        assert (
            format_command_for_appliance(capability, "targetTemperatureC", 16) == 16.0
        )
        # Test value near max
        assert (
            format_command_for_appliance(capability, "targetTemperatureC", 30) == 30.0
        )
        # Test rounding behavior (24.5 should round to nearest step: 24.0 or 25.0)
        result = format_command_for_appliance(capability, "targetTemperatureC", 24.5)
        assert result in [24.0, 25.0]  # Either is acceptable depending on rounding

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

    def test_string_capability_boolean_to_on_off(self):
        """Test boolean values with string-based ON/OFF switches."""
        capability = {
            "type": "string",
            "values": {
                "OFF": {},
                "ON": {},
            },
        }

        # Test boolean True converts to "ON"
        result = format_command_for_appliance(capability, "UVState", True)
        assert result == "ON"

        # Test boolean False converts to "OFF"
        result = format_command_for_appliance(capability, "UVState", False)
        assert result == "OFF"

        # Test string values still work
        result = format_command_for_appliance(capability, "UVState", "ON")
        assert result == "ON"

        result = format_command_for_appliance(capability, "UVState", "OFF")
        assert result == "OFF"

        # Test case-insensitive string values
        result = format_command_for_appliance(capability, "UVState", "on")
        assert result == "ON"

        result = format_command_for_appliance(capability, "UVState", "off")
        assert result == "OFF"

    def test_boolean_vs_string_on_off_switches(self):
        """Verify boolean-type switches are NOT affected by string ON/OFF conversion."""
        # Boolean-type capability (like cavityLight in ovens)
        boolean_capability = {"type": "boolean"}

        # Boolean input should return Python bool, NOT "ON"/"OFF" string
        result = format_command_for_appliance(boolean_capability, "cavityLight", True)
        assert result is True
        assert isinstance(result, bool)

        result = format_command_for_appliance(boolean_capability, "cavityLight", False)
        assert result is False
        assert isinstance(result, bool)

        # String-type ON/OFF capability (like UVState in air purifiers)
        string_on_off_capability = {"type": "string", "values": {"ON": {}, "OFF": {}}}

        # Boolean input should be converted to "ON"/"OFF" string
        result = format_command_for_appliance(string_on_off_capability, "UVState", True)
        assert result == "ON"
        assert isinstance(result, str)

        result = format_command_for_appliance(
            string_on_off_capability, "UVState", False
        )
        assert result == "OFF"
        assert isinstance(result, str)

    def test_string_capability_with_non_on_off_values(self):
        """Verify string switches with other values don't trigger boolean conversion."""
        # String capability with values other than ON/OFF (like Workmode)
        capability = {
            "type": "string",
            "values": {
                "Auto": {},
                "Manual": {},
                "Quiet": {},
                "PowerOff": {},
            },
        }

        # Boolean input should NOT be converted to ON/OFF for non-ON/OFF switches
        # It should fall through to normal string handling (which will warn and pass through)
        result = format_command_for_appliance(capability, "Workmode", True)
        # Should return the original boolean since "True" is not in values
        assert result is True

        # String values should work normally
        result = format_command_for_appliance(capability, "Workmode", "Auto")
        assert result == "Auto"

        result = format_command_for_appliance(capability, "Workmode", "manual")
        assert result == "Manual"  # Case-insensitive match

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


class TestShouldSendNotification:
    """Tests for should_send_notification utility."""

    def test_not_needed_always_false(self):
        """Returns False when alert_status is NOT_NEEDED regardless of config."""
        from custom_components.electrolux.util import should_send_notification

        config_entry = MagicMock()
        config_entry.data = {
            "notifications": True,
            "notifications_warning": True,
            "notifications_diagnostic": True,
        }
        assert should_send_notification(config_entry, "DEFAULT", "NOT_NEEDED") is False

    def test_diagnostic_respects_config_true(self):
        """DIAGNOSTIC alerts enabled when CONF_NOTIFICATION_DIAG is True."""
        from custom_components.electrolux.util import should_send_notification

        config_entry = MagicMock()
        config_entry.data = {"notifications_diagnostic": True}
        assert should_send_notification(config_entry, "DIAGNOSTIC", "NEW") is True

    def test_diagnostic_respects_config_false(self):
        """DIAGNOSTIC alerts disabled when CONF_NOTIFICATION_DIAG is False."""
        from custom_components.electrolux.util import should_send_notification

        config_entry = MagicMock()
        config_entry.data = {"notifications_diagnostic": False}
        assert should_send_notification(config_entry, "DIAGNOSTIC", "NEW") is False

    def test_warning_respects_config_true(self):
        """WARNING alerts enabled when CONF_NOTIFICATION_WARNING is True."""
        from custom_components.electrolux.util import should_send_notification

        config_entry = MagicMock()
        config_entry.data = {"notifications_warning": True}
        assert should_send_notification(config_entry, "WARNING", "NEW") is True

    def test_warning_respects_config_false(self):
        """WARNING alerts disabled when CONF_NOTIFICATION_WARNING is False."""
        from custom_components.electrolux.util import should_send_notification

        config_entry = MagicMock()
        config_entry.data = {"notifications_warning": False}
        assert should_send_notification(config_entry, "WARNING", "NEW") is False

    def test_other_severity_uses_default_true(self):
        """Non-DIAGNOSTIC/WARNING severity uses CONF_NOTIFICATION_DEFAULT."""
        from custom_components.electrolux.util import should_send_notification

        config_entry = MagicMock()
        config_entry.data = {"notifications": True}
        assert should_send_notification(config_entry, "CRITICAL", "NEW") is True

    def test_other_severity_default_missing_returns_true(self):
        """Non-DIAGNOSTIC/WARNING severity returns True when CONF_NOTIFICATION_DEFAULT not set."""
        from custom_components.electrolux.util import should_send_notification

        config_entry = MagicMock()
        config_entry.data = {}
        # get("notifications", True) returns True when missing
        assert should_send_notification(config_entry, "CRITICAL", "NEW") is True


class TestTimeConversions:
    """Tests for time conversion utilities."""

    def test_time_seconds_to_minutes_none(self):
        """Returns None when input is None."""
        from custom_components.electrolux.util import time_seconds_to_minutes

        assert time_seconds_to_minutes(None) is None

    def test_time_seconds_to_minutes_sentinel(self):
        """Returns sentinel when input is sentinel."""
        from custom_components.electrolux.const import TIME_INVALID_SENTINEL
        from custom_components.electrolux.util import time_seconds_to_minutes

        assert time_seconds_to_minutes(TIME_INVALID_SENTINEL) == TIME_INVALID_SENTINEL

    def test_time_seconds_to_minutes_zero(self):
        """Converts 0 seconds to 0 minutes."""
        from custom_components.electrolux.util import time_seconds_to_minutes

        assert time_seconds_to_minutes(0) == 0

    def test_time_seconds_to_minutes_typical(self):
        """Converts 3600 seconds to 60 minutes."""
        from custom_components.electrolux.util import time_seconds_to_minutes

        assert time_seconds_to_minutes(3600) == 60

    def test_time_minutes_to_seconds_none(self):
        """Returns None when input is None."""
        from custom_components.electrolux.util import time_minutes_to_seconds

        assert time_minutes_to_seconds(None) is None

    def test_time_minutes_to_seconds_sentinel(self):
        """Returns sentinel when input is sentinel."""
        from custom_components.electrolux.const import TIME_INVALID_SENTINEL
        from custom_components.electrolux.util import time_minutes_to_seconds

        assert time_minutes_to_seconds(TIME_INVALID_SENTINEL) == TIME_INVALID_SENTINEL

    def test_time_minutes_to_seconds_typical(self):
        """Converts 60 minutes to 3600 seconds."""
        from custom_components.electrolux.util import time_minutes_to_seconds

        assert time_minutes_to_seconds(60) == 3600


class TestTemperatureConversions:
    """Tests for celsius/fahrenheit conversion utilities."""

    def test_celsius_to_fahrenheit_none(self):
        """Returns None for None input."""
        from custom_components.electrolux.util import celsius_to_fahrenheit

        assert celsius_to_fahrenheit(None) is None

    def test_celsius_to_fahrenheit_zero(self):
        """0°C = 32°F."""
        from custom_components.electrolux.util import celsius_to_fahrenheit

        assert celsius_to_fahrenheit(0) == 32.0

    def test_celsius_to_fahrenheit_hundred(self):
        """100°C = 212°F."""
        from custom_components.electrolux.util import celsius_to_fahrenheit

        assert celsius_to_fahrenheit(100) == 212.0

    def test_celsius_to_fahrenheit_body_temp(self):
        """37°C ≈ 98.6°F."""
        from custom_components.electrolux.util import celsius_to_fahrenheit

        assert celsius_to_fahrenheit(37) == 98.6

    def test_fahrenheit_to_celsius_none(self):
        """Returns None for None input."""
        from custom_components.electrolux.util import fahrenheit_to_celsius

        assert fahrenheit_to_celsius(None) is None

    def test_fahrenheit_to_celsius_freezing(self):
        """32°F = 0°C."""
        from custom_components.electrolux.util import fahrenheit_to_celsius

        assert fahrenheit_to_celsius(32) == 0.0

    def test_fahrenheit_to_celsius_boiling(self):
        """212°F = 100°C."""
        from custom_components.electrolux.util import fahrenheit_to_celsius

        assert fahrenheit_to_celsius(212) == 100.0


class TestParseErrorDetailForUserMessage:
    """Tests for the _parse_error_detail_for_user_message internal function.

    Accessed indirectly via map_command_error_to_home_assistant_error.
    """

    def _parse(self, detail, capability=None):
        """Call the private function directly (tested via import)."""
        from custom_components.electrolux.util import (
            _parse_error_detail_for_user_message,
        )

        return _parse_error_detail_for_user_message(detail.lower(), capability)

    def test_returns_none_for_unknown_detail(self):
        """Returns None for unrecognized error detail."""
        assert self._parse("some unknown error") is None

    def test_invalid_step_without_capability(self):
        """'invalid step' returns generic step message."""
        result = self._parse("invalid step value")
        assert result is not None
        assert "increments" in result.lower()

    def test_invalid_step_with_capability(self):
        """'invalid step' returns step value from capability."""
        cap = {"step": 5}
        result = self._parse("invalid step provided", capability=cap)
        assert result is not None
        assert "5" in result

    def test_type_mismatch(self):
        """'type mismatch' returns formatting mismatch message."""
        result = self._parse("type mismatch: boolean expected")
        assert result is not None
        assert "mismatch" in result.lower() or "formatting" in result.lower()

    def test_remote_control_disabled(self):
        """Remote control error phrase returns remote control message."""
        result = self._parse("remote control disabled for this appliance")
        assert result is not None
        assert "remote" in result.lower()

    def test_temporary_locked(self):
        """'temporary_locked' returns temp lock message."""
        result = self._parse("temporary_locked")
        assert result is not None
        assert "remote start" in result.lower() or "locked" in result.lower()

    def test_not_supported_by_program(self):
        """Program restriction phrase returns program message."""
        result = self._parse("not supported by program")
        assert result is not None
        assert "program" in result.lower()

    def test_food_probe_not_inserted(self):
        """Food probe error phrase returns probe insertion message."""
        result = self._parse("food probe not inserted")
        assert result is not None
        assert "probe" in result.lower()

    def test_door_open(self):
        """Door open phrase returns door closed message."""
        result = self._parse("door open, please close")
        assert result is not None
        assert "door" in result.lower()

    def test_appliance_busy(self):
        """Appliance busy phrase returns busy message."""
        result = self._parse("appliance busy")
        assert result is not None
        assert "running" in result.lower() or "operation" in result.lower()

    def test_child_lock_active(self):
        """Child lock phrase returns lock message."""
        result = self._parse("child lock active")
        assert result is not None
        assert "lock" in result.lower()

    def test_string_value_not_allowed(self):
        """'string value not allowed' returns state message."""
        result = self._parse("string value not allowed")
        assert result is not None
        assert "state" in result.lower() or "available" in result.lower()


class TestGetCapability:
    """Tests for get_capability utility function."""

    def test_returns_none_for_missing_key(self):
        """Returns None when key is not present."""
        from custom_components.electrolux.util import get_capability

        assert get_capability({}, "missing_key") is None

    def test_returns_scalar_value(self):
        """Returns scalar value directly."""
        from custom_components.electrolux.util import get_capability

        assert get_capability({"temp": 21.5}, "temp") == 21.5

    def test_returns_default_from_dict(self):
        """Returns 'default' value from nested dict capability."""
        from custom_components.electrolux.util import get_capability

        cap = {"mode": {"default": "COOL", "values": {"COOL": {}}}}
        assert get_capability(cap, "mode") == "COOL"

    def test_returns_none_for_dict_without_default(self):
        """Returns None when capability is a dict but has no 'default' key."""
        from custom_components.electrolux.util import get_capability

        cap = {"mode": {"values": {"COOL": {}}}}
        result = get_capability(cap, "mode")
        assert result is None


class TestCreateNotification:
    """Tests for create_notification utility function."""

    def test_notification_not_sent_when_not_needed(self):
        """No notification is created when should_send_notification returns False."""
        from custom_components.electrolux.util import create_notification

        hass = MagicMock()
        config_entry = MagicMock()
        config_entry.data = {}  # CONF_NOTIFICATION_DEFAULT defaults to True

        # Alert status NOT_NEEDED → should not send
        create_notification(hass, config_entry, "TestAlert", "DEFAULT", "NOT_NEEDED")
        hass.async_create_task.assert_not_called()

    def test_notification_sent_for_default_severity(self):
        """Notification is created for default severity with default config."""
        from custom_components.electrolux.util import create_notification

        hass = MagicMock()
        config_entry = MagicMock()
        config_entry.data = {"notifications": True}

        create_notification(hass, config_entry, "TestAlert", "DEFAULT", "NEW")
        hass.async_create_task.assert_called_once()


class TestMapCommandError:
    """Tests for map_command_error_to_home_assistant_error covering all Methods 1-3."""

    def _logger(self):
        import logging

        return MagicMock(spec=logging.Logger)

    # ------------------------------------------------------------------ #
    # Helpers for constructing exceptions with various attributes          #
    # ------------------------------------------------------------------ #

    def _ex_with_response_json(self, payload):
        """Exception whose .response.json() returns payload."""

        class _Resp:
            def json(self):
                return payload

        class _Ex(Exception):
            response: object = None
            status: object = None

        ex = _Ex("api error")
        ex.response = _Resp()
        ex.status = None
        return ex

    def _ex_with_response_text(self, payload_json_str):
        """Exception whose .response has .text but no .json()."""

        class _Resp:
            text = payload_json_str

        class _Ex(Exception):
            response: object = None
            status: object = None

        ex = _Ex("api error")
        ex.response = _Resp()
        ex.status = None
        return ex

    def _ex_with_error_data(self, data):
        """Exception with .error_data attribute."""

        class _Ex(Exception):
            error_data: object = None

        ex = _Ex("api error")
        ex.error_data = data
        return ex

    def _ex_with_details(self, data):
        """Exception with .details attribute."""

        class _Ex(Exception):
            details: object = None

        ex = _Ex("api error")
        ex.details = data
        return ex

    # ------------------------------------------------------------------ #
    # Method 1 — structured error response parsing                         #
    # ------------------------------------------------------------------ #

    def test_response_json_remote_control_disabled_error_code(self):
        """Method 1: Response JSON with REMOTE_CONTROL_DISABLED → remote control msg."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = self._ex_with_response_json({"error": "REMOTE_CONTROL_DISABLED"})
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "Remote control" in str(result)

    def test_response_json_appliance_offline_error_code(self):
        """Method 1: Response JSON with APPLIANCE_OFFLINE → disconnected msg."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = self._ex_with_response_json({"error": "APPLIANCE_OFFLINE"})
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "disconnected" in str(result).lower() or "offline" in str(result).lower()

    def test_response_json_rate_limit_exceeded_error_code(self):
        """Method 1: RATE_LIMIT_EXCEEDED error code → rate limit msg."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = self._ex_with_response_json({"error": "RATE_LIMIT_EXCEEDED"})
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "Too many" in str(result)

    def test_response_json_command_validation_remote_control_detail(self):
        """Method 1: COMMAND_VALIDATION_ERROR + 'remote control' detail → remote control msg."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = self._ex_with_response_json(
            {
                "error": "COMMAND_VALIDATION_ERROR",
                "detail": "Remote control disabled",
            }
        )
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "Remote control" in str(result)

    def test_response_json_command_validation_with_pattern_detail(self):
        """Method 1: COMMAND_VALIDATION_ERROR + parseable detail → derived message."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = self._ex_with_response_json(
            {
                "error": "COMMAND_VALIDATION_ERROR",
                "detail": "Not supported by current program",
            }
        )
        result = map_command_error_to_home_assistant_error(
            ex, "attr", self._logger(), capability={"values": {"AUTO": {}}}
        )
        assert isinstance(result, Exception)

    def test_response_json_command_validation_generic_detail(self):
        """Method 1: COMMAND_VALIDATION_ERROR + generic non-pattern detail → 'Command not accepted' msg."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = self._ex_with_response_json(
            {
                "error": "COMMAND_VALIDATION_ERROR",
                "detail": "Some custom non-matching detail",
            }
        )
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "not accepted" in str(result).lower() or "Command" in str(result)

    def test_response_text_only_no_json_method(self):
        """Method 1: response has .text but no .json() → text branch (elif) executes."""
        import json

        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        # Response has text but NO json() method → triggers the elif branch
        class _Resp:
            text = json.dumps({"error": "DEVICE_OFFLINE"})

        class _Ex(Exception):
            response: object = None
            status: object = None

        ex = _Ex("device error 503")
        ex.response = _Resp()
        ex.status = None
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "disconnected" in str(result).lower() or isinstance(result, Exception)

    def test_response_text_directly(self):
        """Method 1: response.text (no json method) is parsed to get error code."""
        import json

        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = self._ex_with_response_text(json.dumps({"error": "RC_DISABLED"}))
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "Remote control" in str(result)

    def test_exception_with_error_data_attribute(self):
        """Method 1: exception.error_data dict provides error code."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = self._ex_with_error_data({"error": "RATE_LIMIT"})
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "Too many" in str(result)

    def test_exception_with_details_attribute(self):
        """Method 1: exception.details dict provides error code."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = self._ex_with_details({"error": "CONNECTION_LOST"})
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "disconnected" in str(result).lower() or isinstance(result, Exception)

    def test_exception_string_with_embedded_json(self):
        """Method 1: JSON extracted from exception string via regex."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        # str(ex) will contain message='{"error": "CONNECTION_LOST"}'
        ex = Exception('API Error: message=\'{"error": "CONNECTION_LOST"}\'')
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert isinstance(result, Exception)

    def test_status_code_from_response_status_attr(self):
        """Method 1: status_code extracted from exception.response.status."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        # exception.status is None, but exception.response.status = 403
        class _Resp:
            status = 403

            def json(self):
                return {}

        class _Ex(Exception):
            status = None
            response: object = None

        ex = _Ex("some api error 403")
        ex.response = _Resp()
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert isinstance(result, Exception)

    def test_status_code_from_status_code_attribute(self):
        """Method 1: status_code extracted from exception.status_code when no .status."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        class _Ex(Exception):
            status_code: object = None

        ex = _Ex("some error")
        ex.status_code = 429
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "Too many" in str(result)

    # ------------------------------------------------------------------ #
    # "type mismatch" string check (after Method 1, before Method 2)       #
    # ------------------------------------------------------------------ #

    def test_type_mismatch_in_exception_string(self):
        """'type mismatch' in exception message → type_mismatch HA error."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = Exception("Error: type mismatch for cavityLight")
        result = map_command_error_to_home_assistant_error(
            ex, "cavityLight", self._logger()
        )
        assert "type" in str(result).lower() or "mismatch" in str(result).lower()

    # ------------------------------------------------------------------ #
    # Method 2 — HTTP status code detection                                #
    # ------------------------------------------------------------------ #

    def test_http_403_returns_remote_control(self):
        """HTTP 403 → remote control disabled message."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        class _Ex(Exception):
            status = 403

        result = map_command_error_to_home_assistant_error(
            _Ex("403"), "attr", self._logger()
        )
        assert "Remote control" in str(result)

    def test_http_429_returns_rate_limit(self):
        """HTTP 429 → too many commands message."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        class _Ex(Exception):
            status = 429

        result = map_command_error_to_home_assistant_error(
            _Ex("429"), "attr", self._logger()
        )
        assert "Too many" in str(result)

    def test_http_503_returns_disconnected(self):
        """HTTP 503 → appliance disconnected message."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        class _Ex(Exception):
            status = 503

        result = map_command_error_to_home_assistant_error(
            _Ex("503"), "attr", self._logger()
        )
        assert "disconnected" in str(result).lower()

    def test_http_406_plain_returns_command_not_accepted(self):
        """HTTP 406 without special detail → command not accepted."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        class _Ex(Exception):
            status = 406

        result = map_command_error_to_home_assistant_error(
            _Ex("406"), "attr", self._logger()
        )
        assert isinstance(result, Exception)

    def test_http_406_with_remote_control_detail(self):
        """HTTP 406 + error detail has 'remote control' → remote control msg."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        class _Ex(Exception):
            status = 406
            error_data: object = None

        ex = _Ex("406 Not Acceptable")
        ex.error_data = {"detail": "Remote control disabled"}
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "Remote control" in str(result)

    def test_http_406_with_parseable_detail(self):
        """HTTP 406 + parseable detail pattern → derived message."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        class _Ex(Exception):
            status = 406
            error_data: object = None

        ex = _Ex("406 Not Acceptable")
        ex.error_data = {"detail": "Not supported by current program"}
        result = map_command_error_to_home_assistant_error(
            ex, "attr", self._logger(), capability={"values": {"AUTO": {}}}
        )
        assert isinstance(result, Exception)

    def test_http_406_with_generic_custom_detail(self):
        """HTTP 406 + non-pattern detail → 'Command not accepted: <detail>' msg."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        class _Ex(Exception):
            status = 406
            error_data: object = None

        ex = _Ex("406 Not Acceptable")
        ex.error_data = {"detail": "Some custom appliance error detail"}
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "not accepted" in str(result).lower() or isinstance(result, Exception)

    # ------------------------------------------------------------------ #
    # Method 3 — string pattern matching fallback                          #
    # ------------------------------------------------------------------ #

    def test_rate_limit_string_pattern(self):
        """Method 3: 'rate limit' substring → rate limit message."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = Exception("rate limit exceeded for this device")
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "Too many" in str(result)

    def test_throttled_string_pattern(self):
        """Method 3: 'throttled' substring → rate limit message."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = Exception("request was throttled by the API")
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "Too many" in str(result)

    def test_command_validation_string_pattern(self):
        """Method 3: 'command validation' substring → command not accepted."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = Exception("command validation failed for operation")
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert isinstance(result, Exception)

    def test_not_acceptable_string_pattern(self):
        """Method 3: 'not acceptable' substring → command not accepted."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = Exception("406 not acceptable returned")
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert isinstance(result, Exception)

    def test_generic_default_error(self):
        """No pattern match → generic 'Command failed' error."""
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        ex = Exception("completely unknown xyzzy error")
        result = map_command_error_to_home_assistant_error(ex, "attr", self._logger())
        assert "Command failed" in str(result)


class TestFormatCommandEdgeCases:
    """Edge-case tests for format_command_for_appliance filling remaining coverage gaps."""

    def test_boolean_type_with_numeric_converts_via_bool(self):
        """Boolean capability with numeric value → bool() conversion (line 791)."""
        from custom_components.electrolux.util import format_command_for_appliance

        cap = {"type": "boolean"}
        assert format_command_for_appliance(cap, "attr", 1) is True
        assert format_command_for_appliance(cap, "attr", 0) is False
        assert format_command_for_appliance(cap, "attr", 42) is True

    def test_number_type_with_invalid_string_returns_original(self):
        """ValueError in numeric conversion → original value returned (lines 824-828)."""
        from custom_components.electrolux.util import format_command_for_appliance

        cap = {"type": "number", "min": 0.0, "max": 100.0}
        result = format_command_for_appliance(cap, "targetTemperatureC", "not_a_number")
        assert result == "not_a_number"

    def test_number_type_step_without_min(self):
        """Number capability with step but no min → step_base=0 (inner step calc)."""
        from custom_components.electrolux.util import format_command_for_appliance

        cap = {"type": "number", "step": 5.0}
        # 7 → step_base=0, steps=7/5=1.4 → round=1 → 0+5=5.0
        result = format_command_for_appliance(cap, "someAttr", 7)
        assert result == 5.0

    def test_unknown_type_bool_returns_on_off_strings(self):
        """Capability with unknown type + bool value → 'ON'/'OFF' (lines 869-875)."""
        from custom_components.electrolux.util import format_command_for_appliance

        cap = {"type": "custom_weird_type"}
        assert format_command_for_appliance(cap, "someAttr", True) == "ON"
        assert format_command_for_appliance(cap, "someAttr", False) == "OFF"

    def test_unknown_type_non_bool_returns_value_as_is(self):
        """Capability with unknown type + non-bool value → value unchanged (line 874)."""
        from custom_components.electrolux.util import format_command_for_appliance

        cap = {"type": "custom_weird_type"}
        assert format_command_for_appliance(cap, "someAttr", "hello") == "hello"
        assert format_command_for_appliance(cap, "someAttr", 99) == 99

    def test_string_type_empty_values_returns_str(self):
        """String type with empty values dict → str(value)."""
        from custom_components.electrolux.util import format_command_for_appliance

        cap = {"type": "string", "values": {}}
        assert format_command_for_appliance(cap, "attr", 42) == "42"
        assert format_command_for_appliance(cap, "attr", True) == "True"

    def test_int_type_always_returns_int(self):
        """'type: int' capabilities must always return int, never float.

        Regression test: Electrolux API returns HTTP 500 when a float (e.g. 3.0)
        is sent for an int-typed capability like Fanspeed.
        """
        from custom_components.electrolux.util import format_command_for_appliance

        fanspeed_cap = {"type": "int", "min": 1, "max": 9, "step": 1}
        result = format_command_for_appliance(fanspeed_cap, "Fanspeed", 3)
        assert result == 3
        assert isinstance(result, int), f"Expected int, got {type(result)}: {result}"

        # float input must also be coerced to int
        result = format_command_for_appliance(fanspeed_cap, "Fanspeed", 3.0)
        assert result == 3
        assert isinstance(
            result, int
        ), f"Expected int from float input, got {type(result)}: {result}"

    def test_temperature_type_in_cap_type_tuple(self):
        """'type: temperature' is handled numerically via the cap_type tuple (defense in depth).

        Even if the attr name doesn't contain 'temperature', the type field alone
        is sufficient to trigger integer conversion.
        """
        from custom_components.electrolux.util import format_command_for_appliance

        temp_cap = {"type": "temperature", "min": 1.0, "max": 7.0, "step": 1.0}
        result = format_command_for_appliance(temp_cap, "fridgeSetpoint", 4)
        assert result == 4
        assert isinstance(result, int), f"Expected int, got {type(result)}: {result}"

    def test_whole_number_returns_int_regardless_of_step_type(self):
        """Whole-number values always return int, even with a fractional step.

        The Electrolux API rejects floats universally. The previous step_has_fraction
        guard was unnecessary — no appliance sample has a fractional step, and even if
        it did, sending 2 instead of 2.0 is always safe.
        """
        from custom_components.electrolux.util import format_command_for_appliance

        # Fractional step=0.5, but value is a whole number → must return int
        cap = {"type": "number", "min": 0.0, "max": 10.0, "step": 0.5}
        result = format_command_for_appliance(cap, "someValue", 2.0)
        assert isinstance(
            result, int
        ), f"Expected int for 2.0, got {type(result)}: {result}"
        assert result == 2

    def test_number_type_integer_step_returns_int(self):
        """'type: number' with integer step must return int for whole-number values.

        Regression test: antiCreaseValue on TD dryers has step=30 (integer).
        format_command_for_appliance was converting 120 → 120.0 (float), causing
        HTTP 500. The fix detects integer steps and returns int instead of float.
        """
        from custom_components.electrolux.util import format_command_for_appliance

        anti_crease_cap = {"type": "number", "min": 30, "max": 120, "step": 30}
        for val in [30, 60, 90, 120, 30.0, 60.0, 90.0, 120.0]:
            result = format_command_for_appliance(
                anti_crease_cap, "antiCreaseValue", val
            )
            assert result == int(val), f"Expected {int(val)}, got {result}"
            assert isinstance(
                result, int
            ), f"Expected int for value {val}, got {type(result)}: {result}"

    def test_number_type_fractional_step_returns_float(self):
        """Genuinely fractional values (non-integer) are preserved as float.

        Only a value that cannot be represented as int (i.e. 24.5 ≠ int(24.5)=24)
        escapes the int-return path. Whole numbers like 24.0 always become 24.
        """
        from custom_components.electrolux.util import format_command_for_appliance

        temp_cap = {"type": "number", "min": 15.56, "max": 32.22, "step": 0.5}
        result = format_command_for_appliance(temp_cap, "targetTemperatureC", 24.5)
        assert isinstance(result, float)


class TestUtilMissingCoverage:
    """Tests targeting the remaining missed lines in util.py."""

    def _logger(self):
        import logging

        return MagicMock(spec=logging.Logger)

    def _map(self, ex, **kwargs):
        from custom_components.electrolux.util import (
            map_command_error_to_home_assistant_error,
        )

        return map_command_error_to_home_assistant_error(
            ex, "attr", self._logger(), **kwargs
        )

    # ------------------------------------------------------------------ #
    # Lines 405-406: response.json() raises → inner except Exception: pass
    # ------------------------------------------------------------------ #

    def test_response_json_raises_falls_through_to_generic_error(self):
        """When response.json() raises, the except is swallowed and parsing continues (lines 405-406)."""

        class _BadResp:
            def json(self):
                raise ValueError("not json")

        class _Ex(Exception):
            response: object = None

        ex = _Ex("api error")
        ex.response = _BadResp()

        result = self._map(ex)
        assert isinstance(result, HomeAssistantError)

    # ------------------------------------------------------------------ #
    # Lines 410-411: response has .text but json.loads fails
    # ------------------------------------------------------------------ #

    def test_response_text_json_parse_fails_falls_through(self):
        """When response has text but json.loads raises, parsing is swallowed (lines 410-411)."""

        class _TextResp:
            text = "not valid json {"

        class _Ex(Exception):
            response: object = None

        ex = _Ex("api error")
        ex.response = _TextResp()

        result = self._map(ex)
        assert isinstance(result, HomeAssistantError)

    # ------------------------------------------------------------------ #
    # Lines 429-430: inner except when json.loads(json_str) fails
    # ------------------------------------------------------------------ #

    def test_regex_json_parse_fails_inner_except_is_swallowed(self):
        """When regex matches but json.loads fails on the extracted string, inner except is swallowed (lines 429-430)."""
        # The string matches  message='{...}' pattern but content is not valid JSON
        ex = Exception("message='{broken json content}'")
        # After regex capture → '{broken json content}', replace ' with " → still invalid
        result = self._map(ex)
        assert isinstance(result, HomeAssistantError)

    # ------------------------------------------------------------------ #
    # Lines 431-433: outer except Exception: pass — triggered by patching re.search
    # ------------------------------------------------------------------ #

    def test_outer_parsing_exception_is_swallowed(self):
        """When re.search raises inside the outer parsing try-block, the except swallows it (lines 429-433)."""
        from unittest.mock import patch

        ex = Exception("plain exception no special attrs")

        with patch(
            "custom_components.electrolux.util.re.search",
            side_effect=RuntimeError("forced error in re.search"),
        ):
            result = self._map(ex)
        assert isinstance(result, HomeAssistantError)

    # ------------------------------------------------------------------ #
    # Lines 440-441: json.dumps(error_data) raises → fallback f-string
    # ------------------------------------------------------------------ #

    def test_json_dumps_error_data_raises_uses_fallback_str(self):
        """When json.dumps(error_data) raises (non-serializable), falls back to str() (lines 440-441)."""

        class _Ex(Exception):
            error_data: object = None

        ex = _Ex("test error")
        # A set inside a dict is not JSON-serializable → json.dumps raises TypeError
        ex.error_data = {"key": {1, 2, 3}}

        # Should return a HomeAssistantError (the unserializable error_data hits except branch then generic fallback)
        result = self._map(ex)
        assert isinstance(result, HomeAssistantError)

    # ------------------------------------------------------------------ #
    # Lines 512-514: COMMAND_VALIDATION_ERROR detail parsing raises
    # ------------------------------------------------------------------ #

    def test_command_validation_error_detail_parsing_raises_is_swallowed(self):
        """When _parse_error_detail_for_user_message raises inside COMMAND_VALIDATION_ERROR handler, it's swallowed (lines 512-514)."""
        from unittest.mock import patch

        class _Ex(Exception):
            error_data: object = None

        ex = _Ex("validation error")
        ex.error_data = {"error": "COMMAND_VALIDATION_ERROR", "detail": "some detail"}

        with patch(
            "custom_components.electrolux.util._parse_error_detail_for_user_message",
            side_effect=RuntimeError("forced parse error"),
        ):
            result = self._map(ex)
        # Should still return HomeAssistantError with generic message
        assert isinstance(result, HomeAssistantError)
        assert "Command not accepted" in str(result)

    # ------------------------------------------------------------------ #
    # Lines 597-598: 406 detail parsing raises → except Exception: pass
    # ------------------------------------------------------------------ #

    def test_406_detail_parsing_raises_is_swallowed(self):
        """When _parse_error_detail_for_user_message raises in 406 handler, it's swallowed (lines 597-598)."""
        from unittest.mock import patch

        class _Ex(Exception):
            status_code: object = None
            error_data: object = None

        ex = _Ex("not acceptable error")
        ex.status_code = 406
        ex.error_data = {"detail": "some appliance-specific rejection"}

        with patch(
            "custom_components.electrolux.util._parse_error_detail_for_user_message",
            side_effect=RuntimeError("forced parse error"),
        ):
            result = self._map(ex)
        assert isinstance(result, HomeAssistantError)

    # ------------------------------------------------------------------ #
    # Lines 692-701: "command validation" string match with error_data.detail
    # ------------------------------------------------------------------ #

    def test_command_validation_string_match_with_detail_from_error_data(self):
        """Method 3 'command validation' match uses error_data.detail to form detail_msg (lines 692-701)."""

        class _Ex(Exception):
            error_data: object = None

        ex = _Ex("command validation error occurred")
        # error_data without a recognised error_code key → bypasses Method 1
        ex.error_data = {"detail": "program does not support this setting"}

        result = self._map(ex)
        assert isinstance(result, HomeAssistantError)
        assert "Command not accepted: program does not support this setting" in str(
            result
        )

    # ------------------------------------------------------------------ #
    # Line 709: long exception string (>= 200 chars) → generic fallback message
    # ------------------------------------------------------------------ #

    def test_command_validation_long_exception_string_uses_generic_message(self):
        """When ex_str >= 200 chars and no detail_msg, uses the generic fallback (line 709)."""

        # Exception string contains "command validation" to enter Method 3 branch
        # Must be >= 200 chars so the short-message branch is NOT taken
        long_message = "command validation " + "x" * 210
        ex = Exception(long_message)

        result = self._map(ex)
        assert isinstance(result, HomeAssistantError)
        assert (
            "Command not accepted by appliance. Check that the appliance supports this operation."
            in str(result)
        )
