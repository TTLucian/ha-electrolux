# Release Notes v3.3.6

## Overview
v3.3.6 is a critical bug fix release addressing an AC temperature control issue that prevented users from setting temperatures correctly. This release also strengthens the dangerous entity filtering system introduced in v3.3.5.

**Key Improvements:**
1. **AC Temperature Fix**: Fixed "Invalid step" errors for AC units with misaligned temperature ranges
2. **Enhanced Security Filtering**: Improved dangerous entity blocking patterns to prevent edge cases
3. **User Safety Warning**: Important notice about manually removing pre-existing dangerous entities

---

## 🚨 CRITICAL: Manual Action Required for Existing Installations

### Background
v3.3.5 introduced automatic blocking of dangerous entities (like `networkInterface/command` and `networkInterface/startUpCommand`) that could damage appliances if accidentally triggered. However, if you upgraded from a version **before v3.3.5**, these dangerous entities may already exist in your Home Assistant entity registry.

**Home Assistant does NOT automatically delete entities when integration code changes.** Once created, entities persist until manually removed.

### Dangerous Entities That May Be Present

If you upgraded from v3.3.4 or earlier, check for these entities:

❌ **REMOVE IMMEDIATELY:**
- `button.*_network_command_appliance_authorize`
- `button.*_network_command_user_authorize`
- `button.*_network_command_user_not_authorize`
- `button.*_network_interface_start_up_command_uninstall`

⚠️ **REVIEW CAREFULLY:**
- `button.*_network_command_start` (may be safe, but review context)

### How to Remove Dangerous Entities

1. **Go to Settings** → **Devices & Services** → **Entities**
2. **Search for**: `network_command` or `network_interface_start_up`
3. **For each dangerous entity found:**
   - Click on the entity
   - Click the **🗑️ Delete** button (NOT just disable)
   - Confirm deletion
4. **Reload the integration**: Settings → Devices & Services → Electrolux → ⋮ → Reload
5. **Verify** the dangerous entities do NOT reappear

### Why This Matters

These entities control low-level system functions:
- `UNINSTALL` - Can factory reset the network module, requiring professional service
- `APPLIANCE_AUTHORIZE` / `USER_*AUTHORIZE` - Can unpair appliances from your account
- Accidental activation through automations, dashboards, or voice assistants could permanently break connectivity

**The integration NOW prevents these from being created**, but cannot automatically remove existing ones.

---

## Fixed: AC Temperature "Invalid Step" Errors

### Problem
AC units with temperature ranges derived from Fahrenheit-to-Celsius conversion (e.g., min=15.56°C from 60°F, step=1.0) caused API validation errors. When users set 24°C, the integration incorrectly calculated and sent 23.56°C, resulting in:

```
ERROR: Command validation failed - Invalid step
```

Real-world valid temperatures for these units are whole numbers: 16, 17, 18... 30°C, not fractional values like 23.56°C.

### Root Cause
The step validation logic in `format_command_for_appliance()` used the raw API minimum value (15.56) as the step base without aligning it to step boundaries:

```python
# Before fix:
step_base = 15.56  # Raw API min
steps_from_base = (24.0 - 15.56) / 1.0 = 8.44
result = 15.56 + round(8.44) * 1.0 = 23.56  # ❌ Invalid!
```

### Solution
Updated `util.py` `format_command_for_appliance()` (lines 1018-1020) to align the step base to the nearest step boundary:

```python
# After fix:
step_base = round(15.56 / 1.0) * 1.0 = 16.0  # Aligned to step boundary
steps_from_base = (24.0 - 16.0) / 1.0 = 8.0
result = 16.0 + round(8.0) * 1.0 = 24.0  # ✓ Valid!
```

### Impact
- ✅ AC temperature commands now work correctly with misaligned API ranges
- ✅ Prevents "Invalid step" validation errors from appliance API
- ✅ Handles Fahrenheit-to-Celsius conversion artifacts automatically
- ✅ No user configuration required - fix is automatic
- ✅ Works for all numeric entities with misaligned min/step values

### Affected Units
This fix primarily benefits AC units, but also applies to any numeric entity where the API-reported minimum value isn't aligned with the step increment. Common scenarios:
- Temperature ranges converted from Fahrenheit (15.56°C, 32.22°C)
- Legacy appliances with imprecise API metadata
- Regional variants with unit conversion quirks

---

## Enhanced: Dangerous Entity Blocking System

### Improvement
Strengthened the `DANGEROUS_ENTITIES_BLACKLIST` regex patterns to be more defensive against edge cases and variations.

**Before (v3.3.5):**
```python
r"^networkInterface/startUpCommand$"  # Exact match only
r"^networkInterface/command$"  # Exact match only
```

