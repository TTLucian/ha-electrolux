"""Electrolux integration."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_REFRESH_TOKEN,
    DEFAULT_WEBSOCKET_RENEWAL_DELAY,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import FIRST_REFRESH_TIMEOUT, ElectroluxCoordinator
from .util import get_electrolux_session

_LOGGER: logging.Logger = logging.getLogger(__package__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


# noinspection PyUnusedLocal
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    # Always create new coordinator for clean, predictable behavior
    _LOGGER.debug("Electrolux creating coordinator instance")
    renew_interval = DEFAULT_WEBSOCKET_RENEWAL_DELAY

    api_key = entry.data.get(CONF_API_KEY) or ""
    access_token = entry.data.get(CONF_ACCESS_TOKEN) or ""
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN) or ""
    session = async_get_clientsession(hass)

    client = get_electrolux_session(api_key, access_token, refresh_token, session, hass)
    coordinator = ElectroluxCoordinator(
        hass,
        client=client,
        renew_interval=renew_interval,
        username=api_key,
    )
    coordinator.config_entry = entry

    # Set up token refresh callback to persist new tokens
    coordinator.setup_token_refresh_callback()

    # Authenticate
    if not await coordinator.async_login():
        # Create an issue to trigger reauth flow
        from homeassistant.helpers import issue_registry

        issue_registry.async_create_issue(
            hass,
            DOMAIN,
            f"invalid_refresh_token_{entry.entry_id}",
            is_fixable=True,
            issue_domain=DOMAIN,
            severity=issue_registry.IssueSeverity.ERROR,
            translation_key="invalid_refresh_token",
            translation_placeholders={
                "entry_title": entry.title,
            },
        )
        raise ConfigEntryAuthFailed("Electrolux wrong credentials")

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Initialize entities
    _LOGGER.debug("async_setup_entry setup_entities")
    await coordinator.setup_entities()

    _LOGGER.debug("async_setup_entry async_config_entry_first_refresh")
    try:
        await asyncio.wait_for(
            coordinator.async_config_entry_first_refresh(),
            timeout=FIRST_REFRESH_TIMEOUT,
        )
    except (asyncio.TimeoutError, Exception) as err:
        # Handle both timeouts and other exceptions gracefully
        _LOGGER.warning(
            "Electrolux first refresh failed or timed out (%s); will retry in background",
            err,
        )
        # Don't set last_update_success to False here - let HA retry naturally

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    _LOGGER.debug("async_setup_entry extend PLATFORMS")
    coordinator.platforms.extend(PLATFORMS)

    # Call async_setup_entry in entity files
    _LOGGER.debug("async_setup_entry async_forward_entry_setups")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("async_setup_entry scheduling websocket renewal task")

    # Schedule websocket tasks as background tasks after HA startup completes to avoid blocking
    # Use proper HA pattern: per-entry task with automatic cleanup via async_on_unload
    async def start_background_tasks(event=None):
        # Start websocket listening
        coordinator.listen_task = hass.async_create_task(
            coordinator.listen_websocket(), name=f"Electrolux listen - {entry.title}"
        )
        # Start websocket renewal
        coordinator.renew_task = hass.async_create_task(
            coordinator.renew_websocket(), name=f"Electrolux renewal - {entry.title}"
        )

        # Bind task cleanup to entry lifecycle - ensures tasks are cancelled when entry is unloaded/reloaded
        def cleanup_tasks():
            if coordinator.listen_task:
                coordinator.listen_task.cancel()
            if coordinator.renew_task:
                coordinator.renew_task.cancel()

        entry.async_on_unload(cleanup_tasks)

    # Start background tasks after HA has fully started to prevent blocking startup
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, start_background_tasks)
    )

    async def _close_coordinator(event):
        """Close coordinator resources on HA shutdown."""
        try:
            await coordinator.close_websocket()
        except Exception as ex:
            _LOGGER.debug("Error during HA shutdown cleanup: %s", ex)

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _close_coordinator)
    )
    entry.async_on_unload(entry.add_update_listener(update_listener))

    _LOGGER.debug("async_setup_entry OVER")
    return True


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update listener."""
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
