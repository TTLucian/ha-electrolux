"""Defined catalog of entities for dehumidifier type devices (DH, Husky)."""

from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import PERCENTAGE

from ..model import ElectroluxDevice

CATALOG_DH: dict[str, ElectroluxDevice] = {
    # Current humidity reading (read-only sensor)
    "sensorHumidity": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:water-percent",
        friendly_name="Humidity",
    ),
    # Target humidity setpoint (read-write number control)
    "targetHumidity": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 30,
            "max": 80,
            "step": 5,
        },
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:water-percent",
        friendly_name="Target Humidity",
    ),
    # Fan speed (select entity — values come from device capabilities at runtime)
    "fanSpeedSetting": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "LOW": {},
                "MEDIUM": {},
                "HIGH": {},
                "TURBO": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
        friendly_name="Fan Speed",
    ),
    # Operating mode (select entity — e.g. continuous, auto, laundry, etc.)
    "mode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUTO": {},
                "CONTINUOUS": {},
                "LAUNDRY": {},
                "DRY_CLOTHES": {},
                "SILENT": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:water-sync",
        friendly_name="Mode",
    ),
}
