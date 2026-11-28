"""Vacuum platform for Electrolux."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.vacuum import Segment, StateVacuumEntity
from homeassistant.components.vacuum.const import (
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)

from .const import VACUUM
from .entity import ElectroluxEntity
from .util import execute_command_with_error_handling

_LOGGER: logging.Logger = logging.getLogger(__package__)

# ── Zone cleaning service ─────────────────────────────────────────────────────

SERVICE_START_ZONE_CLEANING = "start_zone_cleaning"

SERVICE_START_ZONE_CLEANING_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("persistent_map_id"): vol.All(cv.string, vol.Length(min=1)),
        vol.Required("zones"): vol.All(
            vol.Length(min=1),
            [
                vol.Schema(
                    {
                        vol.Required("zone_id"): vol.All(cv.string, vol.Length(min=1)),
                        vol.Optional("power_mode", default=1): vol.Any(
                            vol.All(vol.Coerce(int), vol.Range(min=1, max=3)),
                            vol.In(["Eco", "Standard", "Power"]),
                        ),
                    }
                )
            ],
        ),
    }
)


# ── Appliance type sets ───────────────────────────────────────────────────────

# All appliance types that get a vacuum entity.
# Extend this tuple as new RVC models are confirmed.
_RVC_TYPES = {"PUREi9", "Gordias", "Cybele", "700series"}

# PUREi9 uses a legacy integer robotStatus (1-14), uppercase CleaningCommand, and numeric powerMode.
# All other types (Gordias, Cybele, 700series) use the modern string state +
# camelCase cleaningCommand + vacuumMode API.
_PUREI9_TYPES = {"PUREi9"}

# Segment ids combine the interactive map id and the zone id, so areas from
# several maps (e.g. one per floor) can be offered at the same time.
_SEGMENT_ID_SEPARATOR = ":"
_DEFAULT_ZONE_POWER_MODE = 2

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
    5: VacuumActivity.RETURNING,  # Returning to the dock
    6: VacuumActivity.PAUSED,  # Paused returning
    7: VacuumActivity.RETURNING,  # Returning for pitstop (recharge mid-clean)
    8: VacuumActivity.PAUSED,  # Paused returning for pitstop
    9: VacuumActivity.DOCKED,  # Charging
    10: VacuumActivity.DOCKED,  # Sleeping
    11: VacuumActivity.ERROR,  # Error
    12: VacuumActivity.DOCKED,  # Pitstop (charging mid-clean)
    13: VacuumActivity.IDLE,  # Manual steering
    14: VacuumActivity.IDLE,  # Firmware upgrade
}

# ── Fan speed / vacuum mode lists ─────────────────────────────────────────────

# Sample-backed modern values only. The current Cybele diagnostic shows these
# values in reported state; avoid inventing additional labels without proof.
_MODERN_FAN_SPEEDS: list[str] = [
    "energySaving",
    "max",
]

# PUREi9 uses integer powerMode (1-3) in the API but we expose human-readable
# labels to the user.  The bidirectional mapping keeps the vacuum entity and
# the command sender in sync.
_PUREI9_FAN_SPEEDS: list[str] = ["Eco", "Standard", "Power"]
_PUREI9_SPEED_TO_INT: dict[str, int] = {"Eco": 1, "Standard": 2, "Power": 3}
_PUREI9_INT_TO_SPEED: dict[int, str] = {v: k for k, v in _PUREI9_SPEED_TO_INT.items()}

# PUREi9 gen 1 (original Pure i9) uses a boolean ecoMode in reported state
# instead of the integer powerMode.  The device only has two modes: Eco and
# Power.  The API rejects direct ecoMode writes, so we send powerMode
# integers (1=Eco, 3=Power) as a workaround.
# See https://github.com/TTLucian/ha-electrolux/issues/81
# and https://github.com/JohNan/homeassistant-wellbeing/pull/194
_PUREI9_GEN1_FAN_SPEEDS: list[str] = ["Eco", "Power"]
_PUREI9_GEN1_SPEED_TO_INT: dict[str, int] = {"Eco": 1, "Power": 3}
_PUREI9_GEN1_ECO_TO_SPEED: dict[bool, str] = {True: "Eco", False: "Power"}
_PUREI9_GEN1_SPEED_TO_ECO: dict[str, bool] = {"Eco": True, "Power": False}


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

    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_START_ZONE_CLEANING,
        SERVICE_START_ZONE_CLEANING_SCHEMA,
        "async_clean_zones",
    )


# ── Entity class ──────────────────────────────────────────────────────────────


class ElectroluxVacuum(ElectroluxEntity, StateVacuumEntity):
    """Electrolux vacuum entity.

    Supports two API generations:

    Legacy (PUREi9):
        State:    robotStatus  (int 1-14)
        Commands: CleaningCommand (play / stop / pause / home)
        Speed:    powerMode (int 1-3) — gen 2 (Pure i9.2)
                  ecoMode (boolean)  — gen 1 (original Pure i9, 2 modes only)

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

    @property
    def _is_purei9_gen1(self) -> bool:
        """Detect gen 1 Pure i9 (original, uses boolean ecoMode).

        Gen 1 devices report ``ecoMode`` (boolean) in state but NOT
        ``powerMode`` (int).  Gen 2 (Pure i9.2) reports ``powerMode`` (int).
        Both gens expose the ``powerMode`` capability (min=1, max=3) in the
        API, so capability inspection alone cannot distinguish them.
        """
        if not self._is_purei9:
            return False
        return self.get_state_attr("ecoMode") is not None and self.get_state_attr("powerMode") is None

    # ── Entity metadata ───────────────────────────────────────────────────────

    @property
    def entity_domain(self) -> str:
        """Entity domain for the entry. Used for consistent entity_id."""
        return VACUUM

    @property
    def supported_features(self) -> VacuumEntityFeature:
        """Return the list of supported features."""
        features = (
            VacuumEntityFeature.STATE
            | VacuumEntityFeature.START
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.RETURN_HOME
            | VacuumEntityFeature.FAN_SPEED
        )
        if self._supports_custom_play:
            features |= VacuumEntityFeature.CLEAN_AREA
        return features

    @property
    def _supports_custom_play(self) -> bool:
        """Return True when the PUREi9 accepts CustomPlay (zone) commands.

        The API reports the capability flattened as ``CustomPlay/persistentMapId``
        and ``CustomPlay/zones``, so check the nested key as well.
        """
        if not self._is_purei9:
            return False
        try:
            data = self.get_appliance.data
            return bool(data.get_capability("CustomPlay") or data.get_capability("CustomPlay/zones"))
        except AttributeError, KeyError, TypeError:
            return False

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
        except ValueError:
            _LOGGER.debug(
                "Invalid robotStatus value '%s' for appliance %s",
                status_value,
                self.pnc_id,
            )
            return None
        except TypeError:
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
            except TypeError:
                _LOGGER.debug(
                    "Invalid batteryStatus value '%s' for appliance %s",
                    value,
                    self.pnc_id,
                )
                return None
            except ValueError:
                _LOGGER.debug(
                    "Invalid batteryStatus value '%s' for appliance %s",
                    value,
                    self.pnc_id,
                )
                return None

            battery_min, battery_max = self._battery_status_range()
            if battery_min is None or battery_max is None or battery_max <= battery_min:
                return round(battery_value)

            if battery_max == 100 and battery_min in (0, 1):
                return round(battery_value)

            battery_value = max(float(battery_min), min(float(battery_max), battery_value))
            percentage = ((battery_value - battery_min) / (battery_max - battery_min)) * 100
            return round(max(0.0, min(100.0, percentage)))
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
        except Exception:
            pass

        if self._is_purei9:
            return 1, 6

        return None, None

    @property
    def fan_speed(self) -> str | None:
        """Return the current fan speed / vacuum mode.

        PUREi9 gen 2 reports an integer powerMode (1-3); translate to the
        human-readable label (Eco / Standard / Power).
        PUREi9 gen 1 reports a boolean ecoMode; translate to Eco / Power.
        """
        if self._is_purei9_gen1:
            eco = self.get_state_attr("ecoMode")
            if eco is None:
                return None
            return _PUREI9_GEN1_ECO_TO_SPEED.get(bool(eco))

        attr = "powerMode" if self._is_purei9 else "vacuumMode"
        value = self.get_state_attr(attr)
        if value is None:
            return None
        if self._is_purei9:
            try:
                return _PUREI9_INT_TO_SPEED.get(int(value))
            except ValueError:
                return None
            except TypeError:
                return None
        return str(value)

    @property
    def fan_speed_list(self) -> list[str]:
        """Return the list of available fan speeds.

        For PUREi9 gen 1 (original) the device only has 2 modes (Eco, Power)
        controlled via boolean ecoMode.  For PUREi9 gen 2 (Pure i9.2) the
        speed list is built dynamically from the device's actual powerMode
        capability (min/max).
        See https://github.com/TTLucian/ha-electrolux/issues/81
        """
        if not self._is_purei9:
            # Prefer the values the appliance actually declares. Cybele reports
            # energySaving/max, but Gordias (UltimateHome 700) declares four:
            # quiet, energySaving, standard, powerful — so the hardcoded list
            # both hid two real modes and offered a "max" the device rejects.
            declared = self._declared_fan_speeds("vacuumMode")
            if declared:
                return declared
            return _MODERN_FAN_SPEEDS

        if self._is_purei9_gen1:
            return _PUREI9_GEN1_FAN_SPEEDS

        pm_min, pm_max = self._purei9_power_mode_range()
        return [_PUREI9_INT_TO_SPEED[i] for i in range(pm_min, pm_max + 1) if i in _PUREI9_INT_TO_SPEED]

    def _declared_fan_speeds(self, attr_name: str) -> list[str]:
        """Return the string values an appliance declares for a capability.

        Returns an empty list when the capability is absent, unreadable, or
        declares no values, so callers can fall back to a known-good default.
        """
        try:
            appliance = self.get_appliance
            if not appliance or not getattr(appliance, "data", None):
                return []
            cap = appliance.data.get_capability(attr_name)
            if not isinstance(cap, dict):
                return []
            values = cap.get("values")
            if not isinstance(values, dict):
                return []
            return [str(value) for value in values]
        except TypeError, ValueError:
            _LOGGER.debug(
                "Could not read %s capability values for %s, using default list",
                attr_name,
                self.pnc_id,
            )
            return []

    def _purei9_power_mode_range(self) -> tuple[int, int]:
        """Return the (min, max) powerMode range from device capabilities.

        Falls back to (1, 3) when the capability cannot be read.
        """
        try:
            appliance = self.get_appliance
            if hasattr(appliance, "data") and appliance.data:
                cap = appliance.data.get_capability("powerMode")
                if isinstance(cap, dict):
                    pm_min = int(cap.get("min", 1))
                    pm_max = int(cap.get("max", 3))
                    return pm_min, pm_max
        except TypeError, ValueError:
            _LOGGER.debug(
                "Could not read powerMode capability for %s, using default range",
                self.pnc_id,
            )
        return 1, 3

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
        """Set the vacuum mode / suction level.

        PUREi9 gen 2 accepts the human-readable label (Eco / Standard / Power)
        and translates it to the integer the API expects.
        PUREi9 gen 1 only has 2 modes (Eco / Power); the API rejects direct
        ecoMode writes, so we send powerMode integers (1 / 3) as a workaround
        and optimistically update ecoMode for immediate UI feedback.
        """
        if self._is_purei9_gen1:
            pm_value = _PUREI9_GEN1_SPEED_TO_INT.get(fan_speed)
            if pm_value is None:
                _LOGGER.error(
                    "Invalid PUREi9 gen 1 fan speed '%s' — expected one of %s",
                    fan_speed,
                    _PUREI9_GEN1_FAN_SPEEDS,
                )
                return
            await self._send_command("powerMode", pm_value)
            # Optimistically update ecoMode (what fan_speed reads for gen 1)
            eco_value = _PUREI9_GEN1_SPEED_TO_ECO.get(fan_speed)
            if eco_value is not None:
                self._apply_optimistic_update("ecoMode", eco_value)
            return

        attr = "powerMode" if self._is_purei9 else "vacuumMode"
        if self._is_purei9:
            value: Any = _PUREI9_SPEED_TO_INT.get(fan_speed)
            if value is None:
                # Fall back to direct integer for backward compatibility
                try:
                    value = int(fan_speed)
                except ValueError:
                    _LOGGER.error(
                        "Invalid PUREi9 fan speed '%s' — expected one of %s",
                        fan_speed,
                        _PUREI9_FAN_SPEEDS,
                    )
                    return
                except TypeError:
                    _LOGGER.error(
                        "Invalid PUREi9 fan speed '%s' — expected one of %s",
                        fan_speed,
                        _PUREI9_FAN_SPEEDS,
                    )
                    return
        else:
            value = fan_speed
        await self._send_command(attr, value)

    async def async_clean_zones(
        self,
        persistent_map_id: str,
        zones: list[dict[str, Any]],
    ) -> None:
        """Start a zone-based cleaning session on appliances that support CustomPlay.

        Sends a CustomPlay command targeting specific zones on a persistent map.
        Zone UUIDs and the persistent map UUID are found in the integration
        diagnostics (mapData/mapMatch/zones and persistentMapsCreated/mapId).

        The power_mode parameter accepts either the integer (1-3) or the
        human-readable label (Eco / Standard / Power).
        """
        # The API reports CustomPlay flattened ("CustomPlay/persistentMapId",
        # "CustomPlay/zones"), so a lookup of "CustomPlay" alone never matches.
        data = self.get_appliance.data
        if not (data.get_capability("CustomPlay") or data.get_capability("CustomPlay/zones")):
            raise HomeAssistantError("Zone cleaning is not supported on this device.")

        # Translate human-readable labels to the integer the API expects
        api_zones = []
        for z in zones:
            pm = z["power_mode"]
            if isinstance(pm, str):
                if pm not in _PUREI9_SPEED_TO_INT:
                    _LOGGER.warning(
                        "Unknown power mode '%s' for zone %s — defaulting to Eco (1)",
                        pm,
                        z["zone_id"],
                    )
                pm = _PUREI9_SPEED_TO_INT.get(pm, 1)
            api_zones.append({"goZonesId": z["zone_id"], "powerMode": pm})

        command = {
            "CustomPlay": {
                "persistentMapId": persistent_map_id,
                "zones": api_zones,
            }
        }

        _LOGGER.debug("Electrolux zone cleaning command: %s", command)

        await execute_command_with_error_handling(
            self.api, self.pnc_id, command, "CustomPlay", _LOGGER, self.capability
        )

    # ── Clean area (HA segments) ──────────────────────────────────────────────

    async def async_get_segments(self) -> list[Segment]:
        """Return the clean zones of every interactive map as HA segments.

        Avoid zones are skipped. The map name is used as the segment group so
        zones from several maps can be told apart in the area mapping dialog.
        """
        segments: list[Segment] = []
        for api_map in await self.api.get_interactive_maps(self.pnc_id):
            map_id = api_map.get("id")
            if not map_id:
                continue
            for zone in api_map.get("zones") or []:
                if not isinstance(zone, dict) or zone.get("zoneType") != "clean" or not zone.get("id"):
                    continue
                segments.append(
                    Segment(
                        id=f"{map_id}{_SEGMENT_ID_SEPARATOR}{zone['id']}",
                        name=zone.get("name") or zone["id"],
                        group=api_map.get("name") or None,
                    )
                )
        return segments

    async def async_clean_segments(self, segment_ids: list[str], **kwargs: Any) -> None:
        """Clean the given segments (zones of one interactive map) with CustomPlay."""
        if not self._supports_custom_play:
            raise HomeAssistantError("Area cleaning is not supported on this device.")

        map_ids: set[str] = set()
        zone_ids: list[str] = []
        for segment_id in segment_ids:
            map_id, separator, zone_id = segment_id.partition(_SEGMENT_ID_SEPARATOR)
            if not separator or not map_id or not zone_id:
                raise HomeAssistantError(f"Unknown area segment '{segment_id}'.")
            map_ids.add(map_id)
            zone_ids.append(zone_id)

        if not zone_ids:
            return
        if len(map_ids) > 1:
            raise HomeAssistantError("Areas from different maps cannot be cleaned in one run.")
        map_id = map_ids.pop()

        # Use each zone's own power mode from the map, else the robot's current one
        # (gen 1 PUREi9: Eco/Power from ecoMode).
        zone_power_modes: dict[str, Any] = {}
        for api_map in await self.api.get_interactive_maps(self.pnc_id):
            if api_map.get("id") == map_id:
                zone_power_modes = {
                    zone["id"]: zone.get("powerMode")
                    for zone in api_map.get("zones") or []
                    if isinstance(zone, dict) and zone.get("id")
                }
                break
        fallback_power_mode = self._zone_fallback_power_mode()

        command = {
            "CustomPlay": {
                "persistentMapId": map_id,
                "zones": [
                    {
                        "zoneId": zone_id,
                        "powerMode": power_mode
                        if isinstance(power_mode := zone_power_modes.get(zone_id), int)
                        and not isinstance(power_mode, bool)
                        else fallback_power_mode,
                    }
                    for zone_id in zone_ids
                ],
            }
        }

        _LOGGER.debug("Electrolux area cleaning command: %s", command)

        await execute_command_with_error_handling(
            self.api, self.pnc_id, command, "CustomPlay", _LOGGER, self.capability
        )

    def _zone_fallback_power_mode(self) -> int:
        """Return the power mode for a zone that has none stored on the map.

        Gen 1 PUREi9 has only Eco (1) and Power (3) and reports a boolean ecoMode
        in place of powerMode, so Standard (2) must never be sent to it.
        """
        if self._is_purei9_gen1:
            return _PUREI9_GEN1_SPEED_TO_INT["Eco" if self.get_state_attr("ecoMode") else "Power"]
        current_power_mode: Any = self.get_state_attr("powerMode")
        if isinstance(current_power_mode, int) and not isinstance(current_power_mode, bool):
            return current_power_mode
        return _DEFAULT_ZONE_POWER_MODE

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
            await execute_command_with_error_handling(client, self.pnc_id, command, attr, _LOGGER, self.capability)
            self._apply_optimistic_update(attr, value)
        except Exception as ex:
            _LOGGER.error("Electrolux vacuum command failed for %s: %s", attr, ex)
            raise
