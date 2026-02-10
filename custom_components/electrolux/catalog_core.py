"""Defined catalog of entities for basic entities (common across all appliance types)."""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from .catalog_oven import CATALOG_OVEN
from .catalog_purifier import A9
from .catalog_refrigerator import CATALOG_REFRIGERATOR, EHE6899SA
from .catalog_washer import CATALOG_WASHER
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
    "CR": CATALOG_REFRIGERATOR,  # Refrigerator
    "WM": CATALOG_WASHER,  # Washing Machine
    # Add more appliance types as needed
}

CATALOG_BASE: dict[str, ElectroluxDevice] = {
    "alerts": ElectroluxDevice(
        capability_info={"access": "read", "type": "alert"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:alert",
    ),
    "applianceMode": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"DEMO": {}, "NORMAL": {}, "SERVICE": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:auto-mode",
        entity_registry_enabled_default=False,
    ),
    "applianceState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:state-machine",
        entity_registry_enabled_default=False,
    ),
    "applianceTotalWorkingTime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timelapse",
    ),
    "connectionState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:wifi",
    ),
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
    ),
    "networkInterface/niuSwUpdateCurrentDescription": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:update",
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
                "UPDATE_ERROR": {},
                "UPDATE_OK": {},
                "WAITINGFORAUTHORIZATION": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:update",
    ),
    "networkInterface/startUpCommand": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
            "values": {"UNINSTALL": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:restart",
        entity_registry_enabled_default=False,
    ),
    "networkInterface/swAncAndRevision": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:information",
        entity_registry_enabled_default=False,
    ),
    "networkInterface/swVersion": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:information",
    ),
}
