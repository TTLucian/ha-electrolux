"""Defined catalog of entities for microwave type devices."""

from homeassistant.components.sensor import SensorDeviceClass

from .model import ElectroluxDevice

# ============================================================================
# CATALOG_MICROWAVE - Microwave Appliance Entities
# ============================================================================
# This catalog is in PREPARATION for full microwave support.
# Currently contains only basic entities. Full implementation pending
# JSON data from users with microwave appliances.
# ============================================================================

CATALOG_MICROWAVE: dict[str, ElectroluxDevice] = {
    # ========================================================================
    # STATUS & STATE SENSORS
    # ========================================================================
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
    ),
    # ========================================================================
    # POWER & ENERGY SENSORS
    # ========================================================================
    "targetMicrowavePower": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.POWER,
        unit="W",
        entity_category=None,
        entity_icon="mdi:microwave",
    ),
    # ========================================================================
    # TIME SENSORS
    # ========================================================================
    "timeToEnd": ElectroluxDevice(
        capability_info={"access": "read", "type": "int"},
        device_class=SensorDeviceClass.TIMESTAMP,
        unit=None,
        entity_category=None,
        entity_icon="mdi:timer-sand",
    ),
}

# ============================================================================
# TODO: PENDING FULL IMPLEMENTATION
# ============================================================================
# When microwave JSON data is available, add support for:
# - Power level controls (number entities)
# - Cooking modes (select entities)
# - Timer controls
# - Quick start buttons
# - Defrost settings
# - Child lock
# - Any microwave-specific features
# ============================================================================
