"""Token management for the Electrolux integration."""

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable

import jwt
from electrolux_group_developer_sdk.auth.token_manager import (
    TokenManager,  # type: ignore[import-untyped]
)
from electrolux_group_developer_sdk.client.client_util import (
    request,  # type: ignore[import-untyped]
)
from electrolux_group_developer_sdk.config import (
    TOKEN_REFRESH_URL,  # type: ignore[import-untyped]
)
from electrolux_group_developer_sdk.constants import (  # type: ignore[import-untyped]
    POST,
    REFRESH_TOKEN,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import ACCESS_TOKEN_VALIDITY_SECONDS

_LOGGER: logging.Logger = logging.getLogger(__package__)

# Progressive exponential backoff settings for token refresh failures
BASE_REFRESH_BACKOFF_SECONDS = 15.0
MAX_REFRESH_BACKOFF_SECONDS = 300.0  # 5 minutes max cooldown
PROACTIVE_REFRESH_BUFFER_SECONDS = 900  # 15 minutes before expiry


class ElectroluxTokenManager(TokenManager):
    """Custom token manager with extended proactive refresh buffer.

    Extends the SDK's TokenManager to use a 15-minute safety buffer
    instead of the default 60 seconds, enabling proactive token refresh
    before expiry to ensure seamless operation.
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        api_key: str,
        on_token_update: Callable[[str, str, str], None] | None = None,
    ):
        """Initialize the custom token manager."""
        super().__init__(access_token, refresh_token, api_key, on_token_update=on_token_update)
        self._on_token_update_with_expiry: Callable[[str, str, str, int], None] | None = None
        self._on_auth_error: Callable[[str], Awaitable[None]] | None = None
        self._refresh_lock = asyncio.Lock()
        self._last_failed_refresh: float = 0.0  # Track timestamp of failed refresh attempt
        self._consecutive_failures: int = 0  # Track consecutive refresh failures for backoff
        self._current_backoff: float = 0.0  # Current effective backoff delay with jitter
        self._permanent_auth_failure: bool = False  # Set on 401/invalid-grant; stops retry loop until new creds
        self._last_log_time: float = 0.0  # Cache timestamp for log throttling
        self._last_log_status: str = ""  # Cache last logged status

    def is_token_valid(self) -> bool:
        """Check token validity with 15-minute proactive refresh buffer.

        Overrides SDK's default 60-second buffer to enable earlier proactive
        refresh, preventing 401 errors during normal operation.

        Returns:
            bool: True if token is valid and has >15 minutes remaining.
        """
        # Check if auth data exists
        if not self._auth_data or not self._auth_data.access_token:
            _LOGGER.debug("[TOKEN-CHECK] Token validation failed: No access token available")
            return False

        try:
            payload = jwt.decode(
                self._auth_data.access_token,
                options={"verify_signature": False, "verify_exp": False},
            )
            exp = payload.get("exp")
            if exp is None:
                _LOGGER.debug("[TOKEN-CHECK] Token validation failed: JWT missing 'exp' claim")
                return False

            current_time = time.time()
            time_remaining = exp - current_time
            is_valid = time_remaining > PROACTIVE_REFRESH_BUFFER_SECONDS

            # Format time remaining as hours and minutes
            hours = int(time_remaining // 3600)
            minutes = int((time_remaining % 3600) // 60)

            if not is_valid:
                status_msg = f"expiring: {hours}h {minutes}m"
                time_since_log = current_time - self._last_log_time
                if self._last_log_status != status_msg or time_since_log >= 30:
                    _LOGGER.info(
                        f"[TOKEN-CHECK] Token expiring soon: {hours} hours, {minutes} minutes remaining (< 15 min buffer), "
                        f"triggering proactive refresh"
                    )
                    self._last_log_time = current_time
                    self._last_log_status = status_msg
            else:
                # Only log if status changed or 30+ seconds since last log (reduce noise)
                status_msg = f"valid: {hours}h {minutes}m"
                time_since_log = current_time - self._last_log_time
                if self._last_log_status != status_msg or time_since_log >= 30:
                    _LOGGER.debug(f"[TOKEN-CHECK] Token valid: {hours} hours, {minutes} minutes remaining")
                    self._last_log_time = current_time
                    self._last_log_status = status_msg

            return is_valid

        except jwt.ExpiredSignatureError:
            _LOGGER.info("[TOKEN-CHECK] Access token already expired, refresh required")
            return False
        except Exception as e:
            _LOGGER.error(f"[TOKEN-CHECK] Token validation error: {e}")
            _LOGGER.debug(f"[TOKEN-CHECK] Validation exception details: {type(e).__name__}: {e!s}")
            return False  # Force refresh if we can't decode JWT

    def set_token_update_callback_with_expiry(self, callback: Callable[[str, str, str, int], None]) -> None:
        """Set callback that includes expiration timestamp."""
        self._on_token_update_with_expiry = callback

    def set_auth_error_callback(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """Set callback for authentication errors."""
        self._on_auth_error = callback

    def _calculate_backoff(self) -> float:
        """Calculate progressive exponential backoff delay with jitter."""
        # Progressive backoff: 15s -> 30s -> 60s -> 120s -> 240s -> 300s (capped)
        multiplier = 2 ** min(self._consecutive_failures - 1, 5) if self._consecutive_failures > 0 else 1
        raw_backoff = min(BASE_REFRESH_BACKOFF_SECONDS * multiplier, MAX_REFRESH_BACKOFF_SECONDS)
        # Apply ±10% jitter to prevent synchronized retry spikes
        jitter = random.uniform(0.9, 1.1)
        return round(raw_backoff * jitter, 1)

    async def refresh_token(self) -> bool:
        """Refresh the access token with race condition protection and strict backoff.

        This method is thread-safe and can be called concurrently from anywhere.
        It acquires the refresh lock internally to prevent race conditions when
        multiple API calls trigger refresh simultaneously.

        Returns:
            bool: True if refresh succeeded, False otherwise.
        """
        async with self._refresh_lock:
            current_time = time.time()
            _LOGGER.debug(f"[TOKEN-REFRESH] Refresh initiated at {int(current_time)}")

            # Stop immediately if credentials are known-bad (permanent 401)
            # Only reset after user provides new credentials via reauth flow
            if self._permanent_auth_failure:
                _LOGGER.debug(
                    "[TOKEN-REFRESH] Skipping refresh: permanent auth failure active. "
                    "User must re-enter credentials via the HA notification."
                )
                return False

            # Double-check if token is still invalid (another task may have refreshed while we waited)
            if self.is_token_valid():
                _LOGGER.debug("[TOKEN-REFRESH] Token already fresh (refreshed by concurrent task), skipping refresh")
                return True

            # Check retry cooldown: strictly enforce backoff delay on failures
            if self._consecutive_failures > 0 and self._last_failed_refresh > 0:
                time_since_failure = current_time - self._last_failed_refresh
                if time_since_failure < self._current_backoff:
                    cooldown_remaining = self._current_backoff - time_since_failure
                    _LOGGER.warning(
                        f"[TOKEN-REFRESH] Refresh on cooldown: {self._consecutive_failures} previous failures, "
                        f"{cooldown_remaining:.0f}s remaining (backoff: {self._current_backoff:.0f}s)"
                    )
                    return False

            _LOGGER.debug("[TOKEN-REFRESH] Preparing token refresh request")
            auth_data = self._auth_data

            if not auth_data or auth_data.refresh_token is None:
                _LOGGER.error("[TOKEN-REFRESH] CRITICAL: Refresh token is missing, cannot refresh")
                raise ConfigEntryAuthFailed("Missing refresh token")

            payload = {REFRESH_TOKEN: auth_data.refresh_token}
            # Redact sensitive token in logs
            refresh_suffix = auth_data.refresh_token[-5:] if len(auth_data.refresh_token) >= 5 else "<short>"
            _LOGGER.debug(
                f"[TOKEN-REFRESH] Sending refresh request to {TOKEN_REFRESH_URL} (token suffix: ...{refresh_suffix})"
            )

            try:
                _LOGGER.debug("[TOKEN-REFRESH] Making HTTP POST request to token endpoint")
                data = await request(method=POST, url=TOKEN_REFRESH_URL, json_body=payload)
                _LOGGER.debug("[TOKEN-REFRESH] HTTP request successful, processing response")

                # Calculate expiration timestamp from response
                expires_in = data.get("expiresIn", ACCESS_TOKEN_VALIDITY_SECONDS)
                expires_at = int(time.time()) + expires_in

                # Format expiration as hours and minutes
                exp_hours = int(expires_in // 3600)
                exp_minutes = int((expires_in % 3600) // 60)

                _LOGGER.debug(
                    f"[TOKEN-REFRESH] New token received: expires in {exp_hours} hours, {exp_minutes} minutes"
                )
                _LOGGER.debug(f"[TOKEN-REFRESH] Token expiration timestamp: {expires_at}")

                # Log token rotation (suffix of new refresh token)
                new_refresh_suffix = data.get("refreshToken", "")[-5:] if data.get("refreshToken") else "<none>"
                _LOGGER.debug(
                    f"[TOKEN-REFRESH] Token rotation: old suffix ...{refresh_suffix} -> new suffix ...{new_refresh_suffix}"
                )

                # Update with new tokens
                _LOGGER.debug("[TOKEN-REFRESH] Updating token manager with new tokens")
                self.update_with_expiry(
                    access_token=data["accessToken"],
                    refresh_token=data["refreshToken"],
                    api_key=auth_data.api_key,
                    expires_at=expires_at,
                )

                # Clear failed refresh counter on success
                self._last_failed_refresh = 0.0
                self._consecutive_failures = 0  # Reset exponential backoff
                self._current_backoff = 0.0
                self._permanent_auth_failure = False  # New creds worked — clear the latch
                _LOGGER.info(
                    f"[TOKEN-REFRESH] Token refresh completed successfully (new token valid for {exp_hours} hours, {exp_minutes} minutes)"
                )
                return True

            except Exception as e:
                error_msg = str(e).lower()
                _LOGGER.error(f"[TOKEN-REFRESH] Token refresh failed: {type(e).__name__}: {e}")
                _LOGGER.debug(f"[TOKEN-REFRESH] Full error details: {error_msg}")

                # Classify permanent vs transient error
                # Permanent auth errors are evaluated unconditionally first so compound
                # messages (e.g. "401 connection reset") strictly trigger reauth latch.
                is_permanent = any(
                    kw in error_msg
                    for kw in [
                        "401",
                        "invalid grant",
                        "invalid_grant",
                        "forbidden",
                        "unauthorized",
                        "invalid token",
                        "invalid_token",
                    ]
                )
                is_transient = not is_permanent and any(
                    kw in error_msg
                    for kw in [
                        "429",
                        "500",
                        "502",
                        "503",
                        "504",
                        "timeout",
                        "temporarily unavailable",
                        "rate limit",
                        "connector",
                        "connection",
                        "reset",
                    ]
                )
                _LOGGER.debug(
                    f"[TOKEN-REFRESH] Error classification: permanent={is_permanent}, transient={is_transient}"
                )

                if is_permanent:
                    _LOGGER.error(f"[TOKEN-REFRESH] PERMANENT AUTH ERROR detected: {error_msg}")
                    # Check for possible multiple instance issue
                    if "invalid grant" in error_msg and self._consecutive_failures == 0:
                        _LOGGER.error(
                            "[TOKEN-REFRESH] Refresh token became invalid unexpectedly (zero failures). "
                            "This may indicate multiple Home Assistant instances using same credentials, "
                            "which is NOT supported due to single-use refresh tokens."
                        )
                    # Latch: stop all future refresh attempts until new credentials are loaded
                    self._permanent_auth_failure = True
                    self._consecutive_failures = 0
                    self._current_backoff = 0.0
                    # Trigger reauthentication once
                    if self._on_auth_error:
                        _LOGGER.warning(
                            "[TOKEN-REFRESH] Triggering reauth callback due to permanent auth error "
                            "(further refresh attempts suppressed until credentials are updated)"
                        )
                        await self._on_auth_error(f"Token refresh failed: {e}")
                    else:
                        _LOGGER.warning("[TOKEN-REFRESH] No auth error callback registered, cannot trigger reauth")
                    return False

                # For transient/other errors, set cooldown and return False
                self._last_failed_refresh = current_time
                self._consecutive_failures += 1
                self._current_backoff = self._calculate_backoff()
                _LOGGER.warning(
                    f"[TOKEN-REFRESH] Temporary refresh failure (will retry with backoff): {e}. "
                    f"Failure tracking: consecutive_failures={self._consecutive_failures}, "
                    f"next_backoff={self._current_backoff:.0f}s"
                )
                return False

    def update_with_expiry(self, access_token: str, refresh_token: str, api_key: str, expires_at: int) -> None:
        """Update the authentication data with expiration information.

        Calls both the extended callback (with expiry) and standard callback,
        then updates internal state using parent's update() method.
        """
        # Call the enhanced callback if available
        if self._on_token_update_with_expiry:
            self._on_token_update_with_expiry(access_token, refresh_token, api_key, expires_at)

        # Clear permanent failure latch and reset backoff — new credentials have been loaded
        self._permanent_auth_failure = False
        self._consecutive_failures = 0
        self._last_failed_refresh = 0.0
        self._current_backoff = 0.0

        # Use parent's update method to maintain SDK compatibility
        # Parent will call _on_token_update callback and update _auth_data
        self.update(access_token, refresh_token, api_key)
