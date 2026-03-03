"""Exceptions and shared error constants for the Electrolux integration."""

# Common error pattern phrases reused across error-handling functions
REMOTE_CONTROL_ERROR_PHRASES = [
    "remote control disabled",
    "remote control not enabled",
    "remote control is not enabled",
    "remote control not active",
    "remote control is not active",
    "remote control off",
    "rc disabled",
    "rc not enabled",
    "rc not active",
]


class CommandError(Exception):
    """Base exception for command errors."""

    pass


class RemoteControlDisabledError(CommandError):
    """Remote control is disabled."""

    pass


class ApplianceOfflineError(CommandError):
    """Appliance is disconnected."""

    pass


class CommandValidationError(CommandError):
    """Command validation failed."""

    pass


class RateLimitError(CommandError):
    """Rate limit exceeded."""

    pass


class AuthenticationError(CommandError):
    """Authentication failed - tokens expired or invalid."""

    pass


class NetworkError(CommandError):
    """Network connectivity error."""

    pass
