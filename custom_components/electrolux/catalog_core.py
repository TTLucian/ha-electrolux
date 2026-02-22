"""Defined catalog of entities for basic entities (common across all appliance types)."""

from functools import lru_cache

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from .catalog_utils import (
    create_config_entity,
    create_diagnostic_string_entity,
)
from .const import CAPABILITY_READ_STRING
from .model import ElectroluxDevice


@lru_cache(maxsize=None)
def _get_catalog_air_conditioner():
    """Lazy load air conditioner catalog."""
    from .catalog_air_conditioner import CATALOG_AIR_CONDITIONER

    return CATALOG_AIR_CONDITIONER


@lru_cache(maxsize=None)
def _get_catalog_dishwasher():
    """Lazy load dishwasher catalog."""
    from .catalog_dishwasher import CATALOG_DISHWASHER

    return CATALOG_DISHWASHER


@lru_cache(maxsize=None)
def _get_catalog_oven():
    """Lazy load oven catalog."""
    from .catalog_oven import CATALOG_OVEN

    return CATALOG_OVEN


@lru_cache(maxsize=None)
def _get_catalog_purifier():
    """Lazy load purifier catalog."""
    from .catalog_purifier import A9

    return A9


@lru_cache(maxsize=None)
def _get_catalog_refrigerator():
    """Lazy load refrigerator catalog."""
    from .catalog_refrigerator import CATALOG_REFRIGERATOR, EHE6899SA

    return CATALOG_REFRIGERATOR, EHE6899SA


@lru_cache(maxsize=None)
def _get_catalog_washer():
    """Lazy load washer catalog."""
    from .catalog_washer import CATALOG_WASHER

    return CATALOG_WASHER


@lru_cache(maxsize=None)
def _get_catalog_washer_dryer():
    """Lazy load washer-dryer catalog."""
    from .catalog_washer_dryer import CATALOG_WASHER_DRYER

    return CATALOG_WASHER_DRYER


@lru_cache(maxsize=None)
def _get_catalog_dryer():
    """Lazy load dryer catalog."""
    from .catalog_dryer import CATALOG_DRYER

    return CATALOG_DRYER


@lru_cache(maxsize=None)
def _get_catalog_microwave():
    """Lazy load microwave catalog."""
    from .catalog_microwave import CATALOG_MICROWAVE

    return CATALOG_MICROWAVE


# definitions of model explicit overrides. These will be used to
# create a new catalog with a merged definition of properties
@lru_cache(maxsize=1)
def _get_catalog_model():
    """Lazy load model catalog.

    This function creates a mapping of model-specific entity overrides.
    Each model can define custom entity configurations that override the
    standard appliance-type definitions.

    Currently supports:
    - EHE6899SA: Refrigerator model with specific overrides
    - A9: Air purifier model with specific overrides

    Returns:
        dict: Mapping of model names to their override configurations
    """
    _, EHE6899SA = _get_catalog_refrigerator()
    A9 = _get_catalog_purifier()
    return {
        "EHE6899SA": EHE6899SA,
        "A9": A9,
    }


# Appliance type catalogs - lazy loaded
@lru_cache(maxsize=1)
def _get_catalog_by_type():
    """Lazy load appliance type catalogs.

    This function provides appliance-type specific entity catalogs that extend
    the base catalog with features unique to each appliance type.

    Supported appliance types:
    - OV: Oven - includes temperature, program, and timing controls
    - RF: Refrigerator - includes temperature zones and alerts
    - WM: Washing Machine - includes cycle programs and options
    - WD: Washer-Dryer - combines washing and drying functionality
    - TD: Tumble Dryer - includes drying programs and controls
    - AC: Air Conditioner - includes climate control and air quality
    - DW: Dishwasher - includes wash programs and options
    - MW: Microwave - includes power levels and cooking programs (in preparation)

    Returns:
        dict: Mapping of appliance type codes to their entity catalogs
    """
    return {
        "OV": _get_catalog_oven(),  # Oven
        "RF": _get_catalog_refrigerator()[0],  # Refrigerator
        "WM": _get_catalog_washer(),  # Washing Machine
        "WD": _get_catalog_washer_dryer(),  # Washer-Dryer
        "TD": _get_catalog_dryer(),  # Tumble Dryer
        "AC": _get_catalog_air_conditioner(),  # Air Conditioner
        "DW": _get_catalog_dishwasher(),  # Dishwasher
        "MW": _get_catalog_microwave(),  # Microwave (in preparation)
    }


# Lazy-loaded properties for backward compatibility
def _get_catalog_model_lazy():
    """Get model catalog (lazy loaded)."""
    return _get_catalog_model()


def _get_catalog_by_type_lazy():
    """Get appliance type catalogs (lazy loaded)."""
    return _get_catalog_by_type()


def _get_catalog_base_lazy():
    """Get base catalog (lazy loaded)."""
    return _get_catalog_base()


