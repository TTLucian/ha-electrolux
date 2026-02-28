"""Defined catalog of entities for purifier type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    Platform,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.helpers.entity import EntityCategory

from .model import ElectroluxDevice

A9 = {
    "Temp": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        friendly_name="Temperature",
    ),
    "Humidity": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        entity_category=None,
        friendly_name="Humidity",
    ),
    "PM1": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.PM1,
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        entity_category=None,
        friendly_name="PM1",
    ),
    "PM2_5": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.PM25,
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        entity_category=None,
        friendly_name="PM2.5",
    ),
    "PM10": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.PM10,
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        entity_category=None,
        friendly_name="PM10",
    ),
    "TVOC": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        unit=CONCENTRATION_PARTS_PER_BILLION,
        entity_category=None,
        friendly_name="TVOC",
    ),
    "ECO2": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.CO2,
        unit=CONCENTRATION_PARTS_PER_MILLION,
        entity_category=None,
        friendly_name="eCO2",
    ),
    "DoorOpen": ElectroluxDevice(
        capability_info={"access": "read", "type": "boolean"},
        device_class=BinarySensorDeviceClass.OPENING,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        friendly_name="Door Open",
    ),
    "FilterType": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        value_mapping={
            48: "BREEZE Complete air filter",
            49: "CLEAN Ultrafine particle filter",
            51: "CARE Ultimate protect filter",
            64: "Breeze 360 filter",
            65: "Clean 360 Ultrafine particle filter",
            66: "Protect 360 filter",
            67: "Breathe 360 filter",
            68: "Fresh 360 filter",
            96: "Breeze 360 filter",
            99: "Breeze 360 filter",
            100: "Fresh 360 filter",
            192: "FRESH Odour protect filter",
            0: "Filter",
        },
    ),
    "FilterLife": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:air-filter",
        friendly_name="Filter Life",
    ),
    # Air purifier controls
    # Note: These definitions represent the superset of capabilities across different models.
    # Actual values are determined by appliance API responses:
    # - A9 (PUREA9): Fanspeed 1-9, Workmode: Manual/Auto/PowerOff (no Quiet)
    # - Muju (UltimateHome 500): Fanspeed 1-5, Workmode: Manual/Auto/Quiet/PowerOff
    "Fanspeed": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 1,
            "max": 9,  # A9 max, Muju uses max=5 (overridden by API)
            "step": 1,
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
        friendly_name="Fan Speed",
    ),
    "Workmode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "Manual": {"icon": "mdi:hand-back-right"},
                "Auto": {"icon": "mdi:refresh-auto"},
                "Quiet": {"icon": "mdi:volume-off"},  # Muju only
                "PowerOff": {"icon": "mdi:power-off"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:cog",
        friendly_name="Work Mode",
    ),
    # Air Purifier Fan Entity - combines Workmode and Fanspeed into unified fan control
    # This creates a fan entity that provides on/off, speed percentage, and preset modes
    # The fan entity dynamically adapts to each model's actual capabilities from the API:
    # - Speed range: A9 (1-9) vs Muju (1-5) automatically detected
    # - Preset modes: Extracted from available Workmode values (excluding PowerOff)
    # Keep the Workmode select entity above for users who prefer separate controls
    "Workmode/fan": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "Manual": {"icon": "mdi:hand-back-right"},
                "Auto": {"icon": "mdi:refresh-auto"},
                "Quiet": {"icon": "mdi:volume-off"},  # Muju only
                "PowerOff": {"icon": "mdi:power-off"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
        friendly_name="Air Purifier",
        entity_platform=Platform.FAN,
    ),
    "UILight": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
            "default": True,
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:lightbulb",
        friendly_name="UI Light",
    ),
    "SafetyLock": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
            "default": False,
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:lock",
        friendly_name="Safety Lock",
    ),
    "Ionizer": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:atom",
        friendly_name="Ionizer",
    ),
    #  UltimateHome 500 air purifier specific entities
    "FilterLife_1": ElectroluxDevice(
        capability_info={"access": "read", "type": "int", "min": 0, "max": 100},
        device_class=None,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:air-filter",
        friendly_name="Filter Life",
    ),
    "FilterType_1": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        value_mapping={
            1: "Standard filter",
            48: "BREEZE Complete air filter",
            49: "CLEAN Ultrafine particle filter",
            51: "CARE Ultimate protect filter",
            64: "Breeze 360 filter",
            65: "Clean 360 Ultrafine particle filter",
            66: "Protect 360 filter",
            67: "Breathe 360 filter",
            68: "Fresh 360 filter",
            96: "Breeze 360 filter",
            99: "Breeze 360 filter",
            100: "Fresh 360 filter",
            192: "FRESH Odour protect filter",
            0: "Filter",
        },
        friendly_name="Filter Type",
    ),
    "PM2_5_approximate": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "min": 0,
            "max": 65535,
            "step": 1,
        },
        device_class=SensorDeviceClass.PM25,
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        entity_category=None,
        friendly_name="PM2.5 (Approximate)",
    ),
    "UVState": ElectroluxDevice(
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
        entity_icon="mdi:sun-wireless",
        friendly_name="UV Light",
    ),
    "UVRuntime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timer",
        friendly_name="UV Runtime",
    ),
    "SchedulingState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "not set": {},
                "ongoing": {},
                "done": {},
                "aborted": {},
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:calendar-clock",
        friendly_name="Scheduling State",
    ),
    # Error sensors
    "ErrImpellerStuck": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "not active": {},
                "active": {},
                "was active": {},
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:fan-alert",
        friendly_name="Error: Impeller Stuck",
    ),
    "ErrPmNotResp": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "not active": {},
                "active": {},
                "was active": {},
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert-circle",
        friendly_name="Error: PM Sensor Not Responding",
    ),
    "ErrCommSensorDisplayBrd": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "not active": {},
                "active": {},
                "was active": {},
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert-circle",
        friendly_name="Error: Display Board Communication",
    ),
    "ErrCommSensorUIBrd": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "not active": {},
                "active": {},
                "was active": {},
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert-circle",
        friendly_name="Error: UI Board Communication",
    ),
    "SignalStrength": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "EXCELLENT": {},
                "GOOD": {},
                "FAIR": {},
                "WEAK": {},
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:wifi-strength-3",
        friendly_name="Signal Strength",
    ),
}
