"""Vacuum platform for Electrolux."""

import logging
from typing import Any

from homeassistant.components.vacuum import StateVacuumEntity
from homeassistant.components.vacuum.const import (
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import VACUUM
from .entity import ElectroluxEntity
from .util import execute_command_with_error_handling

_LOGGER: logging.Logger = logging.getLogger(__package__)


# ── Appliance type sets ───────────────────────────────────────────────────────

# All appliance types that get a vacuum entity.
# Extend this tuple as new RVC models are confirmed.
_RVC_TYPES = {"PUREi9", "Gordias", "Cybele"}

# PUREi9 uses a legacy integer robotStatus (1-14), uppercase CleaningCommand, and numeric powerMode.
# All other types (Gordias, Cybele, 700series) use the modern string state +
# camelCase cleaningCommand + vacuumMode API.
_PUREI9_TYPES = {"PUREi9"}

# ── State → VacuumActivity mappings ──────────────────────────────────────────

# Cybele / Gordias / 700series: string "state" attribute.
#
# Design notes:
#   pitStop   — robot suspends the session to visit the base station for dust
#               collection, mop wash, or water refill, then automatically resumes.
#               The cleaning session is still active, so CLEANING is correct.
#   stationAction — robot is physically docked and the base station is performing
#                   an autonomous action (dust collection, mop drying, …). DOCKED
#                   is the right representation because the robot itself is idle.
#   idle/sleeping — refined to DOCKED when inCharger is True (see _activity_modern).
_MODERN_STATE_TO_ACTIVITY: dict[str, VacuumActivity] = {
    "inProgress": VacuumActivity.CLEANING,
    "vacuuming": VacuumActivity.CLEANING,
    "mopping": VacuumActivity.CLEANING,
    "pitStop": VacuumActivity.CLEANING,
    "stationAction": VacuumActivity.DOCKED,
    "goingHome": VacuumActivity.RETURNING,
    "paused": VacuumActivity.PAUSED,
    "idle": VacuumActivity.IDLE,  # refined to DOCKED if inCharger
    "sleeping": VacuumActivity.IDLE,  # refined to DOCKED if inCharger
}

# PUREi9: integer robotStatus (1-14).
_PUREI9_STATUS_TO_ACTIVITY: dict[int, VacuumActivity] = {
    1: VacuumActivity.CLEANING,  # Cleaning
    2: VacuumActivity.PAUSED,  # Paused cleaning
    3: VacuumActivity.CLEANING,  # Spot cleaning
    4: VacuumActivity.PAUSED,  # Paused spot cleaning
    5: VacuumActivity.CLEANING,  # Zone cleaning
    6: VacuumActivity.PAUSED,  # Paused zone cleaning
    7: VacuumActivity.CLEANING,  # Collecting (returning to dock mid-session)
    8: VacuumActivity.PAUSED,  # Paused collecting
    9: VacuumActivity.DOCKED,  # Docked
    10: VacuumActivity.DOCKED,  # Sleeping
    11: VacuumActivity.ERROR,  # Error
    12: VacuumActivity.DOCKED,  # Fully charged
    13: VacuumActivity.RETURNING,  # Going home
    14: VacuumActivity.ERROR,  # End of life (needs service)
}

# ── Fan speed / vacuum mode lists ─────────────────────────────────────────────

# Sample-backed modern values only. The current Cybele diagnostic shows these
# values in reported state; avoid inventing additional labels without proof.
_MODERN_FAN_SPEEDS: list[str] = [
    "energySaving",
    "max",
]

_PUREI9_FAN_SPEEDS: list[str] = ["1", "2", "3"]


# ── Platform setup ────────────────────────────────────────────────────────────


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure vacuum platform."""
    coordinator = entry.runtime_data
    if appliances := coordinator.data.get("appliances", None):
        entities = []
        for appliance_id, appliance in appliances.appliances.items():
            if appliance.appliance_type in _RVC_TYPES:
                entity = ElectroluxVacuum(
                    coordinator=coordinator,
                    name=appliance.name,
                    config_entry=entry,
                    pnc_id=appliance.pnc_id,
                    entity_type=VACUUM,
                    entity_name="vacuum",
                    entity_attr="vacuum",
                    entity_source=None,
                    capability={},
                    unit=None,
                    device_class=None,
                    entity_category=None,
                    icon="mdi:robot-vacuum",
                    catalog_entry=None,
                    appliance_type=appliance.appliance_type,
                )
                entities.append(entity)
                _LOGGER.debug(
                    "Electrolux created VACUUM entity for appliance %s (type: %s)",
                    appliance_id,
                    appliance.appliance_type,
                )
        async_add_entities(entities)


# ── Entity class ──────────────────────────────────────────────────────────────


class ElectroluxVacuum(ElectroluxEntity, StateVacuumEntity):
    """Electrolux vacuum entity.

    Supports two API generations:

    Legacy (PUREi9):
        State:    robotStatus  (int 1-14)
        Commands: CleaningCommand (play / stop / pause / home)
        Speed:    powerMode (int 1-3)

    Modern (Cybele, Gordias, 700series):
        State:    state (string: idle / inProgress / goingHome / paused / …)
        Commands: cleaningCommand (startGlobalClean / stopClean / pauseClean /
                                   resumeClean / startGoToCharger)
        Speed:    vacuumMode (quiet / energySaving / standard / powerful / max)
    """

    def __init__(
        self,
        coordinator,
        name: str,
        config_entry,
        pnc_id: str,
        entity_type,
        entity_name: str,
        entity_attr: str,
        entity_source,
        capability: dict,
        unit: str | None,
        device_class,
        entity_category,
        icon: str,
        catalog_entry,
        appliance_type: str,
    ) -> None:
        """Initialize the vacuum entity."""
        super().__init__(
            coordinator=coordinator,
            name=name,
            config_entry=config_entry,
            pnc_id=pnc_id,
            entity_type=entity_type,
            entity_name=entity_name,
            entity_attr=entity_attr,
            entity_source=entity_source,
            capability=capability,
            unit=unit,
            device_class=device_class,
            entity_category=entity_category,
            icon=icon,
            catalog_entry=catalog_entry,
        )
        self._appliance_type = appliance_type
        self._is_purei9 = appliance_type in _PUREI9_TYPES

    # ── Entity metadata ───────────────────────────────────────────────────────

    @property
    def entity_domain(self) -> str:
        """Entity domain for the entry. Used for consistent entity_id."""
        return VACUUM

    @property
    def supported_features(self) -> VacuumEntityFeature:
        """Return the list of supported features."""
        return (
            VacuumEntityFeature.STATE
            | VacuumEntityFeature.START
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.RETURN_HOME
            | VacuumEntityFeature.BATTERY
            | VacuumEntityFeature.FAN_SPEED
        )

    # ── State properties ──────────────────────────────────────────────────────

    @property
    def activity(self) -> VacuumActivity | None:
        """Return the current vacuum activity."""
        if self._is_purei9:
            return self._activity_purei9()
        return self._activity_modern()

    def _activity_modern(self) -> VacuumActivity | None:
        """Derive VacuumActivity from the Cybele/Gordias string 'state' attribute."""
        state_value = self.get_state_attr("state")
        if state_value is None:
            return None

        state_str = str(state_value)
        activity = _MODERN_STATE_TO_ACTIVITY.get(state_str)
        if activity is None:
            _LOGGER.debug(
                "Unrecognised RVC state value '%s' for appliance %s",
                state_str,
                self.pnc_id,
            )
            return None

        # Refine idle/sleeping → DOCKED when the robot is physically in the charger.
        # inCharger is a boolean reported attribute; treat any truthy value as True.
        if activity == VacuumActivity.IDLE and self.get_state_attr("inCharger"):
            return VacuumActivity.DOCKED

        return activity

    def _activity_purei9(self) -> VacuumActivity | None:
        """Derive VacuumActivity from the PUREi9 integer robotStatus attribute."""
        status_value = self.get_state_attr("robotStatus")
        if status_value is None:
            return None
        try:
            return _PUREI9_STATUS_TO_ACTIVITY.get(int(status_value))
        except ValueError, TypeError:
            _LOGGER.debug(
                "Invalid robotStatus value '%s' for appliance %s",
                status_value,
                self.pnc_id,
            )
            return None

    @property
    def battery_level(self) -> int | None:
        """Return the battery level as a percentage (0-100)."""
        value = self.get_state_attr("batteryStatus")
        if value is not None:
            try:
                battery_value = float(value)
            except TypeError, ValueError:
                _LOGGER.debug(
                    "Invalid batteryStatus value '%s' for appliance %s",
                    value,
                    self.pnc_id,
                )
                return None

            battery_min, battery_max = self._battery_status_range()
            if battery_min is None or battery_max is None or battery_max <= battery_min:
                return int(round(battery_value))

            if battery_max == 100 and battery_min in (0, 1):
                return int(round(battery_value))

            battery_value = max(
                float(battery_min), min(float(battery_max), battery_value)
            )
            percentage = (
                (battery_value - battery_min) / (battery_max - battery_min)
            ) * 100
            return int(round(max(0.0, min(100.0, percentage))))
        return None

    def _battery_status_range(self) -> tuple[int | None, int | None]:
        """Return the min/max range reported for batteryStatus."""
        try:
            appliance = self.get_appliance
            if hasattr(appliance, "data") and appliance.data:
                capabilities = appliance.data.capabilities or {}
                battery_capability = capabilities.get("batteryStatus")
                if isinstance(battery_capability, dict):
                    battery_min = battery_capability.get("min")
                    battery_max = battery_capability.get("max")
                    if battery_min is not None and battery_max is not None:
                        return int(battery_min), int(battery_max)
        except Exception:  # noqa: BLE001
            pass

        if self._is_purei9:
            return 1, 6

        return None, None

    @property
    def fan_speed(self) -> str | None:
        """Return the current fan speed / vacuum mode."""
        attr = "powerMode" if self._is_purei9 else "vacuumMode"
        value = self.get_state_attr(attr)
        return str(value) if value is not None else None

    @property
    def fan_speed_list(self) -> list[str]:
        """Return the list of available fan speeds."""
        return _PUREI9_FAN_SPEEDS if self._is_purei9 else _MODERN_FAN_SPEEDS

    # ── Commands ───────────────────────────────────────────────────────────────

    async def async_start(self) -> None:
        """Start or resume cleaning.

        When the robot is paused, send a resume command rather than
        startGlobalClean — the latter discards the current session map.
        PUREi9 uses a single "play" command for both cases.
        """
        if self._is_purei9:
            await self._send_command("CleaningCommand", "play")
        elif self.activity == VacuumActivity.PAUSED:
            await self._send_command("cleaningCommand", "resumeClean")
        else:
            await self._send_command("cleaningCommand", "startGlobalClean")

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the current cleaning session."""
        if self._is_purei9:
            await self._send_command("CleaningCommand", "stop")
        else:
            await self._send_command("cleaningCommand", "stopClean")

    async def async_pause(self) -> None:
        """Pause the current cleaning session."""
        if self._is_purei9:
            await self._send_command("CleaningCommand", "pause")
        else:
            await self._send_command("cleaningCommand", "pauseClean")

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Send the robot back to its charger."""
        if self._is_purei9:
            await self._send_command("CleaningCommand", "home")
        else:
            await self._send_command("cleaningCommand", "startGoToCharger")

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set the vacuum mode / suction level."""
        attr = "powerMode" if self._is_purei9 else "vacuumMode"
        value: Any = int(fan_speed) if self._is_purei9 else fan_speed
        await self._send_command(attr, value)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _send_command(self, attr: str, value: Any) -> None:
        """Send a flat command to the appliance.

        RVC appliances are legacy (not DAM) and always use top-level commands
        with no entity_source wrapping.
        """
        client = self.api
        command: dict[str, Any] = {attr: value}

        _LOGGER.debug("Electrolux vacuum command: %s", command)

        try:
            await execute_command_with_error_handling(
                client, self.pnc_id, command, attr, _LOGGER, self.capability
            )
            self._apply_optimistic_update(attr, value)
        except Exception as ex:
            _LOGGER.error("Electrolux vacuum command failed for %s: %s", attr, ex)
            raise
