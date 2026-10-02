# Release Notes v3.2.7

## 🎉 HACS Integration Now Official!

**Great news!** The integration is now available directly in the HACS default repository. The PR to HACS has been merged, which means:

✅ **No more custom repository URLs needed**  
✅ **Easier discovery for new users**  
✅ **Automatic updates through HACS**  
✅ **Official HACS badge and visibility**  

Simply search for "Electrolux" in HACS → Integrations to install!

---

## 🔧 Bug Fixes

### A few bugs I can't remember, mostly for air conditioners...

### Fixed Temperature Controls Becoming Read-Only Sensors (Regression)

**Problem:**
Temperature control entities (like `number.oven_target_temperature_c`, `number.oven_target_food_probe_temperature_c`, refrigerator temperature controls) were incorrectly created as read-only sensor entities instead of adjustable number sliders. This was a regression introduced in an earlier version when device class override logic was added to the entity creation process.

**Root Cause:**
Catalog definitions were using `SensorDeviceClass.TEMPERATURE` instead of `NumberDeviceClass.TEMPERATURE`. The device class override logic in entity creation prioritized the device class type over the correct capability-based determination.

**Fix:**
- Updated `catalog_oven.py`: Changed 4 temperature entities to use `NumberDeviceClass.TEMPERATURE`
- Updated `catalog_refrigerator.py`: Changed 3 temperature entities to use `NumberDeviceClass.TEMPERATURE`
- All writable temperature controls now correctly appear as number sliders

**Impact:** 
After updating and restarting Home Assistant, temperature controls will be adjustable again. No entity IDs changed - they simply regain their number slider functionality.

**Affected Entities Fixed:**
- Ovens: `targetTemperatureC`, `targetTemperatureF`, `targetFoodProbeTemperatureC`, `targetFoodProbeTemperatureF`
- Refrigerators: `freezer/targetTemperatureC`, `fridge/targetTemperatureC`, `extraCavity/targetTemperatureC`

### Disabled Fahrenheit Temperature Entities (API Data Issue)

**Problem:**
Fahrenheit temperature entities (e.g., `number.oven_target_temperature_f`) were displaying incorrect values - they showed Celsius values with Fahrenheit units (like -17.8°C displayed as "-17.8°F").

**Root Cause:**
The Electrolux API reports both `targetTemperatureC` and `targetTemperatureF` fields, but both contain the same Celsius value without proper unit conversion. This is an API/appliance firmware issue.

**Fix:**
Disabled Fahrenheit temperature entities by default (`entity_registry_enabled_default=False`) for ovens:
- `displayTemperatureF` (read-only)
- `targetTemperatureF` (writable)
- `targetFoodProbeTemperatureF` (writable)

**Impact:**
- New installations: Only Celsius entities will appear by default
- Existing installations: Fahrenheit entities remain if already enabled, but users should disable them manually as they show incorrect values
- Users can still enable Fahrenheit entities manually if their appliance properly supports them
- Users that want Fahrenheit controls can change the unit of measurement of the Celsius controls in the entity's settings 

**Recommendation:** Use only Celsius temperature entities unless you've verified your appliance correctly reports Fahrenheit values.

---

## ✨ New Features

### Basic Microwave Support (Foundation)

**What's Added:**
- Created new `catalog_microwave.py` with basic microwave entity definitions
- Added microwave appliance type code `"MW"` to catalog system
- Moved `targetMicrowavePower` sensor to microwave-specific catalog
- Includes basic entities: `applianceState`, `timeToEnd`, microwave power sensor

**Status:** ⚠️ **Preparation Phase**
This is foundational infrastructure for future microwave support. Full implementation requires JSON diagnostic data from users with microwave appliances.

**When Full Support Will Be Available:**
Once diagnostic JSON files are received from users, the following features can be added:
- Power level controls
- Cooking mode selection
- Timer controls
- Quick start buttons
- Defrost settings
- Child lock
- Microwave-specific programs

**For Microwave Owners:**
If you have an Electrolux microwave, please help me by:
1. Going to Settings → Devices & Services → Electrolux
2. Selecting your microwave device
3. Downloading the diagnostic file
4. Submitting it via GitHub issue

---

## 🔇 Performance Improvements

### Reduced Debug Log Noise

Implemented intelligent log throttling to reduce repeated debug messages:

- **Token validation logs**: Now only log status changes or every 30+ seconds (instead of every API call)
- **Time jump warnings**: Throttled to once per hour after system wake/sleep
- **Food probe debug messages**: Reduced to once per hour when probe not inserted

**Impact:** Significantly cleaner debug logs without losing diagnostic value.

---

## 🎯 Enhancements

### Improved Error Messages - See Exactly Why Commands Fail

**What's Improved:**
Enhanced error handling to provide users with specific, actionable error messages instead of generic failures.

**Changes:**
- **Parse API error details from exception messages**: Now extracts structured error data (error codes, details) from SDK exceptions
- **Include specific reasons in validation errors**: Instead of generic "Command not accepted by appliance", users now see the actual reason (e.g., "Command not accepted: Remote control disabled")
- **Better error detail extraction**: Automatically parses error detail messages from API responses

**Examples of Improved Messages:**
- Before: *"Command not accepted by appliance. Check that the appliance supports this operation."*
- After: *"Command not accepted: Remote control disabled"* (when applicable)
- Or: *"Command not accepted: Food probe not inserted"*
- Or: *"Command not accepted: Invalid step"*

**Impact:** 
Users now get immediate, clear feedback about why a command failed without having to check logs. Error messages explain exactly what needs to be fixed (enable remote control, insert probe, close door, etc.).

---

## Upgrade Instructions

1. **Update via HACS** to v3.2.7
2. **Restart Home Assistant** (full restart required)
3. **Verify fixes:**
   - Temperature controls (oven, fridge) now appear as adjustable number sliders
   - Microwave power sensor warning is gone (if you had it)
4. **Optional - Disable incorrect Fahrenheit entities:**
   - If you have Fahrenheit temperature entities enabled (e.g., `number.oven_target_temperature_f`)
   - Go to Settings → Devices & Services → Electrolux → Your Appliance
   - Disable any `*TemperatureF` entities (they show incorrect values)
   - Use only Celsius entities for accurate temperature readings

---

## For Developers

### New Catalog Structure
Added microwave catalog following the same pattern as other appliance types:
- `catalog_microwave.py` - Microwave-specific entity definitions
- Lazy-loaded via `_get_catalog_microwave()` in catalog_core.py
- Registered as appliance type `"MW"` in catalog system

### Testing
All 334 tests continue to pass with no regressions.

---

## Known Limitations

- Microwave support is currently basic (state sensors only)
- Proper microwave functionality requires diagnostic JSON data from users
- No new entities will appear for non-microwave appliances

---

## Summary

### What's New
✅ **HACS Default Repository** - Now available directly in HACS  
✅ **Microwave infrastructure** prepared for full implementation  
✅ **Temperature control regression fixed** - Number sliders restored (broken in earlier version)  
✅ **Fahrenheit entities disabled** - API reports incorrect F values (Celsius data mislabeled as Fahrenheit)  
✅ **Improved error messages** - See exactly why commands fail with specific, actionable feedback  
✅ **Debug log verbosity** reduced with intelligent throttling  
✅ **Entity availability** improved (entities now show 'unknown' state when offline instead of becoming unavailable)

---

## Contributors

Thanks to the community for reporting issues and providing feedback on the temperature control regression and device class warnings.
