"""Defined catalog of entities for air conditioner type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory

from .model import ElectroluxDevice

CATALOG_AIR_CONDITIONER: dict[str, ElectroluxDevice] = {
    # Air conditioner specific controls
    "executeCommand": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
            "values": {
                "ON": {},
                "OFF": {},
                "START": {},
                "STOPRESET": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:power",
    ),
    # Temperature controls
    "targetTemperatureC": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 16,
            "max": 30,
            "step": 1,
            "unit": "°C",
        },
        device_class=None,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "targetTemperatureF": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 60,
            "max": 86,
            "step": 1,
            "unit": "°F",
        },
        device_class=None,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "ambientTemperatureC": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "unit": "°C",
        },
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "ambientTemperatureF": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "unit": "°F",
        },
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    # Operating modes
    "mode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUTO": {"icon": "mdi:autorenew"},
                "COOL": {"icon": "mdi:snowflake"},
                "HEAT": {"icon": "mdi:fire"},
                "DRY": {"icon": "mdi:water-percent"},
                "FAN": {"icon": "mdi:fan"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
    ),
    # Fan modes
    "fanMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUTO": {"icon": "mdi:fan-auto"},
                "LOW": {"icon": "mdi:fan-speed-1"},
                "MEDIUM": {"icon": "mdi:fan-speed-2"},
                "HIGH": {"icon": "mdi:fan-speed-3"},
                "QUIET": {"icon": "mdi:fan-chevron-down"},
                "TURBO": {"icon": "mdi:fan-plus"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan-speed-1",
    ),
    # Swing modes
    "swingMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "OFF": {},
                "VERTICAL": {},
                "HORIZONTAL": {},
                "BOTH": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:arrow-up-down",
    ),
    # Humidity control (if supported)
    "targetHumidity": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 30,
            "max": 70,
            "step": 5,
            "unit": "%",
        },
        device_class=None,
        unit="%",
        entity_category=None,
        entity_icon="mdi:water-percent",
    ),
    "ambientHumidity": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "unit": "%",
        },
        device_class=None,
        unit="%",
        entity_category=None,
        entity_icon="mdi:water-percent",
    ),
    # Power state
    "powerState": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:power",
    ),
    # Filter status
    "filterStatus": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
    ),
    # Door/window sensors
    "doorState": ElectroluxDevice(
        capability_info={"access": "read", "type": "boolean"},
        device_class=BinarySensorDeviceClass.DOOR,
        unit=None,
        entity_category=None,
        entity_icon="mdi:door",
    ),
    "windowState": ElectroluxDevice(
        capability_info={"access": "read", "type": "boolean"},
        device_class=BinarySensorDeviceClass.WINDOW,
        unit=None,
        entity_category=None,
        entity_icon="mdi:window-open",
    ),
    # Timer controls
    "startTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 1440,  # 24 hours in minutes
            "step": 15,
            "unit": "min",
        },
        device_class=None,
        unit="min",
        entity_category=None,
        entity_icon="mdi:timer",
    ),
    # Energy monitoring
    "powerConsumption": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "unit": "W",
        },
        device_class=SensorDeviceClass.POWER,
        unit="W",
        entity_category=None,
        entity_icon="mdi:flash",
    ),
    "energyConsumption": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "unit": "kWh",
        },
        device_class=SensorDeviceClass.ENERGY,
        unit="kWh",
        entity_category=None,
        entity_icon="mdi:lightning-bolt",
    ),
    # Additional operating modes and features
    "cleanAirMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:air-filter",
    ),
    "sleepMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:sleep",
    ),
    "batchSchedulerMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:calendar-clock",
    ),
    "verticalSwing": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:arrow-up-down",
    ),
    # Fan speed controls
    "fanSpeedSetting": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUTO": {},
                "HIGH": {},
                "LOW": {},
                "MIDDLE": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
    ),
    "fanSpeedState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "HIGH": {},
                "LOW": {},
                "MIDDLE": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
    ),
    # Filter maintenance
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
    ),
    "airFilterLifeTime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
    ),
    "hepaFilterLifeTime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        entity_registry_enabled_default=False,
    ),
    # Timer controls
    "stopTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 1440,
            "step": 15,
            "unit": "min",
        },
        device_class=None,
        unit="min",
        entity_category=None,
        entity_icon="mdi:timer-off",
    ),
    # Diagnostic sensors
    "applianceUiSwVersion": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:information",
        entity_registry_enabled_default=False,
    ),
    "applianceCategory": ElectroluxDevice(
        capability_info={
            "access": "constant",
            "default": 2,
            "type": "enum",
            "values": {"2": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:tag",
        entity_registry_enabled_default=False,
    ),
    # Network diagnostics
    "networkInterface/linkQualityIndicator": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "EXCELLENT": {},
                "GOOD": {},
                "POOR": {},
                "UNDEFINED": {},
                "VERY_GOOD": {},
                "VERY_POOR": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:wifi",
        entity_registry_enabled_default=False,
    ),
    "networkInterface/swVersion": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:chip",
        entity_registry_enabled_default=False,
    ),
    "networkInterface/otaState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "DESCRIPTION_AVAILABLE": {},
                "DESCRIPTION_DOWNLOADING": {},
                "DESCRIPTION_READY": {},
                "FW_DOWNLOADING": {},
                "FW_DOWNLOAD_START": {},
                "FW_SIGNATURE_CHECK": {},
                "FW_UPDATE_IN_PROGRESS": {},
                "IDLE": {},
                "READY_TO_UPDATE": {},
                "UPDATE_ABORT": {},
                "UPDATE_CHECK": {},
                "UPDATE_ERROR": {},
                "UPDATE_OK": {},
                "WAITINGFORAUTHORIZATION": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:update",
        entity_registry_enabled_default=False,
    ),
}
