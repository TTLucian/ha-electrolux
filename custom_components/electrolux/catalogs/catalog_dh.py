"""Defined catalog of entities for dehumidifier type devices (DH, Husky)."""

from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import PERCENTAGE, EntityCategory, Platform, UnitOfTime

from ..model import ElectroluxDevice

CATALOG_DH: dict[str, ElectroluxDevice] = {
    # Power control — ON/OFF (button entity; SDK dh_config.py EXECUTE_COMMAND_ON/OFF)
    "executeCommand": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
            "values": {
                "ON": {},
                "OFF": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:power",
        friendly_name="Power",
        state_mapping="applianceState",
    ),
    # Current humidity reading (read-only sensor)
    "sensorHumidity": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:water-percent",
        friendly_name="Humidity",
    ),
    # Target humidity setpoint (read-write number control)
    "targetHumidity": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 35,
            "max": 85,
            "step": 5,
        },
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:water-percent",
        friendly_name="Target Humidity",
    ),
    # Delayed start / stop timers
    "startTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "default": 0,
            "max": 86400,
            "min": 0,
            "step": 1800,
            "values": {"INVALID_OR_NOT_SET_TIME": {}},
        },
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=None,
        entity_icon="mdi:clock-start",
        friendly_name="Start Time",
    ),
    "stopTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "default": 0,
            "max": 86400,
            "min": 0,
            "step": 1800,
            "unit": "s",
        },
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=None,
        entity_icon="mdi:clock-end",
        friendly_name="Stop Time",
    ),
    # Additional air treatment toggle
    "cleanAirMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "OFF": {},
                "ON": {},
            },
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:air-filter",
        friendly_name="Clean Air Mode",
    ),
    # Display light
    "displayLight": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "DISPLAY_LIGHT_0": {},
                "DISPLAY_LIGHT_1": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:lightbulb",
        friendly_name="Display Light",
        entity_platform=Platform.SELECT,
    ),
    # Fan speed (select entity)
    # NOTE: The SDK reads values dynamically from device capabilities.
    # Placeholder values below will be replaced by whatever the device
    # actually reports. Unverified until a real diagnostic is provided.
    "fanSpeedSetting": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "LOW": {},
                "MIDDLE": {},
                "HIGH": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
        friendly_name="Fan Speed",
        entity_platform=Platform.SELECT,
    ),
    # Current fan speed (read-only sensor)
    "fanSpeedState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "LOW": {},
                "MIDDLE": {},
                "HIGH": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
        friendly_name="Fan Speed State",
    ),
    # Filter maintenance status
    "filterState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "BUY": {},
                "CHANGE": {},
                "CLEAN": {},
                "GOOD": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="Filter State",
    ),
    # Operating mode (select entity)
    # NOTE: The SDK reads values dynamically from device capabilities.
    # Placeholder values below will be replaced by whatever the device
    # actually reports. Unverified until a real diagnostic is provided.
    "mode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUTO": {},
                "CONTINUOUS": {},
                "DRY": {},
                "OFF": {"disabled": True},
                "QUIET": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:water-sync",
        friendly_name="Mode",
        entity_platform=Platform.SELECT,
    ),
    # Water bucket fill level
    "waterBucketLevel": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:bucket-outline",
        friendly_name="Water Bucket Level",
    ),
}
