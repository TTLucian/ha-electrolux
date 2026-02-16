"""Defined catalog of entities for refrigerator type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number import NumberDeviceClass
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
        device_class=SensorDeviceClass.TIMESTAMP,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timer-outline",
    ),
    "freezer/targetTemperatureC": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": -18.0,
            "max": -13.0,
            "min": -23.0,
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
        device_class=SensorDeviceClass.TIMESTAMP,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timer-outline",
    ),
    "fridge/targetTemperatureC": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "default": 4.0,
            "max": 7.0,
            "min": 1.0,
            "step": 1.0,
            "type": "temperature",
        },
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    # Main appliance controls
    "sabbathMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:star-david",
        friendly_name="Sabbath Mode",
    ),
    "vacationHolidayMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:beach",
        friendly_name="Vacation Mode",
    ),
    # Sensors
    "sensorHumidity": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.HUMIDITY,
        unit="%",
        entity_category=None,
        entity_icon="mdi:water-percent",
        friendly_name="Humidity",
    ),
    # Filter monitoring
    "waterFilterState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"GOOD": {}, "CLEAN": {}, "CHANGE": {}, "BUY": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:water",
        friendly_name="Water Filter Status",
    ),
    "waterFilterStateReset": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:water",
        friendly_name="Reset Water Filter",
    ),
    "waterFilterLifeTime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:water",
        friendly_name="Water Filter Life Time",
    ),
    "waterFilterFlow": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit="L",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:water",
        friendly_name="Water Filter Flow",
    ),
    "airFilterState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"GOOD": {}, "CLEAN": {}, "CHANGE": {}, "BUY": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:air-filter",
        friendly_name="Air Filter Status",
    ),
    "airFilterStateReset": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:air-filter",
        friendly_name="Reset Air Filter",
    ),
    "airFilterLifeTime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="Air Filter Life Time",
    ),
    # Additional sensors and controls
    "coolingValveState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:valve",
        friendly_name="Cooling Valve State",
    ),
    "defrostRoutineState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:snowflake-melt",
        friendly_name="Defrost Routine State",
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
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=None,
        entity_icon="mdi:clock",
        friendly_name="Reminder Time",
    ),
    # Extra cavity (wine cellar, etc.)
    "extraCavity/applianceState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"OFF": {}, "RUNNING": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fridge-variant",
        friendly_name="Extra Cavity State",
    ),
    "extraCavity/doorState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"CLOSED": {}, "OPEN": {}},
        },
        device_class=BinarySensorDeviceClass.DOOR,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fridge-variant",
        friendly_name="Extra Cavity Door",
    ),
    "extraCavity/fanState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:fan",
        friendly_name="Extra Cavity Fan State",
    ),
    "extraCavity/cloneTargetTemperatureMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "values": {"OFF": {}, "FREEZER": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:thermometer",
        friendly_name="Extra Cavity Clone Mode",
    ),
    "extraCavity/targetTemperatureC": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "temperature",
            "values": {"-2.0": {}, "0.0": {}, "3.0": {}, "7.0": {}},
        },
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
        friendly_name="Extra Cavity Temperature",
    ),
    "extraCavity/temperatureAdjustingState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "values": {"DOWN": {}, "NONE": {}, "UP": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:thermometer",
        friendly_name="Extra Cavity Adjusting",
    ),
    # Ice maker
    "iceMaker/applianceState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"OFF": {}, "RUNNING": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:snowflake",
        friendly_name="Ice Maker State",
    ),
    "iceMaker/executeCommand": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:power",
        friendly_name="Ice Maker Control",
    ),
    "iceMaker/defrostTemperatureC": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:snowflake-thermometer",
        friendly_name="Ice Maker Defrost Temperature",
    ),
    "iceMaker/evaporatorFanState": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:fan",
        friendly_name="Ice Maker Fan State",
    ),
    "iceMaker/iceDispenserState": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:cup-water",
        friendly_name="Ice Dispenser State",
    ),
    "iceMaker/iceTrayWaterFillSetting": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "values": {
                "VERY_LOW_PRESSURE": {},
                "LOW_PRESSURE": {},
                "NORMAL_PRESSURE": {},
                "VERY_HIGH_PRESSURE": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:tray",
        friendly_name="Ice Tray Fill Setting",
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
