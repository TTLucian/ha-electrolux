"""Defined catalog of entities for refrigerator type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from .model import ElectroluxDevice

CATALOG_REFRIGERATOR: dict[str, ElectroluxDevice] = {
    "freezer/alerts": ElectroluxDevice(
        capability_info={"access": "read", "type": "alert"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert",
    ),
    "freezer/applianceState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fridge-variant",
    ),
    "freezer/doorState": ElectroluxDevice(
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
    "freezer/fastMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fridge-variant",
    ),
    "freezer/fastModeTimeToEnd": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:fridge-variant",
    ),
    "freezer/targetTemperatureC": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": -18.0,
            "max": -13.0,
            "min": -24.0,
            "step": 1.0,
            "type": "temperature",
        },
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "fridge/alerts": ElectroluxDevice(
        capability_info={"access": "read", "type": "alert"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert",
    ),
    "fridge/applianceState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fridge-variant",
    ),
    "fridge/doorState": ElectroluxDevice(
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
    "fridge/fastMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fridge-variant",
    ),
    "fridge/fastModeTimeToEnd": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:fridge-variant",
    ),
    "fridge/targetTemperatureC": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": 4.0,
            "max": 8.0,
            "min": 2.0,
            "step": 1.0,
            "type": "temperature",
        },
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
}

EHE6899SA = {
    "uiLockMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:lock",
        friendly_name="Child Lock Internal",
    ),
    "ui2LockMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:lock",
        friendly_name="Child Lock External",
    ),
}
