"""Adds config flow for Electrolux."""

import logging
import time
from typing import Any

import jwt
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowHandler, FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
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


def _validate_credentials(
    api_key: str | None, access_token: str | None, refresh_token: str | None
) -> list[str]:
    """Validate credential inputs for security and format requirements."""
    errors = []

    if not api_key or not isinstance(api_key, str) or len(api_key.strip()) < 10:
        errors.append("API key must be at least 10 characters long")

    if (
        not access_token
        or not isinstance(access_token, str)
        or len(access_token.strip()) < 20
    ):
        errors.append("Access token must be at least 20 characters long")

    if (
        not refresh_token
        or not isinstance(refresh_token, str)
        or len(refresh_token.strip()) < 20
    ):
        errors.append("Refresh token must be at least 20 characters long")

    # Check for potentially dangerous characters that might indicate injection attempts
    dangerous_chars = ["<", ">", '"', "'", ";", "\\", "\n", "\r"]
    for token_name, token in [
        ("API key", api_key),
        ("Access token", access_token),
        ("Refresh token", refresh_token),
    ]:
        if token:
            for char in dangerous_chars:
                if char in token:
                    errors.append(
                        f"{token_name} contains invalid character: {repr(char)}"
                    )
                    break

    return errors


def _mask_token(token: str | None) -> str:
    """Mask sensitive token for logging purposes."""
    if not token or len(token) < 8:
        return "***"
    return f"{token[:4]}***{token[-4:]}"


def _extract_token_expiry(access_token: str | None) -> int | None:
    """Extract expiry timestamp from JWT access token.

    Returns unix timestamp when token expires, or None if unable to extract.
    """
    if not access_token:
        return None

    try:
        payload = jwt.decode(
            access_token,
            options={"verify_signature": False, "verify_exp": False},
        )
        exp = payload.get("exp")
        if exp and isinstance(exp, (int, float)):
            return int(exp)
    except Exception as e:
        _LOGGER.debug(f"Unable to extract token expiry: {e}")

    return None


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
        # Validate credential format and security
        validation_errors = _validate_credentials(
            user_input.get("api_key"),
            user_input.get("access_token"),
            user_input.get("refresh_token"),
        )
        if validation_errors:
            self._errors["base"] = "invalid_format"
            _LOGGER.warning(
                "Credential validation failed: %s", "; ".join(validation_errors)
            )
            return None

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
            # Extract token expiry from JWT and store it in config entry
            access_token = user_input.get("access_token")
            token_expiry = _extract_token_expiry(access_token)
            if token_expiry:
                user_input["token_expires_at"] = token_expiry
                # Log when token will expire for visibility
                time_remaining = token_expiry - time.time()
                _LOGGER.info(
                    f"Initial token expires in {time_remaining/3600:.1f} hours "
                    f"(at timestamp {token_expiry})"
                )
            else:
                _LOGGER.warning("Could not extract token expiry from JWT")

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
        _LOGGER.warning(
            f"[AUTH-DEBUG] Reauth flow initiated for entry {entry.entry_id} (title: {entry.title})"
        )
        # Store the entry for later use
        self._reauth_entry = entry
        _LOGGER.info("[AUTH-DEBUG] Displaying reauth form to user")
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
        _LOGGER.info(
            "[AUTH-DEBUG] Validating reauth credentials (api_key: %s, access_token: %s, refresh_token: %s)",
            _mask_token(user_input.get("api_key")),
            _mask_token(user_input.get("access_token")),
            _mask_token(user_input.get("refresh_token")),
        )
        valid = await self._test_credentials(
            user_input.get("api_key"),
            user_input.get("access_token"),
            user_input.get("refresh_token"),
        )
        if valid:
            _LOGGER.info("[AUTH-DEBUG] Reauth credentials validated successfully")
            # Dismiss the token refresh issue since re-authentication succeeded
            from homeassistant.helpers import issue_registry

            entry = self._get_reauth_entry()
            if entry is None:
                _LOGGER.error(
                    "[AUTH-DEBUG] CRITICAL: No reauth entry found during reauthentication"
                )
                self._errors["base"] = "reauth_failed"
                return None

            issue_id = f"invalid_refresh_token_{entry.entry_id}"
            _LOGGER.info(f"[AUTH-DEBUG] Dismissing repair issue: {issue_id}")
            issue_registry.async_delete_issue(self.hass, DOMAIN, issue_id)

            # Extract token expiry from JWT and store it
            access_token = user_input.get("access_token")
            token_expiry = _extract_token_expiry(access_token)
            entry_data = dict(user_input)
            if token_expiry:
                entry_data["token_expires_at"] = token_expiry
                time_remaining = token_expiry - time.time()
                _LOGGER.info(
                    f"[AUTH-DEBUG] Reauth: New token expires in {time_remaining/3600:.1f} hours (at timestamp {token_expiry})"
                )
            else:
                _LOGGER.warning(
                    "[AUTH-DEBUG] Could not extract token expiry from JWT during reauth"
                )

            # Update the existing entry with new tokens
            _LOGGER.info(
                f"[AUTH-DEBUG] Updating config entry {entry.entry_id} with new credentials"
            )
            return self.async_update_reload_and_abort(entry, data=entry_data)
        _LOGGER.warning(
            "[AUTH-DEBUG] Reauth credentials validation failed - invalid credentials"
        )
        self._errors["base"] = "invalid_auth"
        return None

    async def async_step_reauth_validate(
        self, user_input: UserInput | None = None
    ) -> ConfigFlowResult:
        """Handle reauth and validation."""
        self._errors = {}
        if user_input is not None:
            _LOGGER.info("[AUTH-DEBUG] Reauth form submitted, validating credentials")
            result = await self._validate_reauth_input(user_input)
            if result is not None:
                _LOGGER.info("[AUTH-DEBUG] Reauth completed successfully")
                return result
            # Invalid, show form with errors
            _LOGGER.info(
                "[AUTH-DEBUG] Reauth validation failed, showing form with errors"
            )

        # For reauth, populate defaults with current config entry values
        entry = self._get_reauth_entry()
        defaults = dict(entry.data) if user_input is None else user_input
        _LOGGER.debug(
            "[AUTH-DEBUG] Showing reauth form with defaults (api_key: %s)",
            _mask_token(defaults.get("api_key")),
        )
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
        _LOGGER.debug(
            "Testing credentials: API key=%s, access_token=%s, refresh_token=%s",
            _mask_token(api_key),
            _mask_token(access_token),
            _mask_token(refresh_token),
        )
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
            _LOGGER.error("Authentication to Electrolux failed: %s", type(e).__name__)
            return False
        except Exception as e:  # Fallback for unexpected errors
            _LOGGER.error(
                "Unexpected error during Electrolux authentication: %s",
                type(e).__name__,
            )
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
        _LOGGER.debug(
            "Testing credentials: API key=%s, access_token=%s, refresh_token=%s",
            _mask_token(api_key),
            _mask_token(access_token),
            _mask_token(refresh_token),
        )
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
            _LOGGER.error("Authentication to Electrolux failed: %s", type(e).__name__)
            return False
        except Exception as e:  # Fallback for unexpected errors
            _LOGGER.error(
                "Unexpected error during Electrolux authentication: %s",
                type(e).__name__,
            )
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


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> FlowHandler:
    """Create fix flow for Electrolux repair issues."""
    return ElectroluxRepairFlow()


