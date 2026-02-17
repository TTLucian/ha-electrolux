"""Electrolux integration."""

# Fix josepy compatibility issue before any imports
try:
    import josepy

    if not hasattr(josepy, "ComparableX509"):
        josepy.ComparableX509 = josepy.ComparableKey  # type: ignore
except ImportError:
    pass  # josepy not installed yet

import asyncio
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DEFAULT_WEBSOCKET_RENEWAL_DELAY,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import FIRST_REFRESH_TIMEOUT, ElectroluxCoordinator
from .util import get_electrolux_session

_LOGGER: logging.Logger = logging.getLogger(__package__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _mask_token(token: str | None) -> str:
    """Mask sensitive token for logging purposes."""
    if not token or len(token) < 8:
        return "***"
    return f"{token[:4]}***{token[-4:]}"


def _validate_config(entry: ConfigEntry) -> None:
    """Validate configuration parameters."""
    if not entry.data.get(CONF_API_KEY):
        raise ConfigEntryError("API key is required")


# noinspection PyUnusedLocal
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    _LOGGER.info(
        f"[AUTH-DEBUG] Setting up integration entry {entry.entry_id} (title: {entry.title})"
    )
    _validate_config(entry)

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    # Always create new coordinator for clean, predictable behavior
    _LOGGER.debug("[AUTH-DEBUG] Creating coordinator instance")
    renew_interval = DEFAULT_WEBSOCKET_RENEWAL_DELAY

    api_key = entry.data.get(CONF_API_KEY) or ""
    access_token = entry.data.get(CONF_ACCESS_TOKEN) or ""
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN) or ""
    token_expires_at = entry.data.get(CONF_TOKEN_EXPIRES_AT)

    _LOGGER.info(
        "[AUTH-DEBUG] Config entry credentials loaded: api_key=%s, access_token=%s, refresh_token=%s",
        _mask_token(api_key),
        _mask_token(access_token),
        _mask_token(refresh_token),
    )
    if token_expires_at:
        import datetime

        expiry_time = datetime.datetime.fromtimestamp(token_expires_at)
        time_until_expiry = token_expires_at - time.time()
        _LOGGER.info(
            f"[AUTH-DEBUG] Stored token expiry: {expiry_time.isoformat()} ({time_until_expiry/3600:.1f} hours from now)"
        )
    else:
        _LOGGER.warning("[AUTH-DEBUG] No token expiry stored in config entry")

    session = async_get_clientsession(hass)

    _LOGGER.debug("[AUTH-DEBUG] Creating API client session")
    client = get_electrolux_session(
        api_key, access_token, refresh_token, session, hass, entry
    )
    _LOGGER.info("[AUTH-DEBUG] API client created successfully")

    coordinator = ElectroluxCoordinator(
        hass,
        client=client,
        renew_interval=renew_interval,
        username=api_key,
    )
    client.coordinator = coordinator
    coordinator.config_entry = entry

    # Set up token refresh callback to persist new tokens
    _LOGGER.info("[AUTH-DEBUG] Setting up token refresh callback")
    coordinator.setup_token_refresh_callback()
    _LOGGER.info("[AUTH-DEBUG] Token refresh callback setup completed")

    # Note: SDK's internal token refresh loop is disabled via API call serialization
    # to prevent race conditions that cause "Invalid grant" errors

    # Authenticate
    _LOGGER.info("[AUTH-DEBUG] Starting authentication test")
    try:
        result = await coordinator.async_login()
        if not result:
            _LOGGER.error(
                "[AUTH-DEBUG] Authentication returned False - likely network issue"
            )
            raise ConfigEntryNotReady("Authentication failed - retrying")
    except ConfigEntryAuthFailed as ex:
        # Don't create repair issue here - let token manager handle it
        # Token manager distinguishes between temporary (expired token) and permanent (invalid credentials)
        # and will create repair only for permanent errors after retry attempts
        _LOGGER.warning(
            "[AUTH-DEBUG] Authentication failed, converting to ConfigEntryNotReady to allow token manager retry: %s",
            ex,
        )
        # Convert to ConfigEntryNotReady so HA retries setup
        # Token manager will create repair if credentials are truly invalid
        raise ConfigEntryNotReady(
            "Authentication failed - allowing token manager to retry"
        ) from ex
    except ConfigEntryNotReady:
        # Network errors - let HA retry
        _LOGGER.error(
            "[AUTH-DEBUG] Network error during authentication - will retry on next HA restart"
        )
        raise

    _LOGGER.debug("Electrolux authentication completed successfully")

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Initialize entities
    _LOGGER.debug("async_setup_entry setup_entities")
    await coordinator.setup_entities()
    appliances_count = (
        len(coordinator.data.get("appliances", {})) if coordinator.data else 0
    )
    _LOGGER.debug(
        "async_setup_entry setup_entities completed - appliances configured: %d",
        appliances_count,
    )

    _LOGGER.debug("async_setup_entry async_config_entry_first_refresh")
    try:
        await asyncio.wait_for(
            coordinator.async_config_entry_first_refresh(),
            timeout=FIRST_REFRESH_TIMEOUT,
        )
        _LOGGER.debug("async_setup_entry first refresh completed successfully")
    except (asyncio.TimeoutError, Exception) as err:
        # Handle both timeouts and other exceptions gracefully
        _LOGGER.warning(
            "Electrolux first refresh failed or timed out (%s); will retry in background",
            err,
        )
        # Don't set last_update_success to False here - let HA retry naturally

    if not coordinator.last_update_success:
        _LOGGER.debug(
            "async_setup_entry coordinator reports last_update_success=False, raising ConfigEntryNotReady"
        )
        raise ConfigEntryNotReady

    _LOGGER.debug("async_setup_entry extend PLATFORMS")
    coordinator.platforms.extend(PLATFORMS)
    _LOGGER.debug(
        "async_setup_entry platforms extended - total platforms: %d",
        len(coordinator.platforms),
    )

    # Call async_setup_entry in entity files
    _LOGGER.debug("async_setup_entry async_forward_entry_setups")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug(
        "async_setup_entry async_forward_entry_setups completed - platforms forwarded"
    )

    _LOGGER.debug("async_setup_entry scheduling websocket renewal task")

    # Schedule websocket tasks as background tasks after HA startup completes to avoid blocking
    # Use proper HA pattern: per-entry task with automatic cleanup via async_on_unload
    async def start_background_tasks(event=None):
        _LOGGER.debug("async_setup_entry background tasks starting after HA startup")
        try:
            # Start websocket listening
            coordinator.listen_task = hass.async_create_task(
                coordinator.listen_websocket(),
                name=f"Electrolux listen - {entry.title}",
            )
            _LOGGER.debug(
                "async_setup_entry websocket listen task created: %s",
                coordinator.listen_task.get_name(),
            )

            # Start websocket renewal
            coordinator.renew_task = hass.async_create_task(
                coordinator.renew_websocket(),
                name=f"Electrolux renewal - {entry.title}",
            )
            _LOGGER.debug(
                "async_setup_entry websocket renewal task created: %s",
                coordinator.renew_task.get_name(),
            )

            # Bind task cleanup to entry lifecycle - ensures tasks are cancelled when entry is unloaded/reloaded
            def cleanup_tasks():
                _LOGGER.debug(
                    "async_setup_entry cleanup_tasks called - cancelling websocket tasks"
                )
                if coordinator.listen_task:
                    coordinator.listen_task.cancel()
                    _LOGGER.debug("async_setup_entry listen task cancelled")
                if coordinator.renew_task:
                    coordinator.renew_task.cancel()
                    _LOGGER.debug("async_setup_entry renewal task cancelled")

            entry.async_on_unload(cleanup_tasks)
            _LOGGER.debug("async_setup_entry cleanup handlers registered")

        except Exception as ex:
            _LOGGER.error("async_setup_entry failed to start background tasks: %s", ex)
            raise

    # Start background tasks after HA has fully started to prevent blocking startup
    # If HA is already running (e.g., during reload), start tasks immediately
    if hass.is_running:
        _LOGGER.debug(
            "async_setup_entry HA already running - starting background tasks immediately"
        )
        await start_background_tasks()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, start_background_tasks)
        _LOGGER.debug(
            "async_setup_entry background task listener registered for EVENT_HOMEASSISTANT_STARTED"
        )

    async def _close_coordinator(event):
        """Close coordinator resources on HA shutdown."""
        _LOGGER.debug("async_setup_entry HA shutdown cleanup starting")
        try:
            await coordinator.close_websocket()
            _LOGGER.debug(
                "async_setup_entry websocket closed successfully during shutdown"
            )
        except Exception as ex:
            _LOGGER.debug("Error during HA shutdown cleanup: %s", ex)

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _close_coordinator)
    )
    _LOGGER.debug("async_setup_entry shutdown cleanup listener registered")

    entry.async_on_unload(entry.add_update_listener(update_listener))
    _LOGGER.debug("async_setup_entry update listener registered")

    _LOGGER.debug("async_setup_entry OVER - integration setup completed successfully")
    return True


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update listener.

    Only reload when options change, not when tokens are auto-refreshed.
    Token updates use async_update_entry with reload=False, but this listener
    would still trigger. We detect token-only changes and skip reload.
    """
    coordinator: ElectroluxCoordinator | None = hass.data[DOMAIN].get(
        config_entry.entry_id
    )

    if coordinator and hasattr(coordinator, "_last_token_update"):
        # Check if this update happened very recently (within last 2 seconds)
        # If so, it's likely the token refresh callback that just updated the config
        import time

        time_since_token_update = time.time() - coordinator._last_token_update

        if time_since_token_update < 2.0:
            _LOGGER.debug(
                f"[AUTH-DEBUG] Update listener: Recent token update detected ({time_since_token_update:.1f}s ago), skipping reload"
            )
            return

    # Options changed or first load - reload is needed
    _LOGGER.info("Update listener: Options or settings changed, reloading integration")
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    # 1. Retrieve the client before data is cleared
    coordinator: ElectroluxCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    client = coordinator.api if coordinator else None

    # 2. Trigger the decisive cleanup in util.py
    if client:
        await client.close()

    # 3. Proceed with standard HA unloading
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.debug("Electrolux async_reload_entry %s", entry)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
