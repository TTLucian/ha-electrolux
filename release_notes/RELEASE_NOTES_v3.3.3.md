# Release Notes v3.3.3

## Overview
v3.3.3 is a focused bug fix release addressing tumble dryer issues reported by users in real-world testing, plus UX improvements for entity naming and command validation. All fixes based on actual user feedback with model 916099949 (TD type).

**Key Fixes:**
1. programUID entity always showing blank
2. Program-context capability validation not working correctly
3. Load weight displaying error codes (65410g shown instead of filtered out)
4. DWYW entities cluttering UI despite being irrelevant
5. Confusing duplicate entity names (Program vs Program)
6. Client-side command validation removed for optimistic API sending

## Bug Fix: programUID Entity Always Blank

### Problem
The `programUID` entity (showing current program identifier like "Cottons", "Synthetics", etc.) was always showing blank/unavailable even when the appliance was running a program.

### Root Cause
The `programUID` attribute was subject to program-specific capability filtering. When the current program didn't explicitly list `programUID` in its supported capabilities, the entity would show as unavailable.

### Solution
Added `programUID` to the always-supported entities list so it always displays the current program regardless of capability restrictions.

**Files Changed:**
- `entity.py` - Added "programUID" to always-supported list alongside analogWriteStatus

### Impact
- programUID entity now always shows current program when available
- No longer incorrectly filtered out by program-specific capability validation
- Users can always see which program is currently selected/running

## Bug Fix: Program-Context Capability Validation

### Problem
Program-specific capability restrictions weren't working correctly. Entities that should be available/unavailable based on the current program's supported capabilities were not being filtered properly.

### Root Cause
The capability path matching logic in `_is_capability_supported_by_current_program()` was comparing mismatched paths:
- Entity had `entity_source` = "DAM_appliance/cavities/0/state" and `entity_attr` = "targetTemperatureC"
- But comparison used full `entity_attr` against capability paths, missing nested structure

### Solution
Fixed path resolution to properly extract the attribute name from `entity_source` and `entity_attr` combinations, then match against capability paths accounting for both direct matches and nested structures.

**Files Changed:**
- `entity.py` - Fixed `_is_capability_supported_by_current_program()` path matching logic

### Impact
- Number controls properly lock at minimum value when program doesn't support them
- Select entities show empty and lock when program doesn't support them
- Prevents HomeAssistantError with clear messages when users try to modify unsupported controls
- All entities remain available (not unavailable) to prevent UI rendering issues

## Bug Fix: Load Weight Displaying Error Codes

### Problem
Load weight sensor was displaying nonsensical values like 65410g instead of being unavailable or showing a proper value.

### Root Cause
The Electrolux API returns special values in the range 65408-65532 as error codes or "not applicable" indicators. These were being displayed as actual weight values.

### Solution
Added special value filtering to detect and exclude the reserved range 65408-65532 from display. When these values are encountered, the sensor shows as unavailable rather than displaying the error code.

**Files Changed:**
- `sensor.py` - Added special value range check (65408-65532) for load weight

### Impact
- Load weight sensor no longer shows error codes as weight values
- Sensor properly shows unavailable when actual weight data isn't available
- Applies to all appliances that report load weight (washers, dryers)

## Enhancement: Hidden DWYW Entities by Default

### Problem
"Do What You Want" (DWYW) program entities were cluttering the UI for all users, but they're only relevant for specific appliances that support this feature. Most users don't have DWYW-capable appliances, making these entities unnecessary visual noise.

### Root Cause
DWYW entities were created as visible by default for all appliances, regardless of whether the appliance actually supports the DWYW program.

### Solution
Added automatic detection to hide DWYW entities by default using `entity_registry_visible_default: False`. Users with DWYW-capable appliances can manually unhide these entities in the UI if needed.

**Affected Entities:**
- dwyws_programUID
- dwyws_antiCrease
- dwyws_dryingLevel
- dwyws_humidityTarget
- dwyws_spinSpeed
- dwyws_temperature
- All other DWYW preset entities

**Files Changed:**
- `entity.py` - Added automatic DWYW entity detection and default hiding

### Impact
- Cleaner UI for majority of users without DWYW-capable appliances
- DWYW entities still available for users who need them (unhide in entity settings)
- Reduces entity count clutter without removing functionality
- More polished user experience out-of-the-box

## Enhancement: Improved Entity Naming

### Problem
Tumble dryers (and other appliances) had confusing duplicate entity names that made it unclear which was the active control vs saved default:
- "Program" for both active program and default program
- "Anti-Crease" for both active setting and default setting
- "Spin Speed" for both active value and default value

### Solution
Implemented clearer naming convention:
- **Active controls:** "Program (Active)", "Anti-Crease (Active)", etc.
- **Saved defaults:** "Default: Program", "Default: Anti-Crease", etc.

**Files Changed:**
- `catalog_dryer.py` - Updated friendly names for all dryer entities

**Examples:**
- `programUID` → "Program (Active)"
- `dwyws_programUID` → "Default: Program"
- `antiCrease` → "Anti-Crease (Active)"
- `dwyws_antiCrease` → "Default: Anti-Crease"
- `humidityTarget` → "Humidity Target (Active)"
- `dwyws_humidityTarget` → "Default: Humidity Target"

### Impact
- Clear distinction between active running values and saved defaults
- No more confusion about which entity to modify
- Consistent naming pattern across all duplicate entities
- Easier to understand at a glance what each entity represents

## Enhancement: Removed Client-Side Command Validation

### Problem
Client-side validation in button entities (START, STOPRESET) was attempting to predict API behavior, but this led to inconsistencies:
- Different appliances have different valid state transitions
- Ovens can START from OFF, washers need READY_TO_START
- Client-side logic couldn't keep up with all appliance variations
- Blocked legitimate commands that API would accept

### Solution
Removed all client-side command validation from button entities. Commands are now sent optimistically to the API, which performs accurate appliance-specific validation and returns clear error messages when commands are rejected.

**Files Changed:**
- `button.py` - Removed ~50 lines of START/STOPRESET validation logic

**Design Philosophy:**
- ✅ Send commands optimistically to API
- ✅ Let API validate with appliance-specific rules
- ✅ Display API error messages to users
- ❌ No client-side blocking of commands

### Impact
- Simpler, more maintainable code
- API handles all validation with appliance-specific rules
- Users see accurate error messages from the actual appliance
- No false-positive command rejections
- START button works correctly for all appliance types (ovens, washers, dryers, etc.)

## Testing
All 360 automated tests passing, including:
- Button entity tests (with simplified validation removal)
- Number entity tests (program-specific validation)
- Sensor entity tests (special value filtering)
- Entity availability tests (DWYW hiding, programUID always-supported)
- Select entity tests (program-specific capability filtering)

## Upgrade Notes
- **No breaking changes** - This is a pure bug fix and enhancement release
- **DWYW entities hidden by default** - If you use DWYW features, unhide the entities in Settings → Entities
- **Load weight sensor** - May show unavailable more often (correct behavior when no valid weight data)
- **programUID entity** - Will now always show current program
- **Entity names changed** - Active controls and defaults have clearer labels

## Files Modified Summary
- `entity.py` - programUID always-supported, program capability validation fix, DWYW hiding
- `sensor.py` - Load weight special value filtering
- `catalog_dryer.py` - Improved entity naming
- `button.py` - Removed client-side validation