**After (v3.3.6):**
```python
r"^networkInterface/startUpCommand"  # Matches any path starting with this
r"^networkInterface/command"  # Matches any path starting with this
```

### Why This Change
Removing the `$` anchor ensures the patterns catch:
- Exact matches: `networkInterface/command`
- Potential child paths: `networkInterface/command/subpath`
- Any variations that might slip through

While still allowing safe entities:
- ✅ `networkInterface/linkQualityIndicator`
- ✅ `networkInterface/swVersion`
- ✅ `networkInterface/otaState`

### Security Layers
The dangerous entity filtering system has **three layers of protection**:

1. **Catalog-level documentation** (catalog_core.py) - Comments explain why entities are dangerous
2. **API capability filtering** (models.py line 642) - Blocks entities from API discovery
3. **Static catalog filtering** (models.py line 573) - Blocks entities from manual catalog definitions

**All three layers must be bypassed for a dangerous entity to be created.** v3.3.6 strengthens layer #2 and #3 with more defensive patterns.

### Caution Despite Protections

⚠️ **While the filtering system is robust, exercise caution:**

1. **Unknown appliance types** may introduce new dangerous entity patterns not yet in the blacklist
2. **API changes** by Electrolux could expose new low-level commands
3. **Entity naming variations** might bypass pattern matching in edge cases

**If you see ANY entity containing these keywords, do NOT use it:**
- `uninstall`
- `authorize` / `unauthorize`
- `factory_reset`
- `pair` / `unpair`
- `register` / `unregister`

**Report such entities** in a GitHub issue immediately so they can be added to the blacklist.

---

## Files Modified

1. **custom_components/electrolux/util.py** (lines 1018-1020): Fixed step alignment bug in `format_command_for_appliance()` to handle misaligned API min values with step boundaries
2. **custom_components/electrolux/const.py** (lines 75-77): Improved `DANGEROUS_ENTITIES_BLACKLIST` patterns by removing `$` anchors for more defensive matching
3. **tests/test_util.py** (lines 282-310): Added comprehensive test `test_numeric_capability_misaligned_min_with_step()` covering the AC temperature scenario

---

## Test Coverage

**New Tests:**
- `test_numeric_capability_misaligned_min_with_step`: Validates AC unit scenario with min=15.56°C, max=32.22°C, step=1.0
  - Verifies 24°C stays as 24.0 (not 23.56)
  - Tests multiple temperature points (16, 20, 24, 30°C)
  - Validates rounding behavior for fractional inputs

**All Tests Passing:** 361/361 ✅

---

## Upgrade Instructions

### For New Installations (v3.3.6)
No action required. Dangerous entities are automatically blocked.

### For Upgrades from v3.3.4 or Earlier
**⚠️ MANUAL ACTION REQUIRED:**

1. **Before upgrading**, document any custom automations using network-related entities
2. **Upgrade** to v3.3.6
3. **Manually remove dangerous entities** (see "Manual Action Required" section above)
4. **Reload integration** to verify entities don't reappear
5. **Test AC temperature controls** if you have AC units

### For Upgrades from v3.3.5
1. **Upgrade** to v3.3.6
2. **No manual action required** (dangerous entities already blocked)
3. **AC temperature fix applies automatically** on next command

---

## Known Limitations

1. **Entity registry cleanup**: Home Assistant does not support automatic entity deletion via integration code. Users must manually remove pre-existing dangerous entities.

2. **AC temperature limits**: The fix aligns step calculations but does not modify the min/max values reported by the API. If your AC reports min=15.56°C, the actual minimum settable temperature will be 16°C (rounded to step boundary).

3. **Partial blacklist coverage**: The `DANGEROUS_ENTITIES_BLACKLIST` covers known dangerous patterns. Unknown or future appliance types may introduce new dangerous entities not yet blacklisted. **Report any suspicious entities immediately.**

---

## What's Next

Users should monitor for:
- Any new entities containing keywords: `uninstall`, `authorize`, `factory`, `reset`, `pair`
- Unusual button entities under `networkInterface` namespace
- Write-only entities without clear documentation

**Report findings** at: https://github.com/TTLucian/ha-electrolux/issues

---

## Thank You

Special thanks to users who reported:
- The AC temperature "Invalid step" issue
- Discovery of dangerous entities persisting after v3.3.5 upgrade

Your feedback makes the integration safer and more reliable for everyone.

---

## Summary

**Critical Fixes:**
- ✅ AC temperature commands now work correctly
- ✅ Enhanced dangerous entity filtering
- ⚠️ **Manual removal required for pre-existing dangerous entities**

**Compatibility:**
- Requires Home Assistant 2024.1.0 or later
- Python 3.11 or later
- electrolux-group-developer-sdk >= 0.2.0

**Version:** 3.3.6  
**Release Date:** February 2026
