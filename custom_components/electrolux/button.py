"""Button platform for Electrolux."""

import hashlib
import logging
from typing import Any, cast

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUTTON, CONF_API_KEY, icon_mapping
from .coordinator import ElectroluxCoordinator
from .entity import ElectroluxEntity
from .execute_command_states import execute_states_from_capabilities
from .model import ElectroluxDevice
from .util import (
    AuthenticationError,
    ElectroluxApiClient,
    execute_command_with_error_handling,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure button platform."""
    coordinator = entry.runtime_data
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [entity for entity in appliance.entities if entity.entity_type == BUTTON]
            _LOGGER.debug(
                "Electrolux add %d BUTTON entities to registry for appliance %s",
                len(entities),
                appliance_id,
            )
            async_add_entities(entities)


class ElectroluxButton(ElectroluxEntity, ButtonEntity):
    """Electrolux button class."""

    _execute_states_cache: dict[str, list[str]] | None = None
    _execute_states_cache_caps_id: int | None = None

    def __init__(
        self,
        coordinator: Any,
        name: str,
        config_entry,
        pnc_id: str,
        entity_type: Platform,
        entity_name,
        entity_attr,
        entity_source,
        capability: dict[str, Any],
        unit: str,
        device_class: str,
        entity_category: EntityCategory,
        icon: str,
        catalog_entry: ElectroluxDevice | None,
        val_to_send: str,
    ) -> None:
        """Initialize the Button Entity."""
        super().__init__(
            coordinator=coordinator,
            capability=capability,
            name=name,
            config_entry=config_entry,
            pnc_id=pnc_id,
            entity_type=entity_type,
            entity_name=entity_name,
            entity_attr=entity_attr,
            entity_source=entity_source,
            unit=None,
            device_class=device_class,
            entity_category=entity_category,
            icon=icon,
            catalog_entry=catalog_entry,
        )
        self.val_to_send = val_to_send

    @property
    def entity_domain(self):
        """Entity domain for the entry. Used for consistent entity_id."""
        return BUTTON

    @property
    def device_class(self) -> ButtonDeviceClass | None:
        """Return the device class for the button entity."""
        if self._catalog_entry and hasattr(self._catalog_entry, "device_class"):
            device_class = self._catalog_entry.device_class
            if isinstance(device_class, ButtonDeviceClass):
                return device_class
        return self._device_class

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        # Use stable unique_id based on API key hash, including val_to_send for button differentiation
        api_key = self.config_entry.data.get(CONF_API_KEY, "")
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16] if api_key else "unknown"
        # Normalize entity_attr by removing fPPN prefix for consistent unique_ids
        normalized_attr = self.entity_attr.lower()
        if normalized_attr.startswith("fppn_"):
            normalized_attr = normalized_attr.replace("fppn_", "").strip("_")
        elif normalized_attr.startswith("fppn"):
            normalized_attr = normalized_attr.replace("fppn", "").strip("_")
        else:
            normalized_attr = normalized_attr.strip("_")
        return f"{api_key_hash}-{normalized_attr}-{self.val_to_send}-{self.entity_source or 'root'}-{self.pnc_id}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        name = self._name
        if self.catalog_entry and self.catalog_entry.friendly_name:
            # Get appliance name from coordinator data
            appliances = self.coordinator.data.get("appliances", None)
            if appliances:
                appliance = appliances.get_appliance(self.pnc_id)
                if appliance:
                    name = f"{appliance.name} {self.catalog_entry.friendly_name.lower()}"
        # Get the last word from the 'name' variable
        # and compare to the command we are sending duplicate names
        # "air filter state reset reset" for instance
        last_word = name.split()[-1]
        if last_word.lower() == str(self.val_to_send).lower():
            return name
        return f"{name} {self.val_to_send}"

    @property
    def _execute_states(self) -> dict[str, list[str]] | None:
        """Return the executeCommand rules that apply to this appliance.

        The appliance's own ``applianceState`` triggers win over the catalog
        table: the tables are per appliance type, and individual models differ.
        A dryer that only accepts ON in IDLE, for example, would otherwise show
        an enabled Start button that can only ever answer 406.
        """
        caps = self._appliance_capabilities()
        caps_id = id(caps)

        if hasattr(self, "_execute_states_cache") and getattr(self, "_execute_states_cache_caps_id", None) == caps_id:
            return cast(dict[str, list[str]] | None, self._execute_states_cache)

        derived = execute_states_from_capabilities(caps, entity_source=self.entity_source)
        states = derived

        if states is None and self._catalog_entry:
            states = self._catalog_entry.available_when_states

        self._execute_states_cache = states
        self._execute_states_cache_caps_id = caps_id
        # Keep a reference to the capabilities object so CPython cannot recycle
        # its id() onto a different dict while the cache entry is alive; id()
        # is only unique among live objects, so a recycled id would otherwise
        # serve stale rules from a previous appliance payload.
        self._execute_states_cache_caps = caps
        return states

    def _appliance_capabilities(self) -> dict[str, Any] | None:
        """Return this appliance's capabilities, or None if not loaded yet.

        available() is called during startup and teardown as well, so this must
        not assume the coordinator holds an appliance for this entity.
        """
        if self.coordinator.data is None:
            return None
        appliances = self.coordinator.data.get("appliances", None)
        if appliances is None:
            return None
        appliance = appliances.get_appliance(self.pnc_id)
        if appliance is None:
            return None
        return getattr(getattr(appliance, "data", None), "capabilities", None)

    def _current_appliance_state(self) -> str | None:
        """Return the applianceState this button's rules are evaluated against.

        The rules may be derived from a source-scoped ``applianceState`` (e.g.
        ``upperOven/applianceState`` on a structured oven, which is an
        independent state machine from the root one), so the compared state must
        be read with the same scoping. Mirrors the "/"-aware path resolution in
        ``ElectroluxEntity``: try the flat ``source/applianceState`` key first,
        then the nested ``source`` -> ``applianceState`` layout, then the root.
        """
        if not self.entity_source:
            return self.reported_state.get("applianceState")

        scoped_path = f"{self.entity_source}/applianceState"
        scoped_state = self.reported_state.get(scoped_path)
        if scoped_state is not None:
            return scoped_state

        source_state = self.reported_state.get(self.entity_source)
        if isinstance(source_state, dict):
            nested_state = source_state.get("applianceState")
            if nested_state is not None:
                return nested_state

        return self.reported_state.get("applianceState")

    @property
    def available(self) -> bool:
        # Check state restrictions first, appliance-derived or catalog-defined.
        # A command absent from the rules is left unrestricted, as before.
        # A missing current state is also left unrestricted: gating on an
        # unknown state would silently hide every rule-covered button on
        # partial payloads, indistinguishable from a real disallowed state.
        if execute_states := self._execute_states:
            allowed_states = execute_states.get(self.val_to_send)
            if allowed_states is not None:
                current_state = self._current_appliance_state()
                if current_state is not None and current_state not in allowed_states:
                    return False

        return super().available

    @property
    def icon(self) -> str | None:
        """Return the icon of the entity."""
        return self._icon or icon_mapping.get(self.val_to_send, "mdi:gesture-tap-button")

    async def send_command(self) -> bool:
        """Send a command to the device."""
        # Check if appliance is connected before sending command
        if not self.is_connected():
            connectivity_state = self.reported_state.get("connectivityState", "unknown")
            _LOGGER.warning(
                "Appliance %s is not connected (state: %s), cannot execute command for %s",
                self.pnc_id,
                connectivity_state,
                self.entity_attr,
            )
            raise HomeAssistantError(
                f"Appliance is offline (current state: {connectivity_state}). "
                "Please check that the appliance is plugged in, has network connectivity and is connected to cloud services."
            )

        # Remote control validation removed - API handles this with precise appliance-specific rules.
        # Different appliances have different states (ENABLED, NOT_SAFETY_RELEVANT_ENABLED, persistentRemoteControl)
        # that only the API can accurately validate. Error handling in util.py displays friendly messages.

        client: ElectroluxApiClient = self.api
        value = self.val_to_send
        command: dict[str, Any]
        if not self.is_dam_appliance:
            # Legacy appliances: send as top-level property, but respect entity_source
            # when the capability key has a slash (e.g. upperOven/executeCommand).
            if self.entity_source:
                command = {self.entity_source: {self.entity_attr: value}}
            else:
                command = {self.entity_attr: value}
        elif self.entity_source:
            if self.entity_source == "userSelections":
                # Safer access to avoid KeyError if userSelections is missing
                reported = (
                    self.appliance_status.get("properties", {}).get("reported", {}) if self.appliance_status else {}
                )
                program_uid = reported.get("userSelections", {}).get("programUID")
                command = {
                    self.entity_source: {
                        "programUID": program_uid,
                        self.entity_attr: value,
                    },
                }
            else:
                command = {self.entity_source: {self.entity_attr: value}}
        else:
            command = {self.entity_attr: value}

        # Wrap DAM commands in the required format
        if self.is_dam_appliance:
            command = {"commands": [command]}

        _LOGGER.debug("Electrolux send command %s", command)
        try:
            result = await execute_command_with_error_handling(client, self.pnc_id, command, self.entity_attr, _LOGGER)
        except AuthenticationError as auth_ex:
            # Handle authentication errors by triggering reauthentication
            coordinator: ElectroluxCoordinator = self.coordinator  # type: ignore[assignment]
            await coordinator.handle_authentication_error(auth_ex)
            return True
        except Exception:
            # Re-raise any errors from execute_command_with_error_handling
            raise
        _LOGGER.debug("Electrolux send command result %s", result)
        return True

    async def async_press(self) -> None:
        """Execute a button press."""
        # Special handling for manual sync button
        if self.entity_attr == "manualSync":
            await self._perform_manual_sync()
        else:
            await self.send_command()

    async def _perform_manual_sync(self) -> None:
        """Perform manual sync operation for all appliances."""
        appliance_name = "Unknown Appliance"
        try:
            # Get appliance name for user feedback
            appliances = self.coordinator.data.get("appliances", None)
            if appliances:
                appliance = appliances.get_appliance(self.pnc_id)
                if appliance:
                    appliance_name = appliance.name

            # Fire progress events for each step
            def fire_progress(step: int, message: str, progress: str):
                self.hass.bus.async_fire(
                    "electrolux_manual_sync_progress",
                    {
                        "appliance_id": self.pnc_id,
                        "appliance_name": appliance_name,
                        "step": step,
                        "message": message,
                        "progress": progress,
                    },
                )

            # Initial warning about sensible usage
            fire_progress(
                0,
                "Manual sync initiated. This refreshes ALL appliances and causes heavy API load. Use only when data appears stuck.",
                "0%",
            )

            # Progress updates during sync
            fire_progress(1, "Disconnecting real-time data stream...", "25%")
            fire_progress(2, "Refreshing appliance data from cloud...", "50%")
            fire_progress(3, "Starting fresh real-time data stream...", "75%")

            # Use the coordinator's thread-safe manual sync method
            await cast(ElectroluxCoordinator, self.coordinator).perform_manual_sync(self.pnc_id, appliance_name)

            # Complete
            fire_progress(4, "Manual sync completed successfully!", "100%")

        except Exception as ex:
            error_msg = f"Manual sync failed: {ex}"
            self.hass.bus.async_fire(
                "electrolux_manual_sync_progress",
                {
                    "appliance_id": self.pnc_id,
                    "appliance_name": appliance_name,
                    "step": -1,
                    "message": error_msg,
                    "progress": "0%",
                },
            )
            _LOGGER.error(
                "Manual sync failed for appliance %s (%s): %s",
                appliance_name,
                self.pnc_id,
                ex,
            )
            raise HomeAssistantError(error_msg) from ex
