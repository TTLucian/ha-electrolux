"""Defined catalog of entities for oven type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from .model import ElectroluxDevice

CATALOG_OVEN: dict[str, ElectroluxDevice] = {
    "alerts": ElectroluxDevice(
        capability_info={"access": "read", "type": "alert"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert",
    ),
    "applianceMode": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon=None,
        entity_registry_enabled_default=False,
    ),
    "applianceState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "ALARM": {},
                "DELAYED_START": {},
                "END_OF_CYCLE": {},
                "IDLE": {},
                "OFF": {},
                "PAUSED": {},
                "READY_TO_START": {},
                "RUNNING": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:state-machine",
        entity_registry_enabled_default=False,
    ),
    "applianceTotalWorkingTime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timelapse",
        entity_registry_enabled_default=False,
    ),
    "applianceType": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "entity_source": "applianceInfo",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:information-outline",
    ),
    "capabilityHash": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "entity_source": "applianceInfo",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:lock",
        entity_registry_enabled_default=False,
    ),
    "connectivityState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:lan-connect",
    ),
    "cpv": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:numeric",
        entity_registry_enabled_default=False,
    ),
    "cavityLight": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:lightbulb",
    ),
    "cyclePhase": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon=None,
    ),
    "cycleSubPhase": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon=None,
    ),
    "defrostRoutineState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:snowflake-thermometer",
        entity_registry_enabled_default=False,
    ),
    "defrostTemperature": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "displayFoodProbeTemperature": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "displayFoodProbeTemperatureC": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "displayTemperature": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "displayTemperatureC": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "displayTemperatureF": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "executeCommand": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
            "values": {"START": {}, "STOPRESET": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:play-pause",
    ),
    "doorState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"CLOSED": {}, "OPEN": {}},
        },
        device_class=BinarySensorDeviceClass.DOOR,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fridge-variant",
    ),
    "foodProbeInsertionState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"INSERTED": {}, "NOT_INSERTED": {}},
        },
        device_class=BinarySensorDeviceClass.PLUG,
        unit=None,
        entity_category=None,
        entity_icon="mdi:thermometer-probe",
    ),
    "foodProbeSupported": ElectroluxDevice(
        capability_info={
            "access": "constant",
            "type": "enum",
            "values": {"NOT_SUPPORTED": {}, "SUPPORTED": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:thermometer-probe",
        entity_registry_enabled_default=False,
    ),
    "processPhase": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:state-machine",
    ),
    "program": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:chef-hat",
    ),
    "remoteControl": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:remote",
    ),
    "runningTime": ElectroluxDevice(
        capability_info={"access": "read", "default": 0, "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timelapse",
    ),
    "startTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": "INVALID_OR_NOT_SET_TIME",
            "max": 86340,  # 1439 minutes * 60 seconds
            "min": 0,
            "step": 60,  # 1 minute in seconds
            "type": "number",
            "values": {"INVALID_OR_NOT_SET_TIME": {"disabled": True}},
        },
        device_class=None,
        unit=UnitOfTime.SECONDS,  # Changed from MINUTES
        entity_category=None,
        entity_icon="mdi:clock-start",
    ),
    "targetDuration": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": 0,
            "max": 86340,  # 1439 minutes * 60 seconds
            "min": 0,
            "step": 60,  # 1 minute in seconds
            "type": "number",
        },
        device_class=None,
        unit=UnitOfTime.SECONDS,  # Changed from MINUTES
        entity_category=None,
        entity_icon="mdi:timelapse",
    ),
    "targetFoodProbeTemperatureC": ElectroluxDevice(
        capability_info={"access": "readwrite", "step": 1.0, "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer-probe",
    ),
    "targetFoodProbeTemperatureF": ElectroluxDevice(
        capability_info={"access": "readwrite", "step": 1.0, "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer-probe",
    ),
    "targetMicrowavePower": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.ENERGY,
        unit="W",
        entity_category=None,
        entity_icon="mdi:microwave",
    ),
    "targetTemperatureC": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "targetTemperatureF": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "timeToEnd": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timelapse",
    ),
    "waterTankEmpty": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"STEAM_TANK_EMPTY": {}, "STEAM_TANK_FULL": {}},
        },
        device_class=BinarySensorDeviceClass.BATTERY,
        unit=None,
        entity_category=None,
        entity_icon="mdi:water",
    ),
    "waterTrayInsertionState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"INSERTED": {}, "NOT_INSERTED": {}},
        },
        device_class=BinarySensorDeviceClass.PLUG,
        unit=None,
        entity_category=None,
        entity_icon="mdi:tray",
    ),
    "linkQualityIndicator": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "entity_source": "networkInterface",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:wifi-strength-3",
    ),
    "otaState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "entity_source": "networkInterface",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:update",
    ),
    "swVersion": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "entity_source": "networkInterface",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:information-outline",
    ),
}
