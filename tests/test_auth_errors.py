"""Tests for authentication error detection.

The important case is a command validation failure: the API answers 406 with a
COMMAND_VALIDATION_ERROR body, and that must never be treated as an
authentication problem, no matter what the error text happens to contain.
"""

from __future__ import annotations

import pytest

from custom_components.electrolux.auth_errors import get_error_status, is_auth_error

# An appliance id containing "401", which is what made string matching unsafe.
APPLIANCE_URL = (
    "url='https://api.developer.electrolux.one/api/v1/appliances/"
    "916900511_01:54926920-443E07773401/command'"
)


def api_error(status: int, detail: str) -> Exception:
    """Build an exception shaped like the one the SDK raises."""
    return Exception(
        f"Failed to send command: {status}, "
        f"message=\"{{'error': 'COMMAND_VALIDATION_ERROR', "
        f"'message': 'Command validation failed', 'detail': '{detail}'}}\", "
        f"{APPLIANCE_URL}"
    )


class StatusError(Exception):
    """Exception exposing a status attribute, like aiohttp's."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


class ResponseError(Exception):
    """Exception exposing the status on a nested response object."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.response = StatusError(message, status)


class TestCommandValidationIsNotAuth:
    """406 command validation errors are ordinary rejections."""

    @pytest.mark.parametrize(
        "detail",
        [
            "Remote control disabled",
            "Appliance disconnected",
            "String value not allowed",
        ],
    )
    def test_406_is_not_an_auth_error(self, detail):
        """A documented command validation failure is not an auth failure."""
        assert is_auth_error(api_error(406, detail)) is False

    def test_401_inside_the_appliance_id_does_not_count(self):
        """The appliance id in the URL must not drive the decision."""
        assert "401" in APPLIANCE_URL
        assert is_auth_error(api_error(500, "Internal error")) is False

    def test_rate_limit_is_not_an_auth_error(self):
        """A 429 must not trigger reauthentication."""
        assert is_auth_error(api_error(429, "Too Many Requests")) is False


class TestGenuineAuthErrors:
    """401 and 403 are the statuses that reauthentication can fix."""

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_statuses_are_detected(self, status):
        """Auth statuses are reported as auth errors."""
        assert is_auth_error(api_error(status, "Unauthorized")) is True

    def test_status_attribute_is_used(self):
        """A status attribute is enough, with no parsable message."""
        assert is_auth_error(StatusError("boom", 401)) is True
        assert is_auth_error(StatusError("boom", 406)) is False

    def test_nested_response_status_is_used(self):
        """A status on a nested response object is enough."""
        assert is_auth_error(ResponseError("boom", 403)) is True
        assert is_auth_error(ResponseError("boom", 500)) is False

    @pytest.mark.parametrize(
        "message",
        [
            "unauthorized access denied",
            "invalid grant error",
            "token expired",
            "authentication failed",
            "403 forbidden",
        ],
    )
    def test_phrases_still_work_without_a_status(self, message):
        """Exceptions carrying no status fall back to phrase matching."""
        assert is_auth_error(Exception(message)) is True

    def test_plain_network_error_is_not_auth(self):
        """An ordinary connection failure is not an auth error."""
        assert is_auth_error(Exception("Cannot connect to host")) is False


class TestGetErrorStatus:
    """Status extraction covers the shapes the SDK produces."""

    def test_status_parsed_from_message(self):
        """The status is read out of the aiohttp string form."""
        assert get_error_status(api_error(406, "Remote control disabled")) == 406

    def test_attribute_wins_over_message(self):
        """An explicit attribute is preferred over the message text."""
        assert get_error_status(StatusError("500, message='x'", 403)) == 403

    def test_missing_status_returns_none(self):
        """Nothing to parse means no status."""
        assert get_error_status(Exception("no status here")) is None
