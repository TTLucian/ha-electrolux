# Release Notes v3.4.1

> ### 📋 DAM Appliance Diagnostics Needed
>
> This release adds **basic DAM appliance support**, but the entity catalog for DAM device types is currently empty. Without real diagnostic samples the integration cannot enrich DAM entities with device classes, units, icons, or friendly names.
>
> **If you own a DAM appliance (identifiable by an appliance ID starting with `1:` or an appliance type starting with `DAM_`), please [open a GitHub issue](https://github.com/TTLucian/ha-electrolux/issues) and attach your downloaded diagnostics** (Settings → Devices & Services → Electrolux → three-dot menu → Download diagnostics).
>
> Without submitted JSON samples, DAM appliances will appear with plain generic sensors and no enrichment.

> ### 🤖 Robot Vacuum Cleaner (RVC) Support Wanted
>
> Robot Vacuum Cleaner support is planned for a future release, but **no diagnostic samples have been submitted yet**. Without a sample the integration cannot determine the appliance type code, capability keys, state values, or command structure needed to build the vacuum entity and room-cleaning controls.
>
> **If you own an Electrolux or AEG robot vacuum (Pure i8, Pure i9, Gordias, Cybele, or any other model managed through the Electrolux app), please [open a GitHub issue](https://github.com/TTLucian/ha-electrolux/issues) titled `RVC diagnostics — [your model]`** and attach your diagnostics (Settings → Devices & Services → Electrolux → three-dot menu → Download diagnostics).
>
> The more models covered, the sooner full room-cleaning and zone support can be added.

> ### 🍽️ Microwave Oven Diagnostics Needed
>
> The `MW` (Microwave) appliance type is registered in the integration but its entity catalog is empty — no capability keys, device classes, units, or icons have been defined yet. This is entirely due to the absence of real diagnostic samples.
>
> **If you own an Electrolux or AEG microwave oven managed through the Electrolux app, please [open a GitHub issue](https://github.com/TTLucian/ha-electrolux/issues) titled `MW diagnostics — [your model]`** and attach your diagnostics (Settings → Devices & Services → Electrolux → three-dot menu → Download diagnostics).
>
> Without a sample, the microwave will continue to appear with only generic sensors and no enrichment.

> ### 📋 Help Improve Entity Catalog Quality
>
> The integration builds its entity catalog from real device diagnostic data. Every Electrolux appliance model exposes a different set of capabilities, and without your diagnostics the catalog can only be as accurate as the samples already on hand.
>
> **If you want better entity types, units, icons, and device classes for your appliance — [open a GitHub issue](https://github.com/TTLucian/ha-electrolux/issues) and attach your diagnostics** (Settings → Devices & Services → Electrolux → three-dot menu → Download diagnostics).
>
> This is especially valuable for appliance types with limited samples: dryers, tumble dryers, refrigerators, air conditioners, and any other type

## Overview

v3.4.1 is a catalog expansion and compatibility release. It introduces basic DAM (Data Analysis Module) appliance support and a catalog expansion driven by four new user-submitted diagnostic samples: two tumble dryers (TD-916098401, TD-916098618), one washing machine (WM-914501128), one washing machine (WM-914915144), and one combined fridge-freezer (CR model EHE6899BA, 925060324). The release adds support for the `CR` appliance type, extends the tumble dryer program list, adds load sensing and cycle statistics sensors for dryers, and broadens the washing machine catalog with additional EWX1493A cycle option switches and automatic detergent dispenser sensors.

**FIXES:**
- **DAM catalog lookup**: DAM appliance types are prefixed with `DAM_` in the API (e.g. `DAM_AC`). The integration now strips this prefix before catalog lookups, so `DAM_AC` correctly receives `AC` catalog enrichment
- **DAM device identity**: DAM appliance IDs are prefixed with `1:` in the API. This prefix is now stripped before parsing, fixing incorrect model strings (e.g. `"Model: TD-1"`) and broken MAC address extraction
- **DAM numeric ranges**: DAM capabilities express constraints as `range: [min, max, step]` or `ranges: [[min, max, step], ...]`. Number entities now extract min/max/step from both formats so sliders show correct limits
- **DAM entity type classification**: `SELECT` vs `NUMBER` detection now checks the DAM `range` field, preventing range-constrained numeric controls from being misclassified as select dropdowns
- **DAM constant sensor values**: DAM capabilities use `"value"` for constant readings; legacy uses `"default"`. Both keys are now checked

**IMPROVEMENTS:**
- **New Appliance Type: CR (Combined Refrigerator)**: Added full catalog support for the `CR` appliance type, backed by the existing refrigerator catalog. Model `925060324` (EHE6899BA) now has a dedicated model entry
- **Refrigerator Compartment Temperature Sensors**: Added `sensorTemperatureC` to all four compartments — `fridge`, `freezer`, `extraCavity`, `iceMaker` — for refrigerators that report per-compartment ambient temperature readings
- **Refrigerator Compressor Entities**: Added `compressorState` (binary running sensor) and `compressorSpeed` (RPM sensor) for refrigerators that expose compressor telemetry
- **Refrigerator Appliance State Device Class Fix**: `fridge/applianceState` and `freezer/applianceState` now use `BinarySensorDeviceClass.RUNNING` instead of the generic string sensor, matching the existing fix already applied to `extraCavity` and `iceMaker`
- **Tumble Dryer: 11 New Programs**: Eleven additional drying programs added to both `userSelections/programUID` and `cyclePersonalization/programUID` select entities
- **Tumble Dryer: Load Weight and Cycle Statistics Sensors**: Added `measuredLoadWeight` (grams), `totalDryCyclesCount` (diagnostic counter), and `totalDryingTime` (duration in seconds) — all enriched from device state since they are not reported in capabilities
- **Tumble Dryer: Save App Favourite Button**: Added `saveAppFavorite` button for dryers that support saving the current program as a favourite via the Electrolux app
- **Washer: 7 New EWX1493A Cycle Option Switches**: Added the full set of `userSelections/EWX1493A_*` switches present on models WM-914501128 and WM-914915144 that were previously missing from the catalog
- **Washer: Automatic Detergent Dispenser Sensors**: Added `fCMiscellaneousState/adTankADetLoaded`, `adTankBDetLoaded`, `adTankBSoftLoaded` (ml sensors for auto-dosing tanks) and `fCMiscellaneousState/ecoLevel` for washers equipped with automatic detergent dispensers

---

## Supported Appliances (as of v3.4.1)

The table below lists all appliance types and the known-tested diagnostic samples that have shaped the catalog. All appliance types in the **Full** column receive entity enrichment (device class, unit, icon, entity category). Types marked **Partial** have a catalog but may be missing entries for some models — submit your diagnostics to help close the gaps. **Stub** means the type code is registered but the catalog has no entries yet (requires user diagnostic samples to build from).

| Type | Appliance | Status | Known-Tested Samples / Models |
|------|-----------|--------|-------------------------------|
| `OV` | Oven | Full | Based on model `OV-944188772` |
| `SO` | Steam Oven | Full | Based on model `SO-944035035` |
| `RF` | Refrigerator | Partial | No diagnostic samples received yet — [submit yours](https://github.com/TTLucian/ha-electrolux/issues) |
| `CR` | Combined Refrigerator | Full ✨ *new* | Based on model `CR-925060324` |
| `WM` | Washing Machine | Full | Based on models `WM-EW7F3816DB`, `WM-914501128`, `WM-914915144` |
| `WD` | Washer-Dryer | Full | Based on models `WD-914611000`, `WD-914611500` |
| `TD` | Tumble Dryer | Full | Based on models `TD-916099949`, `TD-916098401`, `TD-916098618` |
| `AC` | Air Conditioner | Full | Based on model `AC-910280820` |
| `DW` | Dishwasher | Full | Based on models `DW-911434654`, `DW-911434834` |
| `A9` / `Muju` | Air Purifier | Full | A9 series; UltimateHome 500 (EP53) |
| `MW` | Microwave | Stub | No diagnostic samples received yet — [submit yours](https://github.com/TTLucian/ha-electrolux/issues) |

> Appliance types not listed above still have all their entities created dynamically from whatever the API reports in the device capabilities — no entities are suppressed. However, without a catalog entry they appear as generic sensors and controls with no device class, unit, icon, or friendly name. The base catalog (connectivity state, software version, network interface) applies to all appliance types regardless.

> ### 🧪 Please Test and Report Issues
>
> v3.4.1 includes a **large catalog expansion** across nearly every supported appliance type. Hundreds of new entities have been added for washing machines, washer-dryers, tumble dryers, dishwashers, refrigerators, steam ovens, and air purifiers — many driven by newly analysed diagnostic samples.
>
> Because the new entities cover capabilities not previously exercised, some may behave unexpectedly on your specific model (wrong entity type, unexpected values, unavailability, etc.).
>
> **Please test the new entities on your appliance and open a GitHub issue if anything looks wrong:**
>
> 1. After updating, check that your appliance entities load without errors in **Settings → Devices & Services → Electrolux**
> 2. Look for any entities that appear unavailable, show unexpected values, or have the wrong unit/device class
> 3. If you find a problem, [open a GitHub issue](https://github.com/TTLucian/ha-electrolux/issues) and attach your diagnostics (three-dot menu on your device → **Download diagnostics**)
>
> Your feedback directly shapes the quality of future catalog entries for every user.

---

## New: CR Appliance Type and EHE6899BA Model

### Background
The Electrolux API identifies fridge-freezer combo units as type `CR` (Combined Refrigerator). Previously this type code was not registered in the integration's type catalog, so any `CR` appliance would receive no entity enrichment — all entities would be created as generic sensors without device classes, units, or icons.

### Changes
- `CR` type is now mapped to the existing refrigerator catalog, sharing all enrichment definitions with the `RF` type
- Model `925060324` (EHE6899BA) is registered as a model override entry

### Effect
`CR` appliances now receive the full refrigerator catalog enrichment, including compartment temperature sensors, filter life time sensors, compressor entities, and appliance state binary sensors.

---

## New: Refrigerator Compartment Temperature Sensors

Added `sensorTemperatureC` entries for all four refrigerator compartments. These sensors represent the actual measured ambient temperature inside each cavity, distinct from the user-configured `targetTemperatureC`.

| Entity | Compartment | Device Class | Unit |
|--------|-------------|-------------|------|
| `fridge/sensorTemperatureC` | Main fridge | `SensorDeviceClass.TEMPERATURE` | °C |
| `freezer/sensorTemperatureC` | Freezer | `SensorDeviceClass.TEMPERATURE` | °C |
| `extraCavity/sensorTemperatureC` | Extra cavity | `SensorDeviceClass.TEMPERATURE` | °C |
| `iceMaker/sensorTemperatureC` | Ice maker | `SensorDeviceClass.TEMPERATURE` | °C |

---

## New: Refrigerator Compressor Entities

Two new catalog entries covering the compressor subsystem reported by some refrigerator models:

| Entity | Device Class | Unit | Category |
|--------|-------------|------|----------|
| `compressorState` | `BinarySensorDeviceClass.RUNNING` | — | — |
| `compressorSpeed` | — | `rpm` | Diagnostic |

---

## Fixed: Refrigerator Appliance State Device Class

`fridge/applianceState` and `freezer/applianceState` were configured as generic string sensors. They now use `BinarySensorDeviceClass.RUNNING`, consistent with the existing fix for `extraCavity` and `iceMaker` in v3.4.0.

| Entity | Before | After |
|--------|--------|-------|
| `fridge/applianceState` | `device_class=None` | `BinarySensorDeviceClass.RUNNING` |
| `freezer/applianceState` | `device_class=None` | `BinarySensorDeviceClass.RUNNING` |

---

## New: Tumble Dryer Programs

Eleven programs present in TD-916098401 and TD-916098618 samples were not in the dryer catalog. Two further programs were identified in TD-916099548_05. All are now added to both `userSelections/programUID` and `cyclePersonalization/programUID` select entities.

| Program UID | Friendly Name | Added From |
|------------|--------------|------------|
| `AUTO_EASY_IRON_PR_EASYIRON` | Easy Iron | TD-916098401/616098618 |
| `BED_LINEN_PLUS_PR_BEDDINGPLUS` | Bedding Plus | TD-916098401/916098618 |
| `COTTON_PR_ENERGYSAVER` | Cotton Energy Saver | TD-916098401/916098618 |
| `FLEECE_PR_FLEECE` | Fleece | TD-916098401/916098618 |
| `OUTD_PROOF_PR_PROOFINGTREATMENT` | Outdoor Proofing Treatment | TD-916098401/916098618 |
| `SHIRTS_PR_BUSINESSSHIRT` | Business Shirt | TD-916098401/916098618 |
| `SHOES_PR_RUNNINGSHOES` | Running Shoes | TD-916099548_05 |
| `SPORTS_PR_MICROFIBRE` | Sports Microfibre | TD-916098401/916098618 |
| `SPORTS_PR_SPORT` | Sports | TD-916098401/916098618 |
| `STEAM_REF_PR_STEAMREFRESH` | Steam Refresh | TD-916099548_05 |
| `UNIVERSAL_PR_MIXEDPLUS` | Mixed Plus | TD-916098401/916098618 |
| `UNIVERSAL_PR_MIXEDPLUSNOTXL` | Mixed Plus (Not XL) | TD-916098401/916098618 |
| `WORKINGCLOTHES_PR_WORKINGCLOTHES` | Working Clothes | TD-916098401/916098618 |

---

## New: Tumble Dryer Load and Statistics Sensors

Three state-reported sensors added for dryers that expose load and usage telemetry. These keys are present in the device's reported state but not in its capabilities list, so they are enriched via the catalog's state loop.

| Entity | Device Class | Unit | Category | Notes |
|--------|-------------|------|----------|-------|
| `measuredLoadWeight` | `SensorDeviceClass.WEIGHT` | g | — | Detected load weight for the current cycle |
| `totalDryingTime` | `SensorDeviceClass.DURATION` | s | Diagnostic | Cumulative drying time across all cycles; HA native unit conversion enabled |
| `totalDryCyclesCount` | — | — | Diagnostic | Total number of drying cycles completed |

---

## New: Tumble Dryer Save Favourite Button

Added `saveAppFavorite` button for dryers that expose the save-favourite command in their capabilities. Pressing the button saves the current program configuration as a favourite in the Electrolux app.

| Entity | Device Class | Icon |
|--------|-------------|------|
| `saveAppFavorite` | `ButtonDeviceClass.RESTART` | `mdi:star` |

---

## New: DWYW (Do What You Wash) Tumble Dryer Entities

The Electrolux DWYW feature allows a connected washer to automatically recommend a dryer program based on the completed wash load. Model TD-916099548_05 exposes the `dwywDataToDryer` container (washer-to-dryer load data) and `dwywSelect` container (pairing control).

These catalog entries provide enrichment for the state and program recommendation entities surfaced by the DWYW system.

| Entity | Type | Device Class | Unit | Category | Description |
|--------|------|-------------|------|----------|-------------|
| `dwywDataToDryer/programUID` | Select | — | — | — | DWYW-recommended dryer program |
| `dwywDataToDryer/wmLoadWeight` | Sensor | `WEIGHT` | g | — | Wash load weight reported by paired washer |
| `dwywDataToDryer/wmLoadMoisture` | Sensor | — | % | — | Residual moisture in wash load |
| `dwywDataToDryer/tdCloudTte` | Sensor | `DURATION` | min | — | Estimated drying time for this load |
| `dwywDataToDryer/tdEcpOverload` | Sensor | — | — | Diagnostic | Load overload flag from washer |
| `dwywDataToDryer/wmLoadError` | Sensor | — | — | Diagnostic | Wash load detection error code |
| `dwywSelect/wmSn` | Text | — | — | Config | Serial number of the paired washer |

---

## New: Washer EWX1493A Cycle Option Switches

Seven `userSelections/EWX1493A_*` switches present on WM-914501128 and WM-914915144 were missing from the washing machine catalog. Combined with the eight keys already registered in v3.4.0, the full set of 15 EWX1493A cycle options is now covered.

| Entity | Friendly Name | Icon |
|--------|--------------|------|
| `userSelections/EWX1493A_stain` | Stain Action | `mdi:sticker-remove` |
| `userSelections/EWX1493A_dryMode` | Dry Mode | `mdi:tumble-dryer` |
| `userSelections/EWX1493A_easyIron` | Easy Iron | `mdi:iron` |
| `userSelections/EWX1493A_pod` | Pod Wash | `mdi:cube-outline` |
| `userSelections/EWX1493A_steamMode` | Steam Mode | `mdi:weather-partly-cloudy` |
| `userSelections/EWX1493A_ultraMix` | Ultra Mix | `mdi:rotate-3d-variant` |
| `userSelections/EWX1493A_wetMode` | Wet Mode | `mdi:water` |

---

## New: Washer Automatic Detergent Dispenser Sensors

Models with an integrated automatic detergent dispenser report per-cycle and per-tank dosing data under `fCMiscellaneousState`. Four previously missing entries are now in the washer catalog.

| Entity | Friendly Name | Unit | Category |
|--------|--------------|------|----------|
| `fCMiscellaneousState/adTankADetLoaded` | Tank A Detergent Loaded | ml | Diagnostic |
| `fCMiscellaneousState/adTankBDetLoaded` | Tank B Detergent Loaded | ml | Diagnostic |
| `fCMiscellaneousState/adTankBSoftLoaded` | Tank B Softener Loaded | ml | Diagnostic |
| `fCMiscellaneousState/ecoLevel` | Eco Level | — | Diagnostic |

---

---

## Basic DAM Appliance Support

DAM (Data Analysis Module) is the next-generation Electrolux/AEG connectivity platform. DAM appliances were previously broken in the integration due to structural differences in how the API represents capabilities and device identity.

**How to identify a DAM appliance:** download your device diagnostics and look for an `applianceId` starting with `"1:"` or an `applianceType` starting with `"DAM_"`.

| Area | Status |
|------|--------|
| Device registration and identity (name, model, MAC) | ✅ Fixed |
| Entity creation from API capabilities | ✅ Works |
| Numeric control ranges (sliders, input boxes) | ✅ Fixed |
| Constant sensor values | ✅ Fixed |
| Commands to appliance | ✅ Already worked |
| Catalog enrichment (device class, unit, icon, friendly name) | ⚠️ Requires diagnostic JSON samples per appliance type |

---

## Files Changed

- `custom_components/electrolux/api.py` — DAM `range` field checked in `SELECT` vs `NUMBER` classification
- `custom_components/electrolux/entity.py` — Constant sensor value reads `"value"` key (DAM) in addition to `"default"` (legacy); DAM `1:` prefix stripped in device identity parsing
- `custom_components/electrolux/number.py` — New `_get_capability_constraint()` helper handles `range`/`ranges` array formats for min/max/step
- `custom_components/electrolux/models.py` — `DAM_` prefix stripped before catalog lookup
- `custom_components/electrolux/catalog_core.py` — Added `CR` type mapping; added model entry `925060324` (EHE6899BA)
- `custom_components/electrolux/catalog_refrigerator.py` — Fixed `fridge/applianceState` and `freezer/applianceState` device_class; added `sensorTemperatureC` for all four compartments; added `compressorState` and `compressorSpeed`
- `custom_components/electrolux/catalog_dryer.py` — 13 new programs in both programUID selects (11 from TD-916098401/616098618, 2 from TD-916099548_05); added `measuredLoadWeight`, `totalDryingTime`, `totalDryCyclesCount`, `saveAppFavorite`; added 7 DWYW entities under `dwywDataToDryer/*` and `dwywSelect/*`
- `custom_components/electrolux/catalog_washer.py` — 7 new `EWX1493A_*` cycle switches; 4 new `fCMiscellaneousState` sensors; added `applianceMode`, `applianceMainBoardSwVersion`, `applianceUiSwVersion`, `networkInterfaceAlwaysOn`, `remoteNotificationPending`, `minFinishInTime`, `autoDosing/adLocalFineTuning`, `clearCyclePersonalizationCmd`, `userSelections/memoryId`, and 10 `cyclePersonalization/*` entries
- `custom_components/electrolux/catalog_washer_dryer.py` — ~50 new entries: `applianceMode`, software version sensors, `networkInterfaceAlwaysOn`, `remoteNotificationPending`, `doorState`, `cycleSubPhase`, `minFinishInTime`, `fcOptisenseLoadWeight`, cycle statistics (totalDryCyclesCount, totalDryingTime, totalWashCyclesCount, totalWashDryCyclesCount, totalWashingTime), full `autoDosing/*` set, `fCMiscellaneousState` auto-dosing sub-fields, `clearCyclePersonalizationCmd`, 9 `cyclePersonalization/EWX1493A_*` switches, and 10 `cyclePersonalization/*` entries
- `custom_components/electrolux/catalog_dishwasher.py` — Added `applianceMode` and `miscellaneousState`; added `SensorDeviceClass` import
- `custom_components/electrolux/catalog_steam_oven.py` — Added `applianceLocalTimeOffset`, `autoLocalTimeOffset`, `favoriteOrder`, `favoriteOrder/number`, `favoriteSelect`, `favoriteStatus`, `favoriteStatus/number`, `messageQueueSync/activeMessageIndex`
- `custom_components/electrolux/catalog_dryer.py` — Added `dwywSelect/command`, `startTime`, `clearCyclePersonalizationCmd`, `userSelections/memoryId`, `cyclePersonalization/steamValue`, `shortcutProgListCmd`
- `custom_components/electrolux/catalog_refrigerator.py` — Added `compressorSpeed/coefficient` and `compressorSpeed/exponent`
- `custom_components/electrolux/catalog_purifier.py` — Added `SignalStrength` (EXCELLENT/GOOD/FAIR/WEAK)
