"""Defined catalog of entities for hood type devices (HD).

Values verified against a real AEG hood diagnostic (HD-942051563_00,
https://github.com/TTLucian/ha-electrolux/issues/211).

Platform resolution notes (api.py:get_entity_type):
- string readwrite with values and no min/max -> SELECT
- string readwrite with ON/OFF values -> SWITCH
- boolean readwrite -> SWITCH, boolean read -> BINARY_SENSOR
- number readwrite with min/max -> NUMBER, number read -> SENSOR
Reported-state-only keys (no advertised capability) still need
``capability_info`` defined here to be picked up by the catalog loop.
"""

from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import PERCENTAGE, EntityCategory, Platform, UnitOfTime

from ..model import ElectroluxDevice

CATALOG_HD: dict[str, ElectroluxDevice] = {
    # ── Fan control ────────────────────────────────────────────────────────────
    # Fan level (select)
    # Values verified against HD-942051563_00 (issue #211).
    # NOTE: targetDuration is only writable while the level is between
    # BREEZE and STEP_3 (per the capability's triggers) — see targetDuration.
    "hoodFanLevel": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "OFF": {"icon": "mdi:fan-off"},
                "BREEZE": {"icon": "mdi:weather-windy"},
                "STEP_1": {"icon": "mdi:fan-speed-1"},
                "STEP_2": {"icon": "mdi:fan-speed-2"},
                "STEP_3": {"icon": "mdi:fan-speed-3"},
                "BOOST": {"icon": "mdi:fan-chevron-up"},
                "BOOST_2": {"icon": "mdi:fan-chevron-double-up"},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
        friendly_name="Fan Level",
    ),
    # ── Lighting controls ──────────────────────────────────────────────────────
    # Light brightness — verified range 0-100 step 1 (HD-942051563_00)
    "lightIntensity": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 100,
            "step": 1,
        },
        device_class=None,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:brightness-6",
        friendly_name="Light Intensity",
    ),
    # Light colour temperature — a 0-100 percentage scale on this hood
    # (reported value: 17), NOT Kelvin. Verified HD-942051563_00 (issue #211).
    "lightColorTemperature": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 100,
            "step": 1,
        },
        device_class=None,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:temperature-kelvin",
        friendly_name="Light Colour Temperature",
    ),
    # ── Filter maintenance ─────────────────────────────────────────────────────
    # Charcoal filter service timer. Reported value 180000 — believed to be
    # minutes (3000 h). Unit is an educated guess; verify on live data.
    "hoodCharcFilterTimer": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=UnitOfTime.MINUTES,
        suggested_unit=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="Charcoal Filter Timer",
    ),
    # Grease filter service timer — same scale caveat as the charcoal timer.
    "hoodGreaseFilterTimer": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=UnitOfTime.MINUTES,
        suggested_unit=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="Grease Filter Timer",
    ),
    # TVOC filter service time — reported-state only (no advertised
    # capability); reported 918000, same scale caveat as the filter timers.
    "tvocFilterTime": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=UnitOfTime.MINUTES,
        suggested_unit=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="TVOC Filter Time",
    ),
    # Charcoal filter enable / disable (string ON/OFF -> switch)
    "hoodFilterCharcEnable": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"OFF": {}, "ON": {}},
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:air-filter",
        friendly_name="Charcoal Filter Enable",
    ),
    # Charcoal filter replace indication — boolean, readwrite (resettable).
    # boolean readwrite resolves to a SWITCH platform.
    "hoodFilterCharcIndication": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "boolean"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter-alert",
        friendly_name="Charcoal Filter Indication",
    ),
    # Grease filter replace indication — string FALSE/TRUE, readwrite
    # (resettable). Resolves to a SELECT (not ON/OFF, so not a switch).
    "hoodFilterGreaseIndication": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {"FALSE": {}, "TRUE": {}},
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter-alert",
        friendly_name="Grease Filter Indication",
    ),
    # ── Status sensors ─────────────────────────────────────────────────────────
    # Auto switch-off event — boolean on HD-942051563_00 (was wrongly modelled
    # as an active/inactive string). boolean read -> BINARY_SENSOR.
    "hoodAutoSwitchOffEvent": ElectroluxDevice(
        capability_info={"access": "read", "type": "boolean"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:timer-off-outline",
        friendly_name="Auto Switch-Off",
    ),
    # Human-centric lighting event state — reported-state only, string value
    # (e.g. "OFF"). Expose as a plain diagnostic sensor.
    "humanCentricLightEventState": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:lightbulb-auto",
        friendly_name="Human-Centric Light",
        entity_platform=Platform.SENSOR,
    ),
    # ── Appliance settings ─────────────────────────────────────────────────────
    # Sound volume — NOT advertised as a capability on HD-942051563_00; it only
    # appears in reported state (value 0). Expose read-only via the
    # reported-only fallback instead of a (failing) writable number.
    # NOTE: hoods that do advertise it use discrete values 1-4 (see SO).
    "soundVolume": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:volume-high",
        friendly_name="Sound Volume",
        reported_only_entity_platform=Platform.SENSOR,
        reported_only_device_class=None,
    ),
    # Timer / countdown duration. Verified range 0-36000 step 60 (seconds).
    # Only writable while hoodFanLevel is between BREEZE and STEP_3
    # (capability triggers on HD-942051563_00).
    "targetDuration": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 36000,
            "step": 60,
        },
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_category=None,
        entity_icon="mdi:timer-outline",
        friendly_name="Target Duration",
    ),
}
