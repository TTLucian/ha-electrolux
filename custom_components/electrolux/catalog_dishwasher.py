"""Defined catalog of entities for dishwasher type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.helpers.entity import EntityCategory

from .model import ElectroluxDevice

CATALOG_DISHWASHER: dict[str, ElectroluxDevice] = {
    # Door state
    "doorState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "CLOSED": {},
                "OPEN": {},
                "OPENING": {},
                "CLOSING": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:door-closed",
    ),
    # Appliance state
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
        entity_icon="mdi:dishwasher",
    ),
    # Execute command buttons
    "executeCommand": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
            "values": {
                "PAUSE": {},
                "RESUME": {},
                "START": {},
                "STOPRESET": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:gesture-tap-button",
    ),
    # Cycle phase
    "cyclePhase": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "ADO_DRYING": {},
                "COLDRINSE": {},
                "DRYING": {},
                "EXTRARINSE": {},
                "HOTRINSE": {},
                "MAINWASH": {},
                "PREWASH": {},
                "UNAVAILABLE": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:rotate-right",
    ),
    # Rinse aid level
    "rinseAidLevel": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "default": 4,
            "min": 0,
            "max": 6,
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:cup-water",
    ),
    # Water hardness
    "waterHardness": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "STEP_0": {},
                "STEP_1": {},
                "STEP_2": {},
                "STEP_3": {},
                "STEP_4": {},
                "STEP_5": {},
                "STEP_6": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:water-percent",
    ),
    # Display light
    "displayLight": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "DISPLAY_LIGHT_0": {},
                "DISPLAY_LIGHT_1": {},
                "DISPLAY_LIGHT_2": {},
                "DISPLAY_LIGHT_3": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:lightbulb",
    ),
    # Display on floor
    "displayOnFloor": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "OFF": {},
                "ON": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:projector-screen",
    ),
    # Key tone
    "keyTone": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:volume-high",
    ),
    # End of cycle sound
    "endOfCycleSound": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "NO_SOUND": {},
                "SHORT_SOUND": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:volume-high",
    ),
    # Start time
    "startTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": -1,
            "max": 86400,
            "step": 60,
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:clock-start",
    ),
    # Pre-select last
    "preSelectLast": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:refresh",
    ),
    # User selections - program options
    "userSelections/programUID": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUTO": {},
                "ECO": {},
                "INTENSIVE": {},
                "QUICK": {},
                "GLASS_CARE": {},
                "SANITIZE": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:play-circle",
    ),
    # User selections - boolean options
    "userSelections/extraPowerOption": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:flash",
        friendly_name="Extra Power",
    ),
    "userSelections/extraSilentOption": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:volume-off",
        friendly_name="Extra Silent",
    ),
    "userSelections/glassCareOption": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:glass-wine",
        friendly_name="Glass Care",
    ),
    "userSelections/sprayZoneOption": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:spray",
        friendly_name="Spray Zone",
    ),
    "userSelections/SprayZoneOption": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:spray",
        friendly_name="Spray Zone (Legacy)",
        entity_registry_enabled_default=False,
    ),
    "userSelections/autoDoorOpener": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:door-open",
        friendly_name="Auto Door Opener",
    ),
    "userSelections/sanitizeOption": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:shield-check",
        friendly_name="Sanitize",
    ),
    "userSelections/oneRackOption": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:silverware-variant",
        friendly_name="One Rack",
    ),
    "userSelections/zoneCleanOption": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:target",
        friendly_name="Zone Clean",
    ),
    "userSelections/xtraDryOption": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:hair-dryer",
        friendly_name="Extra Dry",
    ),
    # User selections - scores (read-only)
    "userSelections/energyScore": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "min": 0,
            "max": 7,
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:leaf",
        friendly_name="Energy Score",
        entity_registry_enabled_default=False,
    ),
    "userSelections/waterScore": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "min": 0,
            "max": 7,
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:water-percent",
        friendly_name="Water Score",
        entity_registry_enabled_default=False,
    ),
    "userSelections/ecoScore": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "min": 0,
            "max": 7,
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:recycle",
        friendly_name="Eco Score",
        entity_registry_enabled_default=False,
    ),
    # Miscellaneous state
    "miscellaneousState/ecoMode": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "boolean",
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:leaf",
        friendly_name="Eco Mode",
    ),
    # Appliance care and maintenance
    "applianceCareAndMaintenance0/1/occured": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "boolean",
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:wrench",
        friendly_name="Maintenance Required",
    ),
    "applianceCareAndMaintenance0/1/threshold": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:counter",
        friendly_name="Maintenance Threshold",
        entity_registry_enabled_default=False,
    ),
}
