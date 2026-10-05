"""Switch platform for Electrolux."""

import logging
from typing import (
    Any,
    cast,
)  # cast: CoordinatorEntity lacks ElectroluxCoordinator type param

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SWITCH
from .coordinator import ElectroluxCoordinator
from .entity import ElectroluxEntity
from .util import (
    AuthenticationError,
    ElectroluxApiClient,
    execute_command_with_error_handling,
    format_command_for_appliance,
    string_to_boolean,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)
PARALLEL_UPDATES = 0


def _reported_path_exists(reported_data: dict[str, Any], path: str, attr: str) -> bool:
    """Return True when a capability path exists in reported state.

    Appliance reported payloads mix flat keys (e.g. ``keyTone``) with nested
    objects (e.g. ``userSelections/autoDoorOpener``). The switch setup filter
    needs to recognize both forms so valid nested switches are not dropped as
    phantom capabilities.
    """
    if path in reported_data or attr in reported_data:
        return True

    current: Any = reported_data
    for part in path.split("/"):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]

    return True


def _has_live_state_mapping(entity: Any, reported_data: dict[str, Any]) -> bool:
    """True when the entity's state comes from a different, reported capability.

    The phantom filter below exists because an appliance advertises a
    capability it cannot actually do - Pod wash, AutoDose (#55) - and that key
    is absent from reported state. That absence is evidence of a phantom.

    A command capability is the exception, and ``executeCommand`` on a
    dehumidifier is the case that matters: no appliance in any collected sample
    reports it, because it is never *state*, it is something you send. A
    dehumidifier reporter (#277) found their unit had no working power control,
    and the cause was here - catalog_dh already carries
    ``state_mapping="applianceState"``, declaring where the state really lives.

    So when a catalog entry declares a ``state_mapping`` and that target *is*
    present in reported state, absence of the entity's own key is by design, not
    evidence of a phantom. The signal is general: it rescues every command
    capability declared this way, without hardcoding a capability name.

    Scope is deliberately narrow, and it is worth being precise about why.
    Only catalog_dh declares that mapping, so only dehumidifiers (Husky, DH)
    are affected - they have no climate entity and need this switch. Air
    conditioners (catalog_ac: AC, Azul, Bogong, Telica) do **not** declare it,
    so they keep dropping executeCommand, and that is correct: their climate
    entity already owns power. ``climate.py`` lists ``HVACMode.OFF`` in
    ``hvac_modes`` and powers the unit off with
    ``_send_command("executeCommand", "OFF")``. Giving them a second power
    switch would duplicate a control they already have, over the same
    capability.
    """
    entry = getattr(entity, "catalog_entry", None)
    mapping = getattr(entry, "state_mapping", None) if entry is not None else None
    # ``state_mapping`` is declared as a str on ElectroluxDevice. Require a real
    # string rather than trusting truthiness: an unmatched catalog entry is None,
    # and anything non-str here must not reach ``_reported_path_exists``, which
    # splits the path on "/".
    if not isinstance(mapping, str) or not mapping:
        return False
    return _reported_path_exists(reported_data, mapping, mapping)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure switch platform."""
    coordinator = entry.runtime_data
    if appliances := coordinator.data.get("appliances", None):
        for appliance_id, appliance in appliances.appliances.items():
            entities = [entity for entity in appliance.entities if entity.entity_type == SWITCH]

            filtered_switches: list[Any] = []
            reported_data = appliance.reported_state or {}

            for entity in entities:
                # Filter out phantom/ghost capabilities (Issue #55)
                # If a property path or capability key is absent from the reported state,
                # the appliance hardware does not support it (e.g., Pod wash, AutoDose).
                # Write-only caps (access == "write") are exempt: they never appear in
                # reported state by design, so absence is not evidence of non-support.
                # So are command caps whose state comes from elsewhere via
                # state_mapping: executeCommand is never reported by any appliance, and
                # the cloud reports it "readwrite" rather than "write" on several
                # models, which this filter would otherwise drop. Only catalog_dh
                # declares that mapping, so this restores dehumidifier power control
                # only - air conditioners are deliberately left alone because their
                # climate entity already provides it (#277).
                if entity.json_path and not _reported_path_exists(reported_data, entity.json_path, entity.entity_attr):
                    cap_access = entity.capability.get("access") if entity.capability else None
                    if cap_access != "write" and not _has_live_state_mapping(entity, reported_data):
                        _LOGGER.debug(
                            "Skipping phantom switch entity %s for appliance %s (not present in reported state)",
                            entity.entity_attr,
                            appliance_id,
                        )
                        continue

                filtered_switches.append(entity)

            _LOGGER.debug(
                "Electrolux add %d SWITCH entities to registry for appliance %s (filtered from %d)",
                len(filtered_switches),
                appliance_id,
                len(entities),
            )

            if filtered_switches:
                async_add_entities(filtered_switches)


class ElectroluxSwitch(ElectroluxEntity, SwitchEntity):
    """Electrolux switch class."""

    @property
    def entity_domain(self):
        """Entity domain for the entry. Used for consistent entity_id."""
        return SWITCH

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on, None if state is unknown (e.g. offline)."""
        # While the appliance is offline the cloud keeps reporting the last known
        # values, so a positive on/off claim would be stale. Report "unknown"
        # instead, matching the convention settled for sensor/number/binary_sensor
        # (#15, #231).
        if self.entity_attr != "connectivityState" and not self.is_connected():
            return None

        value = self.extract_value()

        if value is None:
            # ``state_mapping`` resolves the state from raw reported values via
            # ``get_state_attr``, which has no offline guard of its own — the
            # early return above is what keeps this fallback from reviving a
            # stale value while the appliance is offline (#231).
            if self.catalog_entry and self.catalog_entry.state_mapping:
                mapping = self.catalog_entry.state_mapping
                value = self.get_state_attr(mapping)

        if value is None:
            return None

        # Handle boolean values
        if isinstance(value, bool):
            return value

        # Handle string values like "ON"/"OFF"
        if isinstance(value, str):
            return bool(string_to_boolean(value, fallback=False))

        # For other types, try to convert to boolean
        return bool(value)

    async def switch(self, value: bool | str) -> None:
        """Control switch state."""
        # Check if appliance is connected before sending command
        if not self.is_connected():
            connectivity_state = self.reported_state.get("connectivityState", "unknown")
            _LOGGER.warning(
                "Appliance %s is not connected (state: %s), cannot set %s",
                self.pnc_id,
                connectivity_state,
                self.entity_attr,
            )
            raise HomeAssistantError(
                f"Appliance is offline (current state: {connectivity_state}). "
                "Please check that the appliance is plugged in, has network connectivity and is connected to cloud services.",
                translation_domain=DOMAIN,
                translation_key="appliance_offline",
                translation_placeholders={"state": str(connectivity_state)},
            )
        # that only the API can accurately validate. Error handling in util.py displays friendly messages.

        client: ElectroluxApiClient = self.api
        # Use dynamic capability-based value formatting
        command_value = format_command_for_appliance(self.capability, self.entity_attr, value)

        command: dict[str, Any]
        if not self.is_dam_appliance:
            # Legacy appliances: send as top-level property, but respect entity_source
            # when the capability key has a slash.
            if self.entity_source == "userSelections":
                # Build the full current userSelections payload so that appliances
                # which treat partial writes as full replacements (resetting omitted
                # options to defaults) keep their sibling options intact.
                full_selections = self._build_full_user_selections(self.entity_attr, command_value)
                # Always bundle programUID, for appliance-level keys too (#232).
                # Dropping it was tried in v3.8.0 and reset the selected program
                # on hardware: timeToEnd 16200 -> 780, ecoScore 7 -> 1, display
                # 4:30 -> 0:13. The key may still be ignored by the cloud, which
                # is what the warning is for; the program must not be damaged.
                if full_selections.get("programUID"):
                    self._warn_if_appliance_level_write(self.entity_attr)
                    command = {"userSelections": full_selections}
                else:
                    command = {self.entity_source: {self.entity_attr: command_value}}
            elif self.entity_source:
                command = {self.entity_source: {self.entity_attr: command_value}}
            else:
                command = {self.entity_attr: command_value}
        elif self.entity_source:
            if self.entity_source == "userSelections":
                # Build the full current userSelections payload (DAM path).
                full_selections = self._build_full_user_selections(self.entity_attr, command_value)
                # See the legacy branch above: programUID is always bundled.
                if full_selections.get("programUID"):
                    self._warn_if_appliance_level_write(self.entity_attr)
                    command = {self.entity_source: full_selections}
                else:
                    command = {self.entity_source: {self.entity_attr: command_value}}
            else:
                command = {self.entity_source: {self.entity_attr: command_value}}
        else:
            command = {self.entity_attr: command_value}

        # Wrap DAM commands in the required format
        if self.is_dam_appliance:
            command = {"commands": [command]}  # type: ignore[dict-item]

        _LOGGER.debug("Electrolux set value")
        try:
            await execute_command_with_error_handling(
                client, self.pnc_id, command, self.entity_attr, _LOGGER, self.capability
            )
        except AuthenticationError as auth_ex:
            # Handle authentication errors by triggering reauthentication
            _coordinator: ElectroluxCoordinator = self.coordinator  # type: ignore[assignment]
            await _coordinator.handle_authentication_error(auth_ex)
            raise
        except Exception:
            # Re-raise any errors from execute_command_with_error_handling
            raise

        # Optimistically update local state using base class helper method
        self._apply_optimistic_update(self.entity_attr, command_value)

        # Schedule a follow-up state refresh — some switch properties are not pushed
        # via SSE by the Electrolux cloud, so the optimistic update is the only way
        # HA learns the state without a follow-up poll.
        cast(ElectroluxCoordinator, self.coordinator)._schedule_state_refresh(self.pnc_id)

        _LOGGER.debug("Electrolux set value completed")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if self.capability and self.capability.get("type") == "string":
            # String enum toggle (e.g., fastMode)
            await self.switch("ON")
        else:
            # Normal boolean switch
            await self.switch(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if self.capability and self.capability.get("type") == "string":
            await self.switch("OFF")
        else:
            await self.switch(False)
