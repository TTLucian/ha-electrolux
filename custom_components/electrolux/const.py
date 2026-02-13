"""The Electrolux constants."""

from typing import Literal

from homeassistant.const import Platform
from homeassistant.helpers.entity import EntityCategory

# Base component constants
NAME = "Electrolux"
DOMAIN = "electrolux"

# Platforms
BINARY_SENSOR = Platform.BINARY_SENSOR
BUTTON = Platform.BUTTON
CLIMATE = Platform.CLIMATE
NUMBER = Platform.NUMBER
SELECT = Platform.SELECT
SENSOR = Platform.SENSOR
SWITCH = Platform.SWITCH
TEXT = Platform.TEXT
PLATFORMS = [BINARY_SENSOR, BUTTON, CLIMATE, NUMBER, SELECT, SENSOR, SWITCH, TEXT]

# Configuration and options
CONF_NOTIFICATION_DEFAULT = "notifications"
CONF_NOTIFICATION_DIAG = "notifications_diagnostic"
CONF_NOTIFICATION_WARNING = "notifications_warning"
CONF_API_KEY = "api_key"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"

# Token validity
ACCESS_TOKEN_VALIDITY_SECONDS = 43200  # 12 hours

# Defaults
DEFAULT_WEBSOCKET_RENEWAL_DELAY = (
    7200  # 2 hours - balance between connection stability and rate limiting
)

# these are attributes that appear in the state file but not in the capabilities.
# defining them here and in the catalog will allow these devices to be added dynamically
STATIC_ATTRIBUTES = [
    "connectivityState",  # Appliance connectivity status
    "networkInterface/linkQualityIndicator",
    "applianceMode",
    "applianceState",  # Appliance operational state
]

# Icon mappings for default executeCommands
icon_mapping = {
    "OFF": "mdi:power-off",
    "ON": "mdi:power-on",
    "START": "mdi:play",
    "STOPRESET": "mdi:stop",
    "PAUSE": "mdi:pause",
    "RESUME": "mdi:play-pause",
}

# List of attributes to ignore and that won't be added as entities (regex format)
ATTRIBUTES_BLACKLIST: list[str] = [
    "^fCMiscellaneous.+",
    "fcOptisenseLoadWeight.*",
    "applianceCareAndMaintenance.*",
    "applianceMainBoardSwVersion",
    "coolingValveState",
    "networkInterface",
    "temperatureRepresentation",
    "^fPPN_OV.+",
]

ATTRIBUTES_WHITELIST: list[str] = [".*waterUsage", ".*tankAReserve", ".*tankBReserve"]

# Rules to simplify the naming of entities
RENAME_RULES: list[str] = [
    r"^userSelections\/[^_]+_",
    r"^userSelections\/",
    r"^fCMiscellaneousState\/[^_]+_",
    r"^fCMiscellaneousState\/",
]

# List of entity names that need to be updated to 0 manually when they are close to 0
TIME_ENTITIES_TO_UPDATE = ["timeToEnd"]

# Auto-dosing constants
AUTODOSE_OFF = "AUTODOSE_OFF"
AUTODOSE_DETERGENT_DUAL_OFF = "AUTODOSE_DETERGENT_DUAL_OFF"
AUTODOSE_DETERGENT_DUAL_ON = "AUTODOSE_DETERGENT_DUAL_ON"
AUTODOSE_LINK_OFF = "AUTODOSE_LINK_OFF"
AUTODOSE_LINK_ON = "AUTODOSE_LINK_ON"
AUTODOSE_SOFTENER_OFF = "AUTODOSE_SOFTENER_OFF"
AUTODOSE_SOFTENER_ON = "AUTODOSE_SOFTENER_ON"

# Common capability patterns
CAPABILITY_READ_STRING = {"access": "read", "type": "string"}
CAPABILITY_READWRITE_STRING = {"access": "readwrite", "type": "string"}
CAPABILITY_READ_NUMBER = {"access": "read", "type": "number"}
CAPABILITY_READWRITE_NUMBER = {"access": "readwrite", "type": "number"}
CAPABILITY_READ_BOOLEAN = {"access": "read", "type": "boolean"}
CAPABILITY_READWRITE_BOOLEAN = {"access": "readwrite", "type": "boolean"}
CAPABILITY_READ_TEMPERATURE = {"access": "read", "type": "temperature"}
CAPABILITY_READWRITE_TEMPERATURE = {"access": "readwrite", "type": "temperature"}
CAPABILITY_READ_ALERT = {"access": "read", "type": "alert"}

# Entity category constants
ENTITY_CATEGORY_DIAGNOSTIC = EntityCategory.DIAGNOSTIC
ENTITY_CATEGORY_CONFIG = EntityCategory.CONFIG

# Icon constants
ICON_ALERT = "mdi:alert"
ICON_ALERT_CIRCLE = "mdi:alert-circle"
ICON_STATE_MACHINE = "mdi:state-machine"
ICON_INFORMATION = "mdi:information-outline"
ICON_FLASK = "mdi:flask"
ICON_UPDATE = "mdi:update"
ICON_WIFI = "mdi:wifi"
ICON_LOCK = "mdi:lock"
ICON_NUMERIC = "mdi:numeric"
ICON_LIGHTBULB = "mdi:lightbulb"
ICON_SNOWFLAKE_THERMOMETER = "mdi:snowflake-thermometer"
ICON_THERMOMETER = "mdi:thermometer"
ICON_PLAY_PAUSE = "mdi:play-pause"
ICON_FRIDGE_VARIANT = "mdi:fridge-variant"
ICON_THERMOMETER_PROBE = "mdi:thermometer-probe"
ICON_CHEF_HAT = "mdi:chef-hat"
ICON_REMOTE = "mdi:remote"
ICON_TIMELAPSE = "mdi:timelapse"

# Type definitions
AlertType = Literal[
    "CHECK_DOOR",
    "CHECK_DRAIN_FILTER",
    "CHECK_INLET_TAP",
    "CLEAN_FLUFF_DRAWER",
    "DETERGENT_OVERDOSING",
    "DOOR",
    "EMPTY_WATER_CONTAINER",
    "MACHINE_RESTART",
    "POWER_FAILURE",
    "STEAM_TANK_FULL",
    "TOP_UP_SALT",
    "UNBALANCED_LAUNDRY",
    "UNSTABLE_SUPPLY_VOLTAGE",
    "WATER_CONTAINER",
    "WATER_LEAK",
    "BUS_HIGH_VOLTAGE",
    "COMMUNICATION_FAULT",
    "DRAIN_PAN_FULL",
    "INDOOR_DEFROST_THERMISTOR_FAULT",
]

CapabilityType = Literal["string", "number", "boolean", "alert", "temperature"]
AccessType = Literal["read", "readwrite", "write", "constant"]
ApplianceType = Literal["OV", "CR", "WM", "WD", "AC", "DW"]
