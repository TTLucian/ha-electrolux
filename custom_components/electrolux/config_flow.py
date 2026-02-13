"""Adds config flow for Electrolux."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import UserInput
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_NOTIFICATION_DEFAULT,
    CONF_NOTIFICATION_DIAG,
    CONF_NOTIFICATION_WARNING,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)
from .util import get_electrolux_session

_LOGGER = logging.getLogger(__name__)


class ElectroluxStatusFlowHandler(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]  # HA metaclass requires domain kwarg
    """Config flow for Electrolux."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._errors: dict[str, str] = {}

    async def _validate_user_input_for_config(
        self, user_input: dict[str, Any]
    ) -> ConfigFlowResult | None:
        """Validate user input for config flow."""
        # check if the specified account is configured already
        # to prevent them from being added twice
        api_key = user_input.get("api_key")
        if api_key and any(
            api_key == entry.data.get("api_key", None)
            for entry in self._async_current_entries()
        ):
            return self.async_abort(reason="already_configured_account")

        valid = await self._test_credentials(
            user_input.get("api_key"),
            user_input.get("access_token"),
            user_input.get("refresh_token"),
        )
        if valid:
            return self.async_create_entry(title="Electrolux", data=user_input)
        self._errors["base"] = "invalid_auth"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            result = await self._validate_user_input_for_config(user_input)
            if result is not None:
                return result
            # Invalid, show form with errors

        return await self._show_config_form(user_input)

    async def async_step_reauth(self, entry: ConfigEntry) -> ConfigFlowResult:
        """Handle configuration by re-auth."""
        # Store the entry for later use
        self._reauth_entry = entry
        return await self.async_step_reauth_validate()

    def _get_reauth_entry(self) -> ConfigEntry:
        """Get the reauth entry."""
        entry = getattr(self, "_reauth_entry", None)
        if entry is None:
            raise RuntimeError("No reauth entry available")
        return entry

    async def _validate_reauth_input(
        self, user_input: UserInput | dict[str, Any]
    ) -> ConfigFlowResult | None:
        """Validate user input for reauth."""
        valid = await self._test_credentials(
            user_input.get("api_key"),
            user_input.get("access_token"),
            user_input.get("refresh_token"),
        )
        if valid:
            # Dismiss the token refresh issue since re-authentication succeeded
            from homeassistant.helpers import issue_registry

            entry = self._get_reauth_entry()
            if entry is None:
                _LOGGER.error("No reauth entry found during reauthentication")
                self._errors["base"] = "reauth_failed"
                return None

            issue_id = f"invalid_refresh_token_{entry.entry_id}"
            issue_registry.async_delete_issue(self.hass, DOMAIN, issue_id)
            # Update the existing entry with new tokens
            return self.async_update_reload_and_abort(entry, data=user_input)
        self._errors["base"] = "invalid_auth"
        return None

    async def async_step_reauth_validate(
        self, user_input: UserInput | None = None
    ) -> ConfigFlowResult:
        """Handle reauth and validation."""
        self._errors = {}
        if user_input is not None:
            result = await self._validate_reauth_input(user_input)
            if result is not None:
                return result
            # Invalid, show form with errors

        # For reauth, populate defaults with current config entry values
        entry = self._get_reauth_entry()
        defaults = dict(entry.data) if user_input is None else user_input
        return await self._show_config_form(defaults, "reauth_validate")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Present the configuration options dialog."""
        return ElectroluxStatusOptionsFlowHandler(config_entry)

    def _get_config_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        """Get the config schema with defaults."""
        data_schema: dict[Any, Any] = {
            vol.Required(
                CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")
            ): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="api-key")
            ),
            vol.Required(
                CONF_ACCESS_TOKEN, default=defaults.get(CONF_ACCESS_TOKEN, "")
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD, autocomplete="access-token"
                )
            ),
            vol.Required(
                CONF_REFRESH_TOKEN, default=defaults.get(CONF_REFRESH_TOKEN, "")
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD, autocomplete="refresh-token"
                )
            ),
        }
        if self.show_advanced_options:
            data_schema.update(
                {
                    vol.Optional(
                        CONF_NOTIFICATION_DEFAULT,
                        default=defaults.get(CONF_NOTIFICATION_DEFAULT, True),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_NOTIFICATION_WARNING,
                        default=defaults.get(CONF_NOTIFICATION_WARNING, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_NOTIFICATION_DIAG,
                        default=defaults.get(CONF_NOTIFICATION_DIAG, False),
                    ): cv.boolean,
                }
            )
        return vol.Schema(data_schema)

    async def _show_config_form(self, user_input, step_id="user") -> ConfigFlowResult:
        """Show the configuration form to edit location data."""
        defaults = user_input or {}

        return self.async_show_form(
            step_id=step_id,
            data_schema=self._get_config_schema(defaults),
            errors=self._errors,
            description_placeholders={"url": "https://developer.electrolux.one/"},
        )

    async def _test_credentials(
        self, api_key: str | None, access_token: str | None, refresh_token: str | None
    ) -> bool:
        """Return true if credentials is valid."""
        try:
            client = get_electrolux_session(
                api_key,
                access_token,
                refresh_token,
                async_get_clientsession(self.hass),
                self.hass,
            )
            await client.get_appliances_list()
        except (ConnectionError, TimeoutError, ValueError, KeyError) as e:
            _LOGGER.error("Authentication to Electrolux failed: %s", e)
            return False
        except Exception as e:  # Fallback for unexpected errors
            _LOGGER.error("Unexpected error during Electrolux authentication: %s", e)
            return False
        return True


class ElectroluxStatusOptionsFlowHandler(OptionsFlow):
    """Config flow options handler for Electrolux."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Manage the options."""
        return await self.async_step_user()

    async def _get_options_schema(self) -> vol.Schema:
        """Get the options schema with current values, checking credential validity."""
        # Get current values from config entry data and options
        current_api_key = self._config_entry.data.get(CONF_API_KEY, "")
        current_access_token = self._config_entry.data.get(CONF_ACCESS_TOKEN, "")
        current_refresh_token = self._config_entry.data.get(CONF_REFRESH_TOKEN, "")
        current_notify_default = self._config_entry.data.get(
            CONF_NOTIFICATION_DEFAULT, True
        )
        current_notify_warning = self._config_entry.data.get(
            CONF_NOTIFICATION_WARNING, False
        )
        current_notify_diag = self._config_entry.data.get(CONF_NOTIFICATION_DIAG, False)

        # For security, never pre-fill access_token and refresh_token fields
        # Users should generate new credentials from the portal
        current_access_token = ""
        current_refresh_token = ""

        return vol.Schema(
            {
                vol.Optional(CONF_API_KEY, default=current_api_key): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT, autocomplete="api-key"
                    )
                ),
                vol.Optional(
                    CONF_ACCESS_TOKEN, default=current_access_token
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.PASSWORD, autocomplete="access-token"
                    )
                ),
                vol.Optional(
                    CONF_REFRESH_TOKEN, default=current_refresh_token
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.PASSWORD, autocomplete="refresh-token"
                    )
                ),
                vol.Optional(
                    CONF_NOTIFICATION_DEFAULT, default=current_notify_default
                ): cv.boolean,
                vol.Optional(
                    CONF_NOTIFICATION_WARNING, default=current_notify_warning
                ): cv.boolean,
                vol.Optional(
                    CONF_NOTIFICATION_DIAG, default=current_notify_diag
                ): cv.boolean,
            }
        )

    async def _test_credentials(
        self, api_key: str | None, access_token: str | None, refresh_token: str | None
    ) -> bool:
        """Return true if credentials is valid."""
        try:
            client = get_electrolux_session(
                api_key,
                access_token,
                refresh_token,
                async_get_clientsession(self.hass),
                self.hass,
            )
            await client.get_appliances_list()
        except (ConnectionError, TimeoutError, ValueError, KeyError) as e:
            _LOGGER.error("Authentication to Electrolux failed: %s", e)
            return False
        except Exception as e:  # Fallback for unexpected errors
            _LOGGER.error("Unexpected error during Electrolux authentication: %s", e)
            return False
        return True

    async def _validate_and_update_options(
        self, user_input: dict[str, Any]
    ) -> ConfigFlowResult | None:
        """Validate credentials and update options if provided."""
        # Test credentials if any API credentials were provided
        if any(
            key in user_input
            for key in [CONF_API_KEY, CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN]
        ):
            api_key = user_input.get(
                CONF_API_KEY, self._config_entry.data.get(CONF_API_KEY)
            )
            access_token = user_input.get(
                CONF_ACCESS_TOKEN, self._config_entry.data.get(CONF_ACCESS_TOKEN)
            )
            refresh_token = user_input.get(
                CONF_REFRESH_TOKEN, self._config_entry.data.get(CONF_REFRESH_TOKEN)
            )

            if not await self._test_credentials(api_key, access_token, refresh_token):
                return None  # Invalid, caller will show form with errors

        # Update the config entry data with new options
        new_data = dict(self._config_entry.data)
        new_options = dict(self._config_entry.options)

        # API credentials and notifications go in data (require restart)
        if "api_key" in user_input:
            new_data["api_key"] = user_input.get("api_key")
        if "access_token" in user_input:
            new_data["access_token"] = user_input.get("access_token")
        if "refresh_token" in user_input:
            new_data["refresh_token"] = user_input.get("refresh_token")
        if "notification_default" in user_input:
            new_data["notification_default"] = user_input.get("notification_default")
        if "notification_warning" in user_input:
            new_data["notification_warning"] = user_input.get("notification_warning")
        if "notification_diag" in user_input:
            new_data["notification_diag"] = user_input.get("notification_diag")

        self.hass.config_entries.async_update_entry(
            self._config_entry, data=new_data, options=new_options
        )
        return self.async_create_entry(title="", data={})

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step."""
        if user_input is not None:
            result = await self._validate_and_update_options(user_input)
            if result is not None:
                return result
            # Invalid credentials, show form with errors
            return self.async_show_form(
                step_id="user",
                data_schema=await self._get_options_schema(),
                errors={"base": "invalid_auth"},
                description_placeholders={
                    "url": "https://developer.electrolux.one/dashboard"
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=await self._get_options_schema(),
            description_placeholders={
                "url": "https://developer.electrolux.one/dashboard"
            },
        )
