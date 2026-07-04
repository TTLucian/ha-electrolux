"""Defined catalog of entities for dehumidifier type devices (DH, Husky).

Verified against real diagnostics from DH-950133061_00 (Frigidaire
FGAC5044W1, SRAC firmware v1.9.1_srac) — see issue #106.

capability_info mirrors the device-reported capabilities so these entities
are also created from reported state when the capabilities API call fails
(the catalog fallback loop in models.setup). Live API values always
override catalog values/min/max/step when capabilities ARE available.
"""

from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import PERCENTAGE, EntityCategory, Platform, UnitOfTime

from ..model import ElectroluxDevice

CATALOG_DH: dict[str, ElectroluxDevice] = {
    # Power control — ON/OFF (write-only pair, surfaced as optimistic switch)
    "executeCommand": ElectroluxDevice(
        capability_info={
            "access": "write",
            "type": "string",
            "values": {
                "ON": {},
                "OFF": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:power",
        friendly_name="Power",
    ),
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
    # Device reports 35–85 % in 5 % steps; only adjustable in DRY mode
    # (a capability trigger disables it in the other modes).
    "targetHumidity": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 35,
            "max": 85,
            "step": 5,
        },
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        entity_category=None,
        entity_icon="mdi:water-percent",
        friendly_name="Target Humidity",
    ),
    # Fan speed (select entity). Values verified from DH-950133061.
    # A capability trigger makes this read-only while mode is AUTO or QUIET;
    # the API rejects writes in those modes.
    "fanSpeedSetting": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "LOW": {},
                "MIDDLE": {},
                "HIGH": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
        friendly_name="Fan Speed",
        entity_platform=Platform.SELECT,
    ),
    # Actual fan speed reported by the appliance (read-only sensor)
    "fanSpeedState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "LOW": {},
                "MIDDLE": {},
                "HIGH": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:fan",
        friendly_name="Fan Speed State",
    ),
    # Operating mode (select entity). Values verified from DH-950133061.
    # OFF is advertised disabled — it is reported as the current mode while
    # the unit is powered down but is not selectable (power off goes through
    # executeCommand); select.py shows it as a transient read-only label.
    "mode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUTO": {},
                "CONTINUOUS": {},
                "DRY": {},
                "QUIET": {},
                "OFF": {"disabled": True},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:water-sync",
        friendly_name="Mode",
        entity_platform=Platform.SELECT,
    ),
    # Ionizer / air purification (read-write ON/OFF switch)
    "cleanAirMode": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "ON": {},
                "OFF": {},
            },
        },
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=None,
        entity_icon="mdi:air-filter",
        friendly_name="Clean Air Mode",
    ),
    # Display brightness (select entity). A capability trigger makes this
    # read-only while mode is CONTINUOUS or QUIET.
    "displayLight": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "DISPLAY_LIGHT_0": {},
                "DISPLAY_LIGHT_1": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:lightbulb",
        friendly_name="Display Light",
        entity_platform=Platform.SELECT,
    ),
    # Filter maintenance status (read-only diagnostic sensor)
    "filterState": ElectroluxDevice(
        capability_info={
            "access": "read",
            "type": "string",
            "values": {
                "BUY": {},
                "CHANGE": {},
                "CLEAN": {},
                "GOOD": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="Filter State",
    ),
    # Water bucket fill level (read-only sensor; unit not reported by the
    # API — raw number, 0 when empty). Pairs with the BUCKET_FULL alert.
    "waterBucketLevel": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:bucket-outline",
        friendly_name="Water Bucket Level",
    ),
    # Timer controls (seconds, 30-minute steps; 86400 = 24h).
    # The appliance reports -1 (INVALID_OR_NOT_SET_TIME) when no timer is set.
    "startTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 86400,
            "step": 1800,
            "unit": "s",
        },
        device_class=None,
        unit=UnitOfTime.SECONDS,
        entity_category=None,
        entity_icon="mdi:timer",
    ),
    "stopTime": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 86400,
            "step": 1800,
            "unit": "s",
        },
        device_class=None,
        unit=UnitOfTime.SECONDS,
        entity_category=None,
        entity_icon="mdi:timer-off",
    ),
    # Network diagnostics (read-only, disabled by default)
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
        entity_registry_enabled_default=False,
    ),
    "networkInterface/swVersion": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:chip",
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
                "UPDATE_CHECK": {},
                "UPDATE_ERROR": {},
                "UPDATE_OK": {},
                "WAITINGFORAUTHORIZATION": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:update",
        entity_registry_enabled_default=False,
    ),
}
