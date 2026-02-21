"""Defined catalog of entities for oven type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from .model import ElectroluxDevice

CATALOG_OVEN: dict[str, ElectroluxDevice] = {
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
    ),
    "cavityLight": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
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
        entity_icon="mdi:progress-clock",
    ),
    "cycleSubPhase": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:progress-helper",
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
        entity_registry_enabled_default=False,  # Disabled: API reports Celsius values in F fields
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
    "runningTime": ElectroluxDevice(
        capability_info={"access": "read", "default": 0, "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timer",
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
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer-probe",
    ),
    "targetFoodProbeTemperatureF": ElectroluxDevice(
        capability_info={"access": "readwrite", "step": 1.0, "type": "temperature"},
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer-probe",
        entity_registry_enabled_default=False,  # Disabled: API reports Celsius values in F fields
    ),
    "targetTemperatureC": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "temperature"},
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "targetTemperatureF": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "temperature"},
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer",
        entity_registry_enabled_default=False,  # Disabled: API reports Celsius values in F fields
    ),
    "waterTankEmpty": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"STEAM_TANK_EMPTY": {}, "STEAM_TANK_FULL": {}},
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
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
    "networkInterface/linkQualityIndicator": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:wifi-strength-3",
    ),
    "networkInterface/otaState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:update",
    ),
}
