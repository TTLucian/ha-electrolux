"""Defined catalog of entities for air conditioner type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory

from .model import ElectroluxDevice

CATALOG_AIR_CONDITIONER: dict[str, ElectroluxDevice] = {
    "alerts": ElectroluxDevice(
        capability_info={"access": "read", "type": "alert"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert",
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
        capability_info={
            "access": "read",
            "type": "string",
        },
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
    # Air conditioner specific controls
    "executeCommand": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
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
    "timeToEnd": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "unit": "min",
        },
        device_class=None,
        unit="min",
        entity_category=None,
        entity_icon="mdi:timer-off",
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
}
