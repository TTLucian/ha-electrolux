"""Defined catalog of entities for air conditioner type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)

from ..model import ElectroluxDevice

CATALOG_AC: dict[str, ElectroluxDevice] = {
    # Air conditioner specific controls
    # Note: executeCommand values vary by model
    # - Bogong/Telica/Panther: ON, OFF
    # - Other AC models may support START, STOPRESET
    # The API returns actual supported values at runtime
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
    ),
    # Temperature controls
    "targetTemperatureC": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "temperature",
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
            "type": "temperature",
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
        device_class=NumberDeviceClass.HUMIDITY,
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
        device_class=SensorDeviceClass.HUMIDITY,
        unit="%",
        entity_category=None,
        entity_icon="mdi:water-percent",
    ),
    # Filter status
    "filterStatus": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
    ),
    # Timer controls (seconds, 30-minute steps; 86400 = 24h)
    "startTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 86400,
            "step": 1800,
            "unit": "s",
        },
        device_class=None,
        unit=UnitOfTime.SECONDS,
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
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:air-filter",
    ),
    "sleepMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:sleep",
    ),
    "batchSchedulerMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:calendar-clock",
    ),
    "verticalSwing": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
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
                "QUIET": {},
                "LOW": {},
                "MIDDLE": {},
                "HIGH": {},
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
                "QUIET": {},
                "LOW": {},
                "MIDDLE": {},
                "HIGH": {},
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
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
    ),
    "hepaFilterLifeTime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        entity_registry_enabled_default=False,
    ),
    # Timer controls (seconds, 30-minute steps; 86400 = 24h)
    "stopTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 86400,
            "step": 1800,
            "unit": "s",
        },
        device_class=None,
        unit=UnitOfTime.SECONDS,
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
    # Feature availability indicators
    "hMEPN_ACAirFilterClean": ElectroluxDevice(
        capability_info={
            "access": "constant",
            "type": "int",
            "default": 1,
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        friendly_name="Air Filter Clean Required",
    ),
    "hMEPN_ACAlerts": ElectroluxDevice(
        capability_info={
            "access": "constant",
            "type": "int",
            "default": 1,
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        friendly_name="AC Alerts Supported",
    ),
    # Additional Bogong AC switches (readwrite ON/OFF)
    "turboFunction": ElectroluxDevice(
        capability_info={"access": "readwrite"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan-plus",
    ),
    "energySavingMode": ElectroluxDevice(
        capability_info={"access": "readwrite"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:leaf",
    ),
    "autoCleanTrigger": ElectroluxDevice(
        capability_info={"access": "readwrite"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:air-filter",
    ),
    "displayLight": ElectroluxDevice(
        capability_info={"access": "readwrite"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:lightbulb",
    ),
    "flapPositionAvoidUser": ElectroluxDevice(
        capability_info={"access": "readwrite"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:arrow-collapse-horizontal",
    ),
    "horizontalSwing": ElectroluxDevice(
        capability_info={"access": "readwrite"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:arrow-left-right",
    ),
    # Temperature unit selector
    "temperatureRepresentation": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "CELSIUS": {},
                "FAHRENHEIT": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    # Module firmware versions (diagnostic, disabled by default)
    "VmNo_NIU": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:chip",
        entity_registry_enabled_default=False,
    ),
    "VmNo_MCU": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:chip",
        entity_registry_enabled_default=False,
    ),
    # Scheduler indicators (binary sensors, ON/OFF)
    "schedulerSession": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"ON": {}, "OFF": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:calendar-clock",
    ),
    "schedulerMode": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"ON": {}, "OFF": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:calendar-clock",
    ),
    # Reported-state-only entries (not in capabilities, but present in `reported`)
    "compressorState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"on": {}, "off": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:heat-pump",
    ),
    "totalRuntime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timer",
        entity_registry_enabled_default=False,
    ),
    "compressorCoolingRuntime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:snowflake-thermometer",
        entity_registry_enabled_default=False,
    ),
    "compressorHeatingRuntime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:fire",
        entity_registry_enabled_default=False,
    ),
    "mainUnitTemp": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:thermometer",
        entity_registry_enabled_default=False,
    ),
    "logE": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert-circle",
        entity_registry_enabled_default=False,
    ),
    "logW": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert",
        entity_registry_enabled_default=False,
    ),
    "demandResponseAu": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:transmission-tower",
        entity_registry_enabled_default=False,
    ),
    # --- Telica (Electrolux 700 multifunctional AC / air purifier combo) ---
    # Air quality sensors
    "pm25": ElectroluxDevice(
        capability_info={"access": "read", "type": "int"},
        device_class=SensorDeviceClass.PM25,
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        entity_category=None,
        entity_icon="mdi:air-filter",
        friendly_name="PM2.5",
    ),
    "pm10": ElectroluxDevice(
        capability_info={"access": "read", "type": "int"},
        device_class=SensorDeviceClass.PM10,
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        entity_category=None,
        entity_icon="mdi:air-filter",
        friendly_name="PM10",
    ),
    "sensorHumidity": ElectroluxDevice(
        capability_info={"access": "read", "type": "int"},
        device_class=SensorDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:water-percent",
    ),
    # Read-only current operating mode (mirrors the writable `mode` field)
    "modeState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    # Sound volume: 0 = silent, 1 = on — binary, modeled as a switch
    "soundVolume": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "boolean"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:volume-high",
    ),
    # Filter maintenance — main air filter
    "filterRuntime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        entity_registry_enabled_default=False,
    ),
    "filterReset": ElectroluxDevice(
        capability_info={"access": "write", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:air-filter",
    ),
    # HEPA filter
    "hepaFilterState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "GOOD": {},
                "BUY": {},
                "CHANGE": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        entity_registry_enabled_default=False,
        friendly_name="HEPA Filter State",
    ),
    "hepaFilterInsertedState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"ON": {}, "OFF": {}},
        },
        device_class=BinarySensorDeviceClass.PRESENCE,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="HEPA Filter Inserted",
    ),
    "hepaFilterReset": ElectroluxDevice(
        capability_info={"access": "write", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:air-filter",
    ),
    # Air quality index (Telica-specific, state-only — not in capabilities)
    "airQualityLevel": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        entity_registry_enabled_default=False,
    ),
}