# For backward compatibility, expose lazy-loaded catalogs
class _LazyCatalog:
    """Lazy loading wrapper for catalogs.

    This class provides backward-compatible access to lazily-loaded catalog data.
    It implements a callable interface that defers expensive catalog loading until
    first access, then caches the result for subsequent calls.

    The lazy loading pattern reduces memory usage and import time by avoiding
    immediate loading of large catalog dictionaries that may not be needed.

    Attributes:
        _loader_func: The function that loads the catalog data when called
        _cache: Internal cache storing loaded catalog data
    """

    def __init__(self, loader_func):
        self._loader_func = loader_func
        self._cache = None

    def __call__(self):
        if self._cache is None:
            self._cache = self._loader_func()
        return self._cache


@lru_cache(maxsize=1)
def _get_catalog_base():
    """Lazy load base catalog.

    This function defines the core set of entities that are common across all
    Electrolux appliance types. These include:

    - Basic connectivity and status entities
    - Alert and diagnostic information
    - Network interface details
    - Common control entities like end-of-cycle sounds
    - Manual sync capabilities

    The base catalog provides the foundation that appliance-type specific
    catalogs build upon, ensuring consistent entity availability across
    all appliance types.

    Returns:
        dict: Base entity catalog applicable to all appliances
    """
    return {
        "alerts": ElectroluxDevice(
            capability_info={
                "access": "read",
                "type": "string",
                "values": {
                    # Refrigerator alerts
                    "DOOR_OPEN": {},
                    "HIGH_TEMP": {},
                    "LOW_TEMP": {},
                    "POWER_FAILURE": {},
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
        "applianceState": ElectroluxDevice(
            capability_info=CAPABILITY_READ_STRING,
            device_class=None,
            unit=None,
            entity_category=None,
            entity_icon="mdi:state-machine",
            entity_registry_enabled_default=True,
            friendly_name="Appliance State",
        ),
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
            entity_category=EntityCategory.CONFIG,
            entity_icon="mdi:thermometer-lines",
            friendly_name="Temperature Unit",
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
        "networkInterface/command": ElectroluxDevice(
            capability_info={
                "access": "write",
                "type": "string",
                "values": {
                    "APPLIANCE_AUTHORIZE": {},
                    "START": {},
                    "USER_AUTHORIZE": {},
                    "USER_NOT_AUTHORIZE": {},
                },
            },
            device_class=None,
            unit=None,
            entity_category=EntityCategory.CONFIG,
            entity_icon="mdi:console-network",
            entity_registry_enabled_default=False,
            friendly_name="Network Command",
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
        "manualSync": ElectroluxDevice(
            capability_info={
                "access": "write",
                "type": "string",
                "values": {
                    "SYNC": {},
                },
            },
            device_class=None,  # Will be handled as button in entity creation
            unit=None,
            entity_category=None,
            entity_icon="mdi:sync",
            friendly_name="Manual Sync",
        ),
        # Common diagnostic entities
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
        "cpv": ElectroluxDevice(
            capability_info={"access": "read", "type": "string"},
            device_class=None,
            unit=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_icon="mdi:numeric",
            entity_registry_enabled_default=False,
        ),
        # Common control and status entities
        "remoteControl": ElectroluxDevice(
            capability_info={
                "access": "read",
                "type": "string",
                "values": {
                    "DISABLED": {},
                    "ENABLED": {},
                    "NOT_SAFETY_RELEVANT_ENABLED": {},
                    "TEMPORARY_LOCKED": {},
                },
            },
            device_class=None,
            unit=None,
            entity_category=None,
            entity_icon="mdi:remote",
        ),
        "uiLockMode": ElectroluxDevice(
            capability_info={
                "access": "readwrite",
                "type": "boolean",
            },
            device_class=SwitchDeviceClass.SWITCH,
            unit=None,
            entity_category=None,
            entity_icon="mdi:lock",
            friendly_name="Child Lock",
        ),
        # Common statistics and counters
        "totalCycleCounter": ElectroluxDevice(
            capability_info={"access": "read", "type": "number"},
            device_class=None,
            unit=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_icon="mdi:counter",
        ),
        "applianceTotalWorkingTime": ElectroluxDevice(
            capability_info={"access": "read", "type": "number"},
            device_class=SensorDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_icon="mdi:timelapse",
        ),
        # Common time-to-end countdown (used by ovens, washers, dryers, dishwashers, AC)
        "timeToEnd": ElectroluxDevice(
            capability_info={"access": "read", "type": "number"},
            device_class=SensorDeviceClass.DURATION,
            unit=UnitOfTime.SECONDS,
            entity_category=None,
            entity_icon="mdi:timer-outline",
            friendly_name="Time to End",
        ),
    }


CATALOG_MODEL = _LazyCatalog(_get_catalog_model)
CATALOG_BY_TYPE = _LazyCatalog(_get_catalog_by_type)
CATALOG_BASE = _LazyCatalog(_get_catalog_base)
