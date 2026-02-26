# Release Notes v3.3.8

## Overview
v3.3.8 includes bug fixes for climate entity functionality and adds support for UltimateHome 500 (EP53) air purifiers. This release fixes temperature unit change detection, restores fan speed and swing mode control functionality, and implements 10 new UltimateHome 500-specific capabilities (UV sterilization, enhanced filter management, additional sensors).

**Key Improvements:**
- **UltimateHome 500 Air Purifier Support**: Added 10 new capabilities including UV sterilization, PM2.5 monitoring, and comprehensive filter management
- **Climate Unit Change Detection**: Fixed climate entity not detecting temperature unit changes made on the appliance
- **Fan Speed Control**: Fixed inability to change fan speed through climate entity
- **Swing Mode Control**: Fixed inability to change swing mode through climate entity

---

## Added: UltimateHome 500 Air Purifier Support

### Overview
Full integration support added for UltimateHome 500 (EP53) air purifier appliances. This model supports the existing A9 purifier capabilities (work mode, fan speed, safety lock, UI light) plus 10 new UltimateHome 500-specific capabilities including UV sterilization, enhanced PM2.5 monitoring, and comprehensive filter management.

**Air Purifier Fan Entity:** Added a unified fan entity that combines Workmode and Fanspeed into a feature-rich Home Assistant fan control. The fan entity provides on/off control (via PowerOff mode), percentage-based speed control (0-100%), and preset modes (Manual, Auto, Quiet). The existing separate Workmode select and Fanspeed number entities remain available for users who prefer individual controls.

### New Capabilities Added

**NEW Control Entity (1):**
- **UV Sterilization**: UV light control with string-based ON/OFF switch

**ENHANCED Existing Control (1):**
- **Work Mode**: Added "Quiet" mode to existing Manual, Auto, and PowerOff modes

**NEW Sensor Entities (9):**
- **Filter Life**: 0-100% filter life remaining with air-filter icon
- **Filter Type**: Displays current filter type installed (13 recognized types including Standard, HEPA, Activated Carbon, Antibacterial, etc.)
- **PM2.5 Level (Approximate)**: Air quality monitoring with PM2.5 device class (in addition to existing PM2.5 sensor)
- **UV Runtime**: Tracks UV sterilization runtime in seconds (duration device class)
- **Scheduling State**: Displays current scheduling status (diagnostic entity)
- **Error Sensors**: 4 diagnostic sensors for impeller, PM sensor, display board, and UI board communication

### Existing A9 Purifier Capabilities (Already Supported)
- **Work Mode**: Manual, Auto, PowerOff modes with icon selection
- **Fan Speed**: 10-level speed control (0-9) with slider interface  
- **Safety Lock**: Child lock control via switch entity
- **UI Light**: Display light control via switch entity
- **Signal Strength**: Wi-Fi signal strength monitoring
- **PM2.5**: Standard PM2.5 sensor

### Technical Implementation

