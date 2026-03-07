"""Defined catalog of entities for robot vacuum type devices (PUREi9, Gordias, Cybele, 700series).

Different robot vacuum models use different API key names for equivalent concepts:
- PUREi9 (older):  robotStatus (int 1-14), CleaningCommand, batteryStatus, powerMode
- Gordias/Cybele/700series (newer):  state (string), cleaningCommand, batteryStatus,
                                      chargingStatus, vacuumMode

Because the catalog is matched against the device's actual capabilities, placing all
keys in one catalog is safe — each device will only expose its own subset.
"""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import PERCENTAGE, EntityCategory

from ..model import ElectroluxDevice

# PUREi9 robotStatus integer values (from SDK rvc_config.py IS_DOCKED_MAP/IS_PAUSED_MAP)
# Keys are strings because value_mapping expects dict[float | str, str]
_PUREI9_ROBOT_STATUS_VALUES: dict[float | str, str] = {
    "1": "Cleaning",
    "2": "Paused cleaning",
    "3": "Spot cleaning",
    "4": "Paused spot cleaning",
    "5": "Zone cleaning",
    "6": "Paused zone cleaning",
    "7": "Collecting",
    "8": "Paused collecting",
    "9": "Docked",
    "10": "Sleeping",
    "11": "Error",
    "12": "Fully charged",
    "13": "Going home",
    "14": "End of life",
}

CATALOG_RVC: dict[str, ElectroluxDevice] = {
    # ── Battery ────────────────────────────────────────────────────────────────
    "batteryStatus": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.BATTERY,
        unit=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:battery",
        friendly_name="Battery",
    ),
    # ── PUREi9 ─────────────────────────────────────────────────────────────────
    # Integer status (1-14); human-readable via value_mapping
    "robotStatus": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "values": {
                str(k): {"name": v} for k, v in _PUREI9_ROBOT_STATUS_VALUES.items()
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=None,
        entity_icon="mdi:robot-vacuum",
        friendly_name="Robot Status",
        value_mapping=_PUREI9_ROBOT_STATUS_VALUES,
    ),
    # Cleaning command (read-write select)
    "CleaningCommand": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "play": {"icon": "mdi:play"},
                "stop": {"icon": "mdi:stop"},
                "pause": {"icon": "mdi:pause"},
                "home": {"icon": "mdi:home"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:robot-vacuum",
        friendly_name="Cleaning Command",
    ),
    # Power/cleaning intensity mode
    "powerMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "QUIET": {"icon": "mdi:fan-speed-1"},
                "SMART": {"icon": "mdi:fan-speed-2"},
                "POWER": {"icon": "mdi:fan-speed-3"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:speedometer",
        friendly_name="Power Mode",
    ),
    # ── Gordias / Cybele / 700series ────────────────────────────────────────────
    # String state (inProgress / goingHome / idle / paused / sleeping / …)
    "state": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "inProgress": {},
                "goingHome": {},
                "idle": {},
                "paused": {},
                "sleeping": {},
                "vacuuming": {},
                "mopping": {},
                "pitStop": {},
                "stationAction": {},
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=None,
        entity_icon="mdi:robot-vacuum",
        friendly_name="Cleaning State",
    ),
    # Charging status (string: idle / charging / fullyCharged)
    "chargingStatus": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "idle": {},
                "charging": {},
                "fullyCharged": {},
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:battery-charging",
        friendly_name="Charging Status",
    ),
    # Cleaning command (Gordias/Cybele/700series naming)
    "cleaningCommand": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "startGlobalClean": {"icon": "mdi:play"},
                "stopClean": {"icon": "mdi:stop"},
                "pauseClean": {"icon": "mdi:pause"},
                "resumeClean": {"icon": "mdi:play-pause"},
                "startGoToCharger": {"icon": "mdi:home"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:robot-vacuum",
        friendly_name="Cleaning Command",
    ),
    # Vacuum cleaning mode (select)
    "vacuumMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "QUIET": {"icon": "mdi:fan-speed-1"},
                "SMART": {"icon": "mdi:fan-speed-2"},
                "POWER": {"icon": "mdi:fan-speed-3"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:speedometer",
        friendly_name="Vacuum Mode",
    ),
}
