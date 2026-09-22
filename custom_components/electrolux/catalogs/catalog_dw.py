"""Defined catalog of entities for dishwasher type devices."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import EntityCategory, Platform

from ..const import CAPABILITY_READ_STRING
from ..execute_command_states import DISHWASHER_EXECUTE_STATES
from ..model import ElectroluxDevice

CATALOG_DW: dict[str, ElectroluxDevice] = {
    # Door state
    "doorState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "CLOSED": {},
                "OPEN": {},
            },
        },
        device_class=BinarySensorDeviceClass.OPENING,
        unit=None,
        entity_category=None,
    ),
    # Appliance state
    "applianceState": ElectroluxDevice(
        capability_info=CAPABILITY_READ_STRING,
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:dishwasher",
        friendly_name="Appliance State",
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
        available_when_states=DISHWASHER_EXECUTE_STATES,
        # Multi-command capability (PAUSE/RESUME/START/STOPRESET, sometimes ON/OFF):
        # one button per command value, never a toggle switch. Belt-and-braces with
        # the exact-match check in api.get_entity_type() (issue #200).
        entity_platform=Platform.BUTTON,
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
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,  # Configuration entity, not cycle-dependent
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
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:lightbulb",
        reported_only_entity_platform=Platform.SENSOR,
        reported_only_device_class=SensorDeviceClass.ENUM,
    ),
    # Display on floor
    "displayOnFloor": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "OFF": {},
                "ON": {},
                "GREEN": {},  # GlassCare 700 and similar models
                "RED": {},  # Additional color option
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:projector-screen",
        reported_only_entity_platform=Platform.SENSOR,
        reported_only_device_class=SensorDeviceClass.ENUM,
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
        reported_only_entity_platform=Platform.BINARY_SENSOR,
        reported_only_device_class=None,
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
            "step": 1,
        },
        device_class=None,
        # This is a bounded score, not an energy measurement.  Keep the
        # numeric state and make the documented 0–7 scale visible in HA.
        unit="/ 7",
        entity_category=None,
        entity_icon="mdi:leaf",
        friendly_name="Energy Score",
    ),
    "userSelections/waterScore": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "min": 0,
            "max": 7,
            "step": 1,
        },
        device_class=None,
        unit="/ 7",
        entity_category=None,
        entity_icon="mdi:water-percent",
        friendly_name="Water Score",
    ),
    "userSelections/ecoScore": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "number",
            "min": 0,
            "max": 7,
            "step": 1,
        },
        device_class=None,
        unit="/ 7",
        entity_category=None,
        entity_icon="mdi:recycle",
        friendly_name="Eco Score",
    ),
    # Miscellaneous state
    "miscellaneousState/ecoMode": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "boolean",
        },
        device_class=None,
        entity_platform=Platform.BINARY_SENSOR,
        unit=None,
        entity_category=None,
        entity_icon="mdi:leaf",
        friendly_name="Eco Mode",
    ),
    # Appliance care and maintenance
    "applianceCareAndMaintenance0/maint1_occured": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "boolean",
            "values": {},
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        friendly_name="Maintenance Required",
        state_path="applianceCareAndMaintenance0/1/occured",
        entity_registry_enabled_default=False,
    ),
    "applianceCareAndMaintenance0/maint1_threshold": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "int",
            "values": {},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:counter",
        friendly_name="Maintenance Threshold",
        entity_registry_enabled_default=False,
        state_path="applianceCareAndMaintenance0/1/threshold",
    ),
    "applianceMode": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "DEMO": {},
                "DIAGNOSTIC": {},
                "NORMAL": {},
                "SERVICE": {},
            },
        },
        device_class=SensorDeviceClass.ENUM,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:cog",
        friendly_name="Appliance Mode",
        entity_registry_enabled_default=False,
    ),
    "miscellaneousState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "complex",
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:information",
        friendly_name="Miscellaneous State",
        entity_registry_enabled_default=False,
    ),
}


# Alert codes verified against the live capability schema of the AEG
# GI7210B2SN (PNC 911472038). Keep these as separate binary sensors while
# retaining the aggregate ``alerts`` sensor for backwards compatibility.
for _alert_code in ("DISH_ALARM_RINSE_AID_LOW", "DISH_ALARM_SALT_MISSING"):
    CATALOG_DW[f"alerts/{_alert_code}"] = ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "boolean",
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        unit=None,
        entity_category=None,
        entity_icon="mdi:alert-circle",
    )
