# Release Notes v3.4.6

## Bug Fix: Missing Entities After Network Timeout During Setup

### Problem

On poor or unstable connections, appliance-specific entities such as `timeToEnd`, `cyclePhase`, `doorState`, and other washer/dryer/oven sensors were permanently absent from Home Assistant — even after the connection recovered and the appliance came back online.

A typical log sequence indicating the issue:

```
WARNING Network error getting required data for appliance 914580416_... (Стиральная машина) after 13.25 seconds: TimeoutError
WARNING Appliance ... will be created with minimal data and populated during next update cycle (within 6 hours)
```

After the 6-hour update cycle, the appliance would be refreshed but the expected entities (e.g. `sensor.electrolux_stiralnaia_mashina_timetoend`) were never created.

### Root Cause

When `get_appliance_state` or `get_appliances_info` timed out during initial setup, the integration created a **minimal appliance** with an empty reported state (`"reported": {}`). The appliance type (`applianceType`, e.g. `"WM"` for washers) is normally extracted from the reported state, but in the minimal appliance it was absent — returning `None`.

The entity catalog is filtered by appliance type. With `appliance_type = None`, no type-specific catalog entries were loaded, so washer entities like `timeToEnd`, `cyclePhase`, `spinSpeed`, `waterHardness` etc. were never registered in Home Assistant. They remained missing permanently because HA entity registry entries are not retroactively added on state updates.

### Fix

The `applianceType` and `modelName` are now extracted at the **very start** of `_setup_single_appliance`, before any async API calls, directly from the appliance list response (which is always available and does not require additional network round-trips). This data is injected into the minimal appliance state whenever any of the four error paths (network error, data validation error, unexpected error, or global timeout) cause a fallback to minimal mode.

```python
# Extracted before any async calls — always available from list API
_appliance_type_hint: str | None = appliance_json.get("applianceType")
_model_hint: str = (
    appliance_json.get("applianceData", {}).get("modelName") or "Unknown"
)
```

All minimal appliance states now include:

```python
"properties": {"reported": {
    "applianceInfo": {"applianceType": _appliance_type_hint},
}}
```

This ensures that even on the worst possible connection, the correct appliance type is known, the full type-specific entity catalog is loaded, and all expected entities are created in Home Assistant (appearing as unavailable until state data arrives, rather than being absent entirely).

### After Upgrading

If your appliance has missing entities due to this issue:

1. Restart Home Assistant after updating.
2. The missing entities will be created automatically.
3. If entities still appear missing, press the **Manual Sync** button on the appliance device card.

---

## Enhancement: Additional Washer Entities from Reported State

Based on a diagnostic submission from a model 914580416 washing machine (capabilities API unavailable), the following entities were added to the washer catalog. These are washer-specific options that report **without** a model prefix (e.g. `userSelections/anticreaseNoSteam` rather than `userSelections/EWX1493A_anticreaseNoSteam`), so they were invisible to all existing catalog entries:

| Property | Entity |
|---|---|
| `userSelections/anticreaseNoSteam` | Switch – Anti-Crease No Steam |
| `userSelections/anticreaseWSteam` | Switch – Anti-Crease With Steam |
| `userSelections/ultraMix` | Switch – Ultra Mix |
| `userSelections/preWashPhase` | Switch – Pre-Wash |
| `userSelections/stain` | Switch – Stain Action |
| `userSelections/nightCycle` | Switch – Night Cycle |
| `userSelections/wmEconomy` | Switch – Economy Mode |
| `userSelections/rinseHold` | Switch – Rinse Hold |
| `userSelections/tcSensor` | Switch – Temperature Care Sensor |
| `userSelections/soak` | Switch – Soak |
| `userSelections/softener` | Switch – Softener |
| `language` | Select – Language (config, disabled by default) |

Other properties present in the diagnostic (`timeToEnd`, `remoteControl`, `applianceTotalWorkingTime`, `totalCycleCounter`, `userSelections/programUID`, `endOfCycleSound`, `networkInterface/linkQualityIndicator`, `networkInterface/swVersion`) are already covered by the core catalog and were already available.

---

## Files Changed

- `custom_components/electrolux/coordinator.py` — `_setup_single_appliance` now extracts `applianceType` and `modelName` from the list API response before any async calls and injects them into all minimal appliance state fallbacks.
- `custom_components/electrolux/catalog_washer.py` — Added 12 new entries: generic (non-model-prefixed) `userSelections/` boolean switches and `language` setting.

---

## Supported Appliances (as of v3.4.6)

| Type | Appliance | Status | Verified Samples |
|------|-----------|--------|-----------------|
| `OV` | Oven | Full | OV-944188772 |
| `SO` | Steam Oven | Full | SO-944035035 |
| `RF` | Refrigerator | Partial | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |
| `CR` | Combined Refrigerator | Full | CR-925060324 |
| `WM` | Washing Machine | Full | WM-914501128, WM-914915144, WM-914580416 |
| `WD` | Washer-Dryer | Full | WD-914611000, WD-914611500 |
| `TD` | Tumble Dryer | Full | TD-916098401, TD-916098618, TD-916099548, TD-916099949, TD-916099971 |
| `AC` | Air Conditioner | Full | AC-910280820 |
| `DW` | Dishwasher | Full | DW-911434654, DW-911434834 |
| `A9` / `Muju` | Air Purifier | Full | A9 series; UltimateHome 500 (EP53) |
| `MW` | Microwave | Stub | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |