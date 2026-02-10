"""Defined catalog of entities for washing machine type devices."""

from homeassistant.components.button import ButtonDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from .model import ElectroluxDevice

CATALOG_WASHER: dict[str, ElectroluxDevice] = {
    "defaultExtraRinse": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": 0,
            "max": 3,
            "min": 0,
            "step": 1,
            "type": "number",
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:washing-machine",
    ),
    "executeCommand": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
            "values": {"START": {}, "STOPRESET": {}},
        },
        device_class=ButtonDeviceClass.RESTART,
        unit=None,
        entity_category=None,
        entity_icon="mdi:play-pause",
    ),
    "preWashPhase": ElectroluxDevice(
        capability_info={"access": "read", "type": "boolean"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:washing-machine",
    ),
    "reminderTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": 1200,
            "max": 2700,
            "min": 1200,
            "step": 60,
            "type": "number",
        },
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timelapse",
        entity_registry_enabled_default=False,
    ),
    "totalWashingTime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        entity_category=None,
        entity_icon="mdi:timelapse",
    ),
    "uiLockMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:lock",
    ),
    "ui2LockMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:lock",
    ),
    "userSelections/analogSpinSpeed": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": 1200,
            "max": 1600,
            "min": 400,
            "step": 100,
            "type": "number",
        },
        device_class=None,
        unit="RPM",
        entity_category=None,
        entity_icon="mdi:rotate-right",
    ),
    "userSelections/analogTemperature": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": 40,
            "max": 90,
            "min": 0,
            "step": 10,
            "type": "number",
        },
        device_class=NumberDeviceClass.TEMPERATURE,
        unit="°C",
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "userSelections/programUID": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:tune",
    ),
    "userSelections/steamValue": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": 0,
            "max": 3,
            "min": 0,
            "step": 1,
            "type": "number",
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:weather-partly-cloudy",
    ),
    "vacationHolidayMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:airplane",
    ),
}