**Catalog Mapping:**
- Added `"Muju": _get_catalog_purifier()` mapping to `CATALOG_BY_TYPE` in [catalog_core.py](custom_components/electrolux/catalog_core.py#L156) (Muju is the technical appliance type identifier for UltimateHome 500 (EP53))
- Updated purifier catalog with UltimateHome 500 (EP53)-specific capabilities in [catalog_purifier.py](custom_components/electrolux/catalog_purifier.py)
- Added unified fan entity (`Workmode/fan`) to catalog that combines Workmode and Fanspeed controls

**Fan Entity Implementation:**
Created new fan platform ([fan.py](custom_components/electrolux/fan.py)) for air purifiers with the following features:
- **On/Off Control**: Maps to Workmode PowerOff state vs active modes
- **Speed Percentage**: Converts Fanspeed (1-9 or 1-5) to percentage (0-100%) using Home Assistant's ordered list conversion
- **Preset Modes**: Maps to Workmode values (Manual, Auto, Quiet) for convenient operation modes
- **Dynamic Capability Detection**: Automatically adapts to appliance-specific speed ranges (A9: 1-9, Muju: 1-5)
- **Optimistic Updates**: Provides immediate UI feedback during command execution
- **Error Handling**: Comprehensive connectivity and command validation with user-friendly error messages

Supported Fan Features:
- `TURN_ON` / `TURN_OFF` - Control fan power state
- `SET_SPEED` - Adjust speed via percentage slider (0-100%)
- `PRESET_MODE` - Select operation mode (Manual, Auto, Quiet)

**Command Formatting Fix:**
Fixed critical issue with string-based ON/OFF switches (UVState) where boolean values from switch entities weren't being converted to string format:

**Before Fix:**
```python
# Boolean True was converted to string "True" 
# Command: {"UVState": "True"} ❌ Rejected by API
```

**After Fix:**
```python
# Special case in format_command_for_appliance() detects boolean input
# for string-type capabilities with ON/OFF values
if isinstance(value, bool):
    upper_values = {str(k).upper() for k in values_dict.keys()}
    if upper_values == {"ON", "OFF"}:
        target_value = "ON" if value else "OFF"
        # Preserves case from capability definition
        return matching_key  # "ON" or "OFF"

# Result: {"UVState": "ON"} ✅ Accepted by API
```

**Entity Configuration:**
- All entities configured with appropriate device classes (PM25, Duration, etc.)
- Custom icons assigned (air-filter, sun-wireless, etc.)
- Proper entity categories (config for controls, diagnostic for errors)
- Number controls with min/max constraints and step values

### Impact
- ✅ UltimateHome 500 (EP53) air purifiers now fully supported with 10 new model-specific capabilities
- ✅ **New Fan entity** provides unified control with on/off, speed percentage, and preset modes
- ✅ Fan entity works with both A9 and Muju air purifiers (adapts to 1-9 or 1-5 speed ranges)
- ✅ Existing Workmode select and Fanspeed number entities remain available for granular control
- ✅ UV sterilization control works correctly with proper string command formatting
- ✅ Enhanced PM2.5 air quality monitoring with approximate sensor
- ✅ Comprehensive filter management with life percentage and type identification
- ✅ Quiet mode added for reduced noise operation
- ✅ Comprehensive error monitoring for proactive maintenance
- ✅ No conflicts with existing appliance types (validated via test suite)

### Testing
Comprehensive test coverage added:
- `test_string_capability_boolean_to_on_off()`: Verifies UVState boolean-to-string conversion
- `test_boolean_vs_string_on_off_switches()`: Ensures boolean-type switches (cavityLight) unaffected
- `test_string_capability_with_non_on_off_values()`: Validates other string switches work correctly
- All 364 tests passing, confirming no regressions in other appliance types

---

## Fixed: Climate Entity Temperature Unit Not Updating When Changed on Appliance

### Problem
When changing the temperature unit (Celsius ↔ Fahrenheit) on the physical AC appliance, the Home Assistant climate entity continued to display the old unit. The unit would only update if the user also changed Home Assistant's global temperature unit setting.

```
User changes appliance from Celsius to Fahrenheit:
❌ Climate entity still shows: 23°C
✅ Should show: 73°F

Workaround required: Change HA's global temp unit to force refresh
```

This created a confusing user experience where the appliance and Home Assistant showed different units until HA was manually updated.

### Root Cause
Home Assistant's climate platform caches the `temperature_unit` property and doesn't detect changes unless an attribute with a watched name changes. Simply returning a different value from the property getter is insufficient to trigger UI updates.

The climate entity's `temperatureRepresentation` state was updating correctly via SSE events, but the climate platform's change detection mechanism wasn't being triggered.

**Before Fix:**
```python
# Property-only implementation - HA doesn't detect changes
@property
def temperature_unit(self) -> str:
    temp_rep = self.get_state_attr("temperatureRepresentation")
    if temp_rep == "FAHRENHEIT":
        return UnitOfTemperature.FAHRENHEIT
    return UnitOfTemperature.CELSIUS
```

**After Fix:**
```python
# Attribute-based tracking with auto-sync property
def __init__(self, ...):
    self._attr_temperature_unit = UnitOfTemperature.CELSIUS

@property
def temperature_unit(self) -> str:
    """Get current temperature unit and ensure attribute stays in sync."""
    current_unit = self._get_temperature_unit()
    if current_unit != self._attr_temperature_unit:
        self._attr_temperature_unit = current_unit
    return self._attr_temperature_unit

def _handle_coordinator_update(self) -> None:
    """Handle updated data from coordinator and detect unit changes."""
    new_unit = self._get_temperature_unit()
    if new_unit != self._attr_temperature_unit:
        _LOGGER.debug(
            "Temperature unit changed from %s to %s for %s",
            self._attr_temperature_unit,
            new_unit,
            self.pnc_id,
        )
        self._attr_temperature_unit = new_unit
    super()._handle_coordinator_update()
```

### Technical Details
- **Changed File**: `custom_components/electrolux/climate.py`
- **Mechanism**: Added `_attr_temperature_unit` attribute that Home Assistant monitors for changes
- **Auto-Sync**: Property getter automatically updates the attribute when source value changes
- **Logging**: Added debug logging when temperature unit changes are detected
- **Change Detection**: HA's climate platform now properly detects unit changes via attribute monitoring

### Impact
- ✅ Temperature unit changes on appliance now immediately reflected in HA UI
- ✅ No need to change HA's global temperature unit setting as workaround
- ✅ Proper synchronization between appliance state and HA display
- ✅ Debug logging helps troubleshoot unit change issues

### Testing
Full test coverage added to validate temperature unit change detection:
- Test verifies `_attr_temperature_unit` updates when `temperatureRepresentation` changes
- Validates both CELSIUS → FAHRENHEIT and FAHRENHEIT → CELSIUS transitions
- Ensures property and attribute remain synchronized

---

## Fixed: Climate Entity Fan Speed and Swing Mode Controls Not Working

### Problem
Users were unable to change fan speed or swing mode through the climate entity interface. While the climate entity correctly displayed the available fan modes and swing modes, attempting to change these settings had no effect on the appliance.

```
User attempts to change fan speed in climate entity:
❌ Command fails silently - appliance fan speed unchanged
❌ Swing mode changes also had no effect

Workaround: Use separate switch entities for verticalSwing
```

This rendered the climate entity's fan and swing controls non-functional, forcing users to control these features through separate switch entities instead of the unified climate interface.

### Root Cause
The climate entity's setter methods were sending commands to incorrect attribute names that don't exist in the AC appliance capabilities:

**Incorrect Attributes Used:**
- `async_set_fan_mode()` was sending commands to `fanMode` (doesn't exist)
- `async_set_swing_mode()` was sending commands to `swingMode` (doesn't exist)

**Correct Attributes in AC Capabilities:**
- Fan speed is controlled via `fanSpeedSetting` 
- Vertical swing is controlled via `verticalSwing`

The property getters were correctly reading from `fanSpeedSetting` and `verticalSwing`, but the setters were trying to write to non-existent attributes, causing commands to fail.

**Before Fix:**
```python
@property
def fan_mode(self) -> str | None:
    """Return the fan setting."""
    value = self.get_state_attr("fanSpeedSetting")  # ✅ Correct
    return str(value).lower() if value else None

async def async_set_fan_mode(self, fan_mode: str) -> None:
    """Set new target fan mode."""
    await self._send_command("fanMode", fan_mode.upper())  # ❌ Wrong attribute
```

**After Fix:**
```python
@property
def fan_mode(self) -> str | None:
    """Return the fan setting."""
    value = self.get_state_attr("fanSpeedSetting")  # ✅ Correct
    return str(value).lower() if value else None

async def async_set_fan_mode(self, fan_mode: str) -> None:
    """Set new target fan mode."""
    await self._send_command("fanSpeedSetting", fan_mode.upper())  # ✅ Fixed
```

### Technical Details
- **Changed File**: `custom_components/electrolux/climate.py`
- **Fixed Methods**:
  - `async_set_fan_mode()`: Now sends commands to `fanSpeedSetting` (was `fanMode`)
  - `async_set_swing_mode()`: Now sends commands to `verticalSwing` (was `swingMode`)
- **Verification**: Confirmed against multiple AC appliance diagnostic files
- **Test Updates**: Updated test expectations to match correct attribute names

### Impact
- ✅ Fan speed changes through climate entity now work correctly
- ✅ Swing mode changes through climate entity now work correctly
- ✅ Climate entity provides unified control interface for AC appliances
- ✅ No need to use separate switch entities for these controls

### Testing
Updated test suite to verify correct attribute names:
- `test_async_set_fan_mode`: Verifies commands sent to `fanSpeedSetting`
- `test_async_set_swing_mode`: Verifies commands sent to `verticalSwing`
- All 364 tests passing, confirming no regressions

---

## Installation

Update via HACS or manually replace files and restart Home Assistant.

## Compatibility

- **Home Assistant**: 2024.1.0 or later
- **Python**: 3.11 or later
- **HACS**: Compatible

---

**Full Changelog**: https://github.com/luciangreentree/ha-electrolux-integration/compare/v3.3.7...v3.3.8
