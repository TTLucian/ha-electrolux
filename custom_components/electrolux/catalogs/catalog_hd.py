"""Defined catalog of entities for hood type devices (HD)."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTime,
)

from ..model import ElectroluxDevice

CATALOG_HD: dict[str, ElectroluxDevice] = {
    # ── Fan control ────────────────────────────────────────────────────────────
    # Fan level (select)
    # NOTE: Values are read dynamically from device capabilities at runtime.
    # Placeholder values below will be replaced by whatever the device reports.
    # Unverified until a real diagnostic is provided.
    "hoodFanLevel": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "off": {"icon": "mdi:fan-off"},
                "low": {"icon": "mdi:fan-speed-1"},
                "medium": {"icon": "mdi:fan-speed-2"},
                "high": {"icon": "mdi:fan-speed-3"},
                "intensive": {"icon": "mdi:fan-plus"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
        friendly_name="Fan Level",
    ),
    # ── Lighting controls ──────────────────────────────────────────────────────
    # Light brightness — range read from device capabilities at runtime
    # NOTE: min/max/step values below are unverified placeholders.
    "lightIntensity": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 100,
            "step": 1,
        },
        device_class=NumberDeviceClass.POWER_FACTOR,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:brightness-6",
        friendly_name="Light Intensity",
    ),
    # Light colour temperature — range read from device capabilities at runtime
    # NOTE: min/max/step values below are unverified placeholders.
    "lightColorTemperature": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 2700,
            "max": 6500,
            "step": 100,
        },
        device_class=NumberDeviceClass.TEMPERATURE,
        unit="K",
        entity_category=None,
        entity_icon="mdi:temperature-kelvin",
        friendly_name="Light Colour Temperature",
    ),
    # ── Filter maintenance ─────────────────────────────────────────────────────
    # Charcoal filter service timer (hours)
    "hoodCharcFilterTimer": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="Charcoal Filter Timer",
    ),
    # Grease filter service timer (hours)
    "hoodGreaseFilterTimer": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="Grease Filter Timer",
    ),
    # TVOC filter service remaining time (hours)
    "tvocFilterTime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="TVOC Filter Time",
    ),
    # Charcoal filter enable / disable
    "hoodFilterCharcEnable": ElectroluxDevice(
        capability_info={"access": "readwrite"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:air-filter",
        friendly_name="Charcoal Filter Enable",
    ),
    # ── Status sensors ─────────────────────────────────────────────────────────
    # Drawer open/closed sensor
    "drawerStatus": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"CLOSED": {}, "OPEN": {}},
        },
        device_class=BinarySensorDeviceClass.OPENING,
        unit=None,
        entity_category=None,
        entity_icon="mdi:tray-arrow-down",
        friendly_name="Drawer",
    ),
    # Human-centric lighting event (active/inactive)
    "humanCentricLightEventState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=BinarySensorDeviceClass.RUNNING,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:lightbulb-auto",
        friendly_name="Human-Centric Light",
    ),
    # Auto switch-off event
    "hoodAutoSwitchOffEvent": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {"active": {}, "inactive": {}},
        },
        device_class=BinarySensorDeviceClass.RUNNING,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timer-off-outline",
        friendly_name="Auto Switch-Off",
    ),
    # ── Appliance settings ─────────────────────────────────────────────────────
    # Operating mode (e.g. normal, delayed start, boost)
    "applianceMode": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:tune",
        friendly_name="Appliance Mode",
    ),
    # Sound volume
    "soundVolume": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 100,
            "step": 10,
        },
        device_class=None,
        unit=PERCENTAGE,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:volume-high",
        friendly_name="Sound Volume",
    ),
    # Timer / countdown duration (SDK: TARGET_DURATION → "targetDuration")
    "targetDuration": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "number"},
        device_class=None,
        unit=UnitOfTime.SECONDS,
        entity_category=None,
        entity_icon="mdi:timer-outline",
        friendly_name="Target Duration",
    ),
}
