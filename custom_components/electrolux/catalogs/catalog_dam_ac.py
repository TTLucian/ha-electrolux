"""Defined catalog of entities for DAM air conditioner type devices (DAM_AC).

DAM_AC appliances use a different API structure from legacy AC appliances.
All control capabilities are nested under the "airConditioner" sub-object:
  - airConditioner/targetTemperature  (integer °C, range in device capabilities)
  - airConditioner/fanMode            (string: AUTO / LOW / MEDIUM / HIGH / …)
  - airConditioner/mode               (string: cool / heat / fan / dry / …)
  - airConditioner/executeCommand     (string: on / off)
  - airConditioner/applianceState     (string: running / off / …)

The ambient temperature is at the root level as "temperature" (not nested).

SDK reference: `dam_ac_config.py` — DAM_AC_CONFIG
"""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature

from ..model import ElectroluxDevice

CATALOG_DAM_AC: dict[str, ElectroluxDevice] = {
    # ── Root-level sensors ─────────────────────────────────────────────────────
    # Ambient temperature (root, not nested under airConditioner)
    "temperature": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
        friendly_name="Ambient Temperature",
    ),
    # ── airConditioner sub-object controls ─────────────────────────────────────
    # Appliance state (nested)
    "airConditioner/applianceState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "running": {},
                "off": {},
                "standby": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:state-machine",
        friendly_name="State",
    ),
    # On/off command (nested under airConditioner)
    "airConditioner/executeCommand": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
            "values": {
                "on": {},
                "off": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:power",
        friendly_name="Power",
    ),
    # Target temperature — integer °C, range read from device capabilities
    "airConditioner/targetTemperature": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 16,
            "max": 30,
            "step": 1,
        },
        device_class=None,
        unit=UnitOfTemperature.CELSIUS,
        entity_category=None,
        entity_icon="mdi:thermometer",
        friendly_name="Target Temperature",
    ),
    # Operating mode
    "airConditioner/mode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "cool": {"icon": "mdi:snowflake"},
                "heat": {"icon": "mdi:fire"},
                "fan": {"icon": "mdi:fan"},
                "dry": {"icon": "mdi:water-percent"},
                "auto": {"icon": "mdi:autorenew"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
        friendly_name="Mode",
    ),
    # Fan speed mode
    "airConditioner/fanMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "auto": {"icon": "mdi:fan-auto"},
                "low": {"icon": "mdi:fan-speed-1"},
                "medium": {"icon": "mdi:fan-speed-2"},
                "high": {"icon": "mdi:fan-speed-3"},
                "quiet": {"icon": "mdi:fan-chevron-down"},
                "turbo": {"icon": "mdi:fan-plus"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan-speed-1",
        friendly_name="Fan Mode",
    ),
}