class ElectroluxRepairFlow(FlowHandler):
    """Handler for Electrolux repair flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize repair flow."""
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the first step of a repair flow."""
        return await self.async_step_confirm_repair(user_input)

    async def async_step_confirm_repair(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the form to confirm repair and enter new credentials."""
        errors = {}

        if user_input is not None:
            # Extract entry_id from the issue_id
            issue_id = self.context.get("issue_id", "")
            entry_id = issue_id.replace("invalid_refresh_token_", "")

            # Get the config entry
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry is None:
                _LOGGER.error("Config entry %s not found", entry_id)
                return self.async_abort(reason="entry_not_found")

            # Test the new credentials
            api_key = user_input.get(CONF_API_KEY)
            access_token = user_input.get(CONF_ACCESS_TOKEN)
            refresh_token = user_input.get(CONF_REFRESH_TOKEN)

            # Validate credential format
            validation_errors = _validate_credentials(
                api_key, access_token, refresh_token
            )
            if validation_errors:
                errors["base"] = "invalid_format"
                _LOGGER.warning(
                    "Credential validation failed: %s", "; ".join(validation_errors)
                )
            else:
                # Test credentials
                if await self._test_credentials(api_key, access_token, refresh_token):
                    # Update config entry with new credentials
                    new_data = dict(entry.data)
                    new_data[CONF_API_KEY] = api_key
                    new_data[CONF_ACCESS_TOKEN] = access_token
                    new_data[CONF_REFRESH_TOKEN] = refresh_token

                    # Extract token expiry from JWT
                    token_expiry = _extract_token_expiry(access_token)
                    if token_expiry:
                        new_data["token_expires_at"] = token_expiry
                        time_remaining = token_expiry - time.time()
                        _LOGGER.info(
                            f"Repair: Token expires in {time_remaining/3600:.1f} hours"
                        )

                    self.hass.config_entries.async_update_entry(entry, data=new_data)

                    # Delete the repair issue
                    ir.async_delete_issue(self.hass, DOMAIN, issue_id)

                    # Reload the config entry
                    await self.hass.config_entries.async_reload(entry.entry_id)

                    _LOGGER.info(
                        "Repair successful for entry %s, credentials updated", entry_id
                    )
                    return self.async_create_entry(title="", data={})

                errors["base"] = "invalid_auth"
                _LOGGER.warning("Invalid credentials provided during repair")

        # Show the form with current values as defaults (entry_id in issue_id)
        issue_id = self.context.get("issue_id", "")
        entry_id = issue_id.replace("invalid_refresh_token_", "")
        entry = self.hass.config_entries.async_get_entry(entry_id)

        defaults = {}
        if entry:
            defaults = {
                CONF_API_KEY: entry.data.get(CONF_API_KEY, ""),
                CONF_ACCESS_TOKEN: "",  # Don't show old tokens for security
                CONF_REFRESH_TOKEN: "",
            }

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT, autocomplete="api-key"
                    )
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
        )

        return self.async_show_form(
            step_id="confirm_repair",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "url": "https://developer.electrolux.one/dashboard"
            },
        )

    async def _test_credentials(
        self, api_key: str | None, access_token: str | None, refresh_token: str | None
    ) -> bool:
        """Return true if credentials is valid."""
        _LOGGER.debug(
            "Testing credentials: API key=%s, access_token=%s, refresh_token=%s",
            _mask_token(api_key),
            _mask_token(access_token),
            _mask_token(refresh_token),
        )
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
            _LOGGER.error("Authentication to Electrolux failed: %s", type(e).__name__)
            return False
        except Exception as e:  # Fallback for unexpected errors
            _LOGGER.error(
                "Unexpected error during Electrolux authentication: %s",
                type(e).__name__,
            )
            return False
        return True
