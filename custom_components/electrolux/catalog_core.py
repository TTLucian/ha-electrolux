"""Defined catalog of entities for basic entities (common across all appliance types)."""

from homeassistant.helpers.entity import EntityCategory

from .catalog_air_conditioner import CATALOG_AIR_CONDITIONER
from .catalog_dishwasher import CATALOG_DISHWASHER
from .catalog_oven import CATALOG_OVEN
from .catalog_purifier import A9
from .catalog_refrigerator import CATALOG_REFRIGERATOR, EHE6899SA
from .catalog_utils import (
    create_config_entity,
    create_diagnostic_string_entity,
    create_hidden_entity,
)
from .catalog_washer import CATALOG_WASHER
from .catalog_washer_dryer import CATALOG_WASHER_DRYER
from .const import CAPABILITY_READ_STRING
from .model import ElectroluxDevice

# definitions of model explicit overrides. These will be used to
# create a new catalog with a merged definition of properties
CATALOG_MODEL: dict[str, dict[str, ElectroluxDevice]] = {
    "EHE6899SA": EHE6899SA,
    "A9": A9,
}

# Appliance type catalogs
CATALOG_BY_TYPE: dict[str, dict[str, ElectroluxDevice]] = {
    "OV": CATALOG_OVEN,  # Oven
    "RF": CATALOG_REFRIGERATOR,  # Refrigerator
    "WM": CATALOG_WASHER,  # Washing Machine
    "WD": CATALOG_WASHER_DRYER,  # Washer-Dryer
    "AC": CATALOG_AIR_CONDITIONER,  # Air Conditioner
    "DW": CATALOG_DISHWASHER,  # Dishwasher
}

CATALOG_BASE: dict[str, ElectroluxDevice] = {
    # Consolidated alert system - comprehensive sensor for all possible alert types across appliances
    "alerts": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "alert",
            "values": {
                # Washer/Washer-dryer alerts
                "CHECK_DOOR": {},
                "CHECK_DRAIN_FILTER": {},
                "CHECK_INLET_TAP": {},
                "CLEAN_FLUFF_DRAWER": {},
                "DETERGENT_OVERDOSING": {},
                "DOOR": {},
                "EMPTY_WATER_CONTAINER": {},
                "MACHINE_RESTART": {},
                "POWER_FAILURE": {},
                "STEAM_TANK_FULL": {},
                "TOP_UP_SALT": {},
                "UNBALANCED_LAUNDRY": {},
                "UNSTABLE_SUPPLY_VOLTAGE": {},
                "WATER_CONTAINER": {},
                "WATER_LEAK": {},
                # Air conditioner alerts
                "BUS_HIGH_VOLTAGE": {},
                "COMMUNICATION_FAULT": {},
                "DRAIN_PAN_FULL": {},
                "INDOOR_DEFROST_THERMISTOR_FAULT": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert",
        friendly_name="Alerts",
    ),
    "applianceState": create_hidden_entity(
        capability_info=CAPABILITY_READ_STRING,
        friendly_name="Appliance State",
    ),
    "networkInterface/linkQualityIndicator": create_diagnostic_string_entity(
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
        friendly_name="Link Quality",
        icon="mdi:wifi",
    ),
    "networkInterface/niuSwUpdateCurrentDescription": create_diagnostic_string_entity(
        capability_info=CAPABILITY_READ_STRING,
        friendly_name="Software Update Description",
        entity_registry_enabled_default=False,
    ),
    "networkInterface/otaState": create_diagnostic_string_entity(
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
                "UPDATE_ERROR": {},
                "UPDATE_OK": {},
                "WAITINGFORAUTHORIZATION": {},
            },
        },
        friendly_name="OTA State",
        icon="mdi:update",
    ),
    "networkInterface/startUpCommand": create_config_entity(
        capability_info={
            "access": "write",
            "type": "string",
            "values": {"UNINSTALL": {}},
        },
        friendly_name="Start Up Command",
        icon="mdi:restart",
    ),
    "networkInterface/swAncAndRevision": create_diagnostic_string_entity(
        capability_info=CAPABILITY_READ_STRING,
        friendly_name="Software Ancestor Revision",
        entity_registry_enabled_default=False,
    ),
    "networkInterface/swVersion": create_diagnostic_string_entity(
        capability_info=CAPABILITY_READ_STRING,
        friendly_name="Software Version",
    ),
    "endOfCycleSound": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"NO_SOUND": {}, "SHORT_SOUND": {}},
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:volume-high",
        friendly_name="End of Cycle Sound",
    ),
    "applianceMode": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "default": "NORMAL",
            "values": {
                "NORMAL": {},
                "DEMO": {},
                "SERVICE": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:cog",
        friendly_name="Appliance Mode",
    ),
    "userSelections/programUID": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:play-circle",
        friendly_name="Program UID",
    ),
    "connectivityState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "connected": {},
                "disconnected": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:lan-connect",
        friendly_name="Connectivity State",
    ),
}
