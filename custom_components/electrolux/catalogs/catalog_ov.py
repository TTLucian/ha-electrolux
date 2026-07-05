"""Defined catalog of entities for oven type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime

from ..const import BINARY_SENSOR, CAPABILITY_READ_STRING
from ..execute_command_states import OVEN_EXECUTE_STATES
from ..model import ElectroluxDevice

CATALOG_OV: dict[str, ElectroluxDevice] = {
    "alerts": ElectroluxDevice(
        # Oven-specific alert codes - overrides base catalog which has refrigerator/AC alerts.
        # Actual alert values come from the API capability at runtime; we just provide metadata.
        capability_info={
            "access": "read",
            "type": "alert",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert",
        friendly_name="Alerts",
    ),
    "applianceState": ElectroluxDevice(
        capability_info=CAPABILITY_READ_STRING,
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:stove",
        friendly_name="Appliance State",
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
    "displayFoodProbeTemperature": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer-probe",
    ),
    "displayFoodProbeTemperatureC": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer-probe",
    ),
    "displayFoodProbeTemperatureF": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer-probe",
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
        available_when_states=OVEN_EXECUTE_STATES,
    ),
    "doorState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"CLOSED": {}, "OPEN": {}},
        },
        device_class=BinarySensorDeviceClass.OPENING,
        unit=None,
        entity_category=None,
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
    ),
    "foodProbeSupported": ElectroluxDevice(
        capability_info={
            "access": "constant",
            "type": "enum",
            "values": {"SUPPORTED": {}, "NOT_SUPPORTED": {}},
        },
        entity_platform=BINARY_SENSOR,
        entity_icon="mdi:thermometer-probe",
        friendly_name="Food Probe Support",
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
        friendly_name="Water Tray",
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
        friendly_name="Water Tank Empty",
    ),
    "processPhase": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:state-machine",
    ),
    "program": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUGRATIN": {},
                "BOTTOM": {},
                "BREAD_BAKING": {},
                "CLEAN_DESCALING": {},
                "CLEAN_DRYING": {},
                "CONVENTIONAL_COOKING": {},
                "DEFROST": {},
                "DOUGH_PROVING": {},
                "DRYING": {},
                "FROZEN_FOOD": {},
                "FULL_STEAM": {},
                "GRILL": {},
                "GRILL_FAN": {},
                "HUMIDITY_HIGH": {},
                "HUMIDITY_LOW": {},
                "HUMIDITY_MEDIUM": {},
                "KEEP_WARM": {},
                "MOIST_FAN_BAKING": {},
                "PIZZA": {},
                "PLATE_WARMING": {},
                "PRESERVING": {},
                "REGENERATE": {},
                "SLOW_COOK": {},
                "SOUS_VIDE": {},
                "STEAMIFY": {},
                "STEAM_CLEAN_DESCALE": {},
                "STEAM_CLEAN_DRY": {},
                "STEAM_CLEAN_INTENSE": {},
                "STEAM_CLEAN_LIGHT": {},
                "STEAM_CLEAN_RINSING": {},
                "STEAM_CLEAN_TANK_EMPTY": {},
                "STEAM_REGENERATING": {},
                "TRUE_FAN": {},
                "YOGHURT": {},
            },
        },
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
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
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
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
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
