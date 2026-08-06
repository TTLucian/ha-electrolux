"""Detection of genuine authentication failures.

Command validation failures are a documented, expected part of the Electrolux
API. Sending a command runs three validation phases and any of them can answer
``406 Not Acceptable`` with a ``COMMAND_VALIDATION_ERROR`` body, for example
``{"detail": "Remote control disabled"}`` or ``{"detail": "Appliance
disconnected"}``. Those are ordinary rejections and the user has to change
something on the appliance, not re-authenticate.

Deciding this from the text of the exception is unsafe, because the string form
of an aiohttp error embeds the request URL, and the request URL embeds the
appliance id. Appliance ids are hex, so an id such as
``916900511_01:54926920-443E07773401`` contains ``401`` and matches a bare
``"401"`` substring on every failure that appliance ever produces.

Prefer the HTTP status, and when a status is known treat it as authoritative.
"""

from __future__ import annotations

import re

AUTH_STATUS_CODES = (401, 403)

# Phrases that unambiguously describe rejected credentials. Deliberately no bare
# "401", "token" or "auth": all three match text that is not about
# authentication, most importantly the request URL.
AUTH_ERROR_PHRASES = (
    "unauthorized",
    "forbidden",
    "invalid grant",
    "invalid_grant",
    "invalid_token",
    "invalid refresh token",
    "refresh token is invalid",
    "refresh token expired",
    "authentication failed",
    "authentication error",
    "authentication required",
)

# Wording around an expired token varies ("token expired", "token has
# expired", "access token is expired"), so match the pair rather than a phrase.
_EXPIRED_TOKEN = re.compile(
    r"\btoken\b.{0,24}?\bexpired\b|\bexpired\b.{0,24}?\btoken\b"
)

# aiohttp renders its errors as "<prefix>: 406, message='...', url='...'".
_STATUS_IN_MESSAGE = re.compile(r"\b(\d{3}),\s*message=")


def get_error_status(ex: BaseException) -> int | None:
    """Return the HTTP status behind an exception, if it can be determined."""
    for attribute in ("status", "status_code"):
        status = getattr(ex, attribute, None)
        if isinstance(status, int):
            return status

    response = getattr(ex, "response", None)
    if response is not None:
        for attribute in ("status", "status_code"):
            status = getattr(response, attribute, None)
            if isinstance(status, int):
                return status

    match = _STATUS_IN_MESSAGE.search(str(ex))
    if match:
        return int(match.group(1))

    return None


def is_auth_error(
    ex: BaseException, *, auth_statuses: tuple[int, ...] = AUTH_STATUS_CODES
) -> bool:
    """Return True only for failures that re-authenticating can fix.

    A known status decides on its own, so a 406 command validation error, a 429
    rate limit or a 500 are never reported as authentication problems. Phrase
    matching is only a fallback for exceptions that carry no status at all.

    Callers that give 403 its own meaning can narrow ``auth_statuses``.
    """
    status = get_error_status(ex)
    if status is not None:
        return status in auth_statuses

    message = str(ex).lower()
    if _EXPIRED_TOKEN.search(message):
        return True
    return any(phrase in message for phrase in AUTH_ERROR_PHRASES)
