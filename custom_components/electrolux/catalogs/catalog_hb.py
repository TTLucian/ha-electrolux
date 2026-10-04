"""Defined catalog of entities for hob type devices (HB).

The HB hob exposes two groups of capabilities:
1. Top-level appliance controls (applianceMode, childLock, keySoundTone, windowNotification)
2. hobHood sub-object — fan speed and state for the linked hood (hobHood/*)
   Accessed via the slash-path notation used throughout the integration.
"""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import EntityCategory

from ..model import ElectroluxDevice

CATALOG_HB: dict[str, ElectroluxDevice] = {
    # ── Top-level hob controls ─────────────────────────────────────────────────
    # Operating mode (e.g. cooking, sabbath, …)
    "applianceMode": ElectroluxDevice(
        capability_info={"access": "readwrite", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:stove",
        friendly_name="Appliance Mode",
    ),
    # Child lock
    "childLock": ElectroluxDevice(
        capability_info={"access": "readwrite"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:lock-outline",
        friendly_name="Child Lock",
    ),
    # Key-press sound toggle
    "keySoundTone": ElectroluxDevice(
        capability_info={"access": "readwrite"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:volume-high",
        friendly_name="Key Sound",
    ),
    # Window detection notification
    "windowNotification": ElectroluxDevice(
        capability_info={"access": "readwrite"},
        device_class=SwitchDeviceClass.SWITCH,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon="mdi:window-open",
        friendly_name="Window Notification",
    ),
    # ── hobHood — linked hood controls (nested under the hobHood sub-object) ──
    # Fan speed level sent to the connected hood
    # NOTE: Values are read dynamically from device capabilities at runtime.
    # Placeholder values below will be replaced by whatever the device reports.
    # Unverified until a real diagnostic is provided.
    "hobHood/hobToHoodFanSpeed": ElectroluxDevice(
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
        friendly_name="Hood Fan Speed",
    ),
    # Hood linkage activation state
    # NOTE: Values are read dynamically from device capabilities at runtime.
    # Placeholder values below will be replaced by whatever the device reports.
    # Unverified until a real diagnostic is provided.
    "hobHood/hobToHoodState": ElectroluxDevice(
        capability_info={
            "access": "readwrite",
            "type": "string",
            "values": {
                "off": {},
                "on": {},
                "auto": {},
            },
        },
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon="mdi:link-variant",
        friendly_name="Hood State",
    ),
    # ── hood filter indicator: a status, not a control ─────────────────────────
    # The hood reports that its filter needs running a cleaning/characterisation
    # cycle. It is read/write in the cloud's capability map, which made it a
    # switch - a control that invites a press and silently does nothing. Same
    # reasoning as #232's Auto Door Opener: expose what it reports, do not
    # pretend the user can change it.
    #
    # The catalog's "access": "read" is not what does this. models.py lets the API
    # capability win that merge and the API says readwrite; the device_class is
    # what actually demotes the platform.
    "hobHood/hoodFilterCharcIndication": ElectroluxDevice(
        capability_info={"access": "read", "type": "boolean"},
        device_class=BinarySensorDeviceClass.RUNNING,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:air-filter",
        friendly_name="Hood Filter Needs Cleaning",
    ),
}
