"""Defined catalog of entities for steam oven type devices (SO).

Steam ovens have their oven control capabilities nested under the "upperOven" container,
unlike regular ovens where capabilities are at the root level. This catalog provides
the correct entity_source paths for steam oven capabilities.
"""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from .model import ElectroluxDevice

# Steam oven specific catalog with upperOven/ prefixed entities
CATALOG_STEAM_OVEN: dict[str, ElectroluxDevice] = {
    # Upper oven cavity entities (nested under upperOven container)
    "upperOven/applianceState": ElectroluxDevice(
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
    "upperOven/cavityLight": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:lightbulb",
    ),
    "upperOven/displayFoodProbeTemperatureC": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "upperOven/displayFoodProbeTemperatureF": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer",
        entity_registry_enabled_default=False,  # Disabled: API reports Celsius values in F fields
    ),
    "upperOven/displayTemperatureC": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "upperOven/displayTemperatureF": ElectroluxDevice(
        capability_info={"access": "read", "type": "temperature"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer",
        entity_registry_enabled_default=False,  # Disabled: API reports Celsius values in F fields
    ),
    "upperOven/doorState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"CLOSED": {}, "OPEN": {}},
        },
        device_class=BinarySensorDeviceClass.OPENING,
        unit=None,
        entity_category=None,
    ),
    "upperOven/executeCommand": ElectroluxDevice(
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
    "upperOven/fastHeatUpFeature": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"DISABLED": {}, "ECO": {}, "ENABLED": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:fire-circle",
    ),
    "upperOven/foodProbeInsertionState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"INSERTED": {}, "NOT_INSERTED": {}},
        },
        device_class=BinarySensorDeviceClass.PLUG,
        unit=None,
        entity_category=None,
    ),
    "upperOven/preheatComplete": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "OFF": {},
                "PRE_HEAT_COMPLETED": {},
                "PRE_HEAT_RUNNING": {},
                "RE_HEAT_COMPLETED": {},
                "RE_HEAT_RUNNING": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:progress-check",
    ),
    "upperOven/processPhase": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "FAST_HEAT_UP": {},
                "HEAT_AND_HOLD": {},
                "NONE": {},
                "NORMAL_HEATING": {},
                "TIME_EXTENSION": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:state-machine",
    ),
    "upperOven/program": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:chef-hat",
    ),
    "upperOven/runningTime": ElectroluxDevice(
        capability_info={"access": "read", "default": 0, "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timer",
    ),
    "upperOven/startTime": ElectroluxDevice(
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
    "upperOven/targetDuration": ElectroluxDevice(
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
    "upperOven/targetDurationEndAction": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "END_ACTION_JUST_SHOW_TEMP": {},
                "END_ACTION_NONE": {},
                "END_ACTION_SILENT_NOTIFICATION": {},
                "END_ACTION_SOUND_ALARM": {},
                "END_ACTION_SOUND_ALARM_STOP_COOKING": {},
                "END_ACTION_SOUND_ALARM_WARM_HOLD": {},
                "END_ACTION_START_COOKING": {},
                "END_ACTION_STOP_COOKING": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:timer-stop",
    ),
    "upperOven/targetFoodProbeTemperatureC": ElectroluxDevice(
        capability_info={"access": "readwrite", "step": 1.0, "type": "temperature"},
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer-probe",
    ),
    "upperOven/targetFoodProbeTemperatureF": ElectroluxDevice(
        capability_info={"access": "readwrite", "step": 1.0, "type": "temperature"},
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer-probe",
    ),
    "upperOven/targetFoodProbeTemperatureEndAction": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "END_ACTION_JUST_SHOW_TEMP": {},
                "END_ACTION_NONE": {},
                "END_ACTION_SILENT_NOTIFICATION": {},
                "END_ACTION_SOUND_ALARM": {},
                "END_ACTION_SOUND_ALARM_STOP_COOKING": {},
                "END_ACTION_SOUND_ALARM_WARM_HOLD": {},
                "END_ACTION_START_COOKING": {},
                "END_ACTION_STOP_COOKING": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:thermometer-alert",
    ),
    "upperOven/targetTemperatureC": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "temperature"},
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "upperOven/targetTemperatureF": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "temperature"},
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        entity_category=None,
        entity_icon="mdi:thermometer",
    ),
    "upperOven/timeToEnd": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=None,
        entity_icon="mdi:timer-sand",
    ),
    "upperOven/waterTankLevel": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "ALMOST_EMPTY": {},
                "ALMOST_FULL": {},
                "EMPTY": {},
                "FULL": {},
                "OK": {},
                "UNKNOWN": {},
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=None,
        entity_icon="mdi:cup-water",
    ),
    "upperOven/waterTrayInsertionState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"INSERTED": {}, "NOT_INSERTED": {}},
        },
        device_class=BinarySensorDeviceClass.PLUG,
        unit=None,
        entity_category=None,
    ),
    "upperOven/reminderTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "max": 86340,
            "min": 0,
            "step": 60,
            "type": "number",
        },
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=None,
        entity_icon="mdi:alarm",
    ),
    # Root-level steam oven configuration entities
    "waterHardness": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "HARD": {},
                "MEDIUM": {},
                "SOFT": {},
                "STEP_4": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:water-opacity",
    ),
    "descalingReminderState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "boolean",
            "values": {
                "ACTIVE_BLOCKING": {},
                "ACTIVE_NOT_BLOCKING": {},
                "NOT_ACTIVE": {},
            },
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        unit=None,
        entity_category=None,
    ),
    "cleaningReminder": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "boolean",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        unit=None,
        entity_category=None,
    ),
    "childLock": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
            "values": {"DISABLED": {}, "ENABLED": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:lock",
    ),
    "displayLight": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "DISPLAY_LIGHT_1": {},
                "DISPLAY_LIGHT_2": {},
                "DISPLAY_LIGHT_3": {},
                "DISPLAY_LIGHT_4": {},
                "DISPLAY_LIGHT_5": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:brightness-6",
    ),
    "soundVolume": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "values": {"1": {}, "2": {}, "3": {}, "4": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:volume-high",
    ),
    "keySoundTone": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"BEEP": {}, "CLICK": {}, "NONE": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:music-note",
    ),
    "clockStyle": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"ANALOG": {}, "DIGITAL": {}, "NOT_SELECTED": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:clock-outline",
    ),
    "language": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "BULGARIAN": {},
                "CROATIAN": {},
                "CZECH": {},
                "DANISH": {},
                "DUTCH": {},
                "ENGLISH": {},
                "ESTONIAN": {},
                "FINNISH": {},
                "FRENCH": {},
                "GERMAN": {},
                "GREEK": {},
                "HUNGARIAN": {},
                "ITALIAN": {},
                "LATVIAN": {},
                "LITHUANIAN": {},
                "NORWEGIAN": {},
                "POLISH": {},
                "PORTUGUESE": {},
                "ROMANIAN": {},
                "RUSSIAN": {},
                "SLOVAK": {},
                "SLOVENIAN": {},
                "SPANISH": {},
                "SWEDISH": {},
                "TURKISH": {},
                "UKRANIAN": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:translate",
    ),
    "localTimeAutomaticMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"AUTOMATIC": {}, "MANUAL": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:clock-check",
    ),
    # Network diagnostics
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
