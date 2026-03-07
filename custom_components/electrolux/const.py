"""The Electrolux constants."""

from typing import Literal

from homeassistant.const import EntityCategory, Platform

# Base component constants
NAME = "Electrolux"
DOMAIN = "electrolux"

# Platforms
BINARY_SENSOR = Platform.BINARY_SENSOR
BUTTON = Platform.BUTTON
CLIMATE = Platform.CLIMATE
FAN = Platform.FAN
NUMBER = Platform.NUMBER
SELECT = Platform.SELECT
SENSOR = Platform.SENSOR
SWITCH = Platform.SWITCH
TEXT = Platform.TEXT
PLATFORMS = [BINARY_SENSOR, BUTTON, CLIMATE, FAN, NUMBER, SELECT, SENSOR, SWITCH, TEXT]

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
# NOTE: networkInterface/linkQualityIndicator is now discovered via API capabilities (no longer needs to be here)
STATIC_ATTRIBUTES = [
    "connectivityState",  # Appliance connectivity status
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
# NOTE: networkInterface parent is NOT blocked here - safe children (linkQualityIndicator, swVersion, otaState)
# are allowed through catalog, while dangerous ones (command, startUpCommand) are blocked by DANGEROUS_ENTITIES_BLACKLIST
ATTRIBUTES_BLACKLIST: list[str] = [
    "^fCMiscellaneous.+",  # Block fCMiscellaneous from API; whitelist allows specific children (waterUsage, tankAReserve, tankBReserve)
    "fcOptisenseLoadWeight.*",  # Catalog-only with special error code filtering in sensor.py
    "applianceMainBoardSwVersion",  # Catalog-only diagnostic info (disabled by default)
    "coolingValveState",  # Catalog-only exposure for refrigerators
    "^applianceCareAndMaintenance",  # Internal maintenance counters/thresholds - cryptic names, no user value
]

ATTRIBUTES_WHITELIST: list[str] = [".*waterUsage", ".*tankAReserve", ".*tankBReserve"]

# Dangerous entities that should NEVER be created (even if in catalog or API)
# These control low-level system functions that can permanently damage appliance functionality
# Pattern matching is case-sensitive and uses regex format
# Patterns match the entity attribute path (e.g., "networkInterface/command")
# Note: Removing $ anchor to catch any potential child paths or variations
DANGEROUS_ENTITIES_BLACKLIST: list[str] = [
    r"^networkInterface/startUpCommand",  # Contains UNINSTALL - can factory reset network module
    r"^networkInterface/command",  # Contains APPLIANCE_AUTHORIZE, USER_*AUTHORIZE - can unpair appliance
]

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

# Temperature fallback constants (when API doesn't provide values)
# Oven temperature fallbacks
TEMP_OVEN_MAX_C = 230.0  # Typical oven maximum temperature in Celsius
TEMP_OVEN_MAX_F = 446.0  # Typical oven maximum temperature in Fahrenheit (~230°C)
TEMP_OVEN_MIN_C = 35.0  # Typical oven minimum temperature in Celsius
TEMP_OVEN_STEP = 5.0  # Typical oven temperature step increment

# Food probe temperature fallbacks
TEMP_PROBE_MAX_C = 99.0  # Typical food probe maximum in Celsius
TEMP_PROBE_MAX_F = 210.0  # Typical food probe maximum in Fahrenheit (~99°C)

# Default number entity fallbacks (for non-temperature entities)
DEFAULT_NUMBER_MAX = 100.0
DEFAULT_NUMBER_MIN = 0.0
DEFAULT_NUMBER_STEP = 1.0

# Number entity UI mode selection threshold
# Controls when to use SLIDER (≤threshold steps) vs BOX (>threshold steps)
# SLIDER: Better for small ranges with visual feedback (e.g., temperature 30-230°C in 5° steps = 41 steps)
# BOX: Better for large ranges where typing is faster (e.g., time 0-1440 min in 1 min steps = 1440 steps)
NUMBER_MODE_SLIDER_MAX_STEPS = 100

# Time conversion constants
TIME_INVALID_SENTINEL = -1  # Indicates invalid/unset time value
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400

# Appliance state constants
# Food probe states
FOOD_PROBE_STATE_INSERTED = "INSERTED"
FOOD_PROBE_STATE_NOT_INSERTED = "NOT_INSERTED"

# Remote control states
# Different appliances report different remote control states:
# - ENABLED: Standard remote control enabled
# - NOT_SAFETY_RELEVANT_ENABLED: Remote control enabled for non-safety features
# - persistentRemoteControl: Always-on remote control
# - DISABLED: Remote control disabled by user or safety lock
REMOTE_CONTROL_ENABLED = "ENABLED"
REMOTE_CONTROL_NOT_SAFETY_RELEVANT_ENABLED = "NOT_SAFETY_RELEVANT_ENABLED"
REMOTE_CONTROL_DISABLED = "DISABLED"

# Time value sentinels
TIME_INVALID_OR_NOT_SET = "INVALID_OR_NOT_SET_TIME"

# Connectivity states
CONNECTIVITY_STATE_CONNECTED = "connected"
CONNECTIVITY_STATE_DISCONNECTED = "disconnected"

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
