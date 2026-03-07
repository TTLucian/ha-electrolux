# Release Notes v3.4.0

> ### 📋 Help Improve Entity Catalog Quality
>
> The integration builds its entity catalog from real device diagnostic data. Every Electrolux appliance model exposes a different set of capabilities, and without your diagnostics the catalog can only be as accurate as the samples already on hand.
>
> **If you want better entity types, units, icons, and device classes for your appliance — please share your diagnostics:**
>
> 1. Go to **Settings → Devices & Services → Electrolux**
> 2. Click the three-dot menu on your device → **Download diagnostics**
> 3. Open a [GitHub issue](https://github.com/TTLucian/ha-electrolux/issues) and attach the downloaded JSON file
>
> This is especially valuable for appliance types with limited samples: dryers, tumble dryers, refrigerators, air conditioners, and any other type

## Overview
v3.4.0 is an entity quality improvement release that corrects missing or incorrect `device_class` and `unit` configurations across multiple appliance catalogs. These fixes enable Home Assistant's native unit conversion UI, proper entity typing, and better integration with HA's statistics and display systems. The oven and steam oven catalogs now include both Celsius and Fahrenheit temperature controls — the runtime entity creation logic ensures only the controls present in the actual device's capabilities are instantiated. The AC climate entity temperature unit is now determined once from device capabilities at startup, eliminating fractional display artifacts caused by double-conversion when HA system units differ from the device's `temperatureRepresentation` setting.

**IMPROVEMENTS:**
- **Filter Life Time Sensors**: Added `SensorDeviceClass.DURATION` and `UnitOfTime.SECONDS` to all filter life time entities across refrigerators, air conditioners, and air purifiers — enabling HA native unit conversion (seconds → minutes → hours → days)
- **AC Climate Temperature Unit**: Climate entity temperature unit is now determined once from device capabilities at startup (`targetTemperatureC` → °C, `targetTemperatureF` → °F). Previously it was derived from the runtime `temperatureRepresentation` state attribute, causing HA to double-convert temperatures and display fractional values like `22.2°C` when the device was switched to Fahrenheit while HA remained in Celsius
- **Oven Temperature Controls (C and F)**: Both Celsius and Fahrenheit target temperature controls are present in the oven and steam oven catalogs. The integration creates only the entities present in the actual device's capabilities — so EU devices with only `targetTemperatureC` get a Celsius slider, US devices with only `targetTemperatureF` get a Fahrenheit slider, and devices supporting both get both controls
- **Humidity Sensors**: Added proper device classes to `ambientHumidity` (`SensorDeviceClass.HUMIDITY`) and `targetHumidity` (`NumberDeviceClass.HUMIDITY`) in the air conditioner catalog
- **Binary State Sensors**: Extra Cavity and Ice Maker appliance/fan state entities changed to `BinarySensorDeviceClass.RUNNING` for proper on/off display
- **Water Volume Sensors**: Added `SensorDeviceClass.WATER` to water filter flow entities in the refrigerator catalog
- **Improved SSE Debug Logging**: SSE messages now log the full raw JSON payload instead of formatted key=value strings
- **Food Probe Sensors Persist When Probe Disconnected**: `displayFoodProbeTemperatureC` and `displayFoodProbeTemperatureF` no longer disappear from the UI when the food probe is physically unplugged — they remain as entities showing `unknown`. Only created on ovens that actually have food probe hardware (detected via `foodProbeInsertionState` capability, with fallback detection for older models)
- **Washer Capability Key Names Corrected (EWX1493A_ prefix)**: Several washer (`WM`/`WD`) capability keys were registered without their firmware-defined `EWX1493A_` platform prefix. The correct key names — as they appear in real device capability data — are now used. No breakage was ever reported, but entities that relied on the old names will be re-created with the corrected IDs. **WM/WD users: please check your dashboards and automations after updating.** If anything broke, open an issue and attach your diagnostics JSON.

---

## Fixed: Filter Life Time Sensor Units

### Problem
Filter life time sensors (water filter, air filter, HEPA filter) across multiple appliance types were missing `device_class` and `unit` configuration, preventing Home Assistant from offering unit conversion options in the UI. Users could not convert displayed values from seconds to minutes, hours, or days.

Notably, the corresponding *threshold* entities (e.g. `waterFilterLifeTimeBuyThreshold`) were already correctly configured — only the actual life time values were missing configuration.

### Affected Entities

| Entity | Appliance | Before | After |
|--------|-----------|--------|-------|
| `waterFilterLifeTime` | Refrigerator | `device_class=None, unit=None` | `device_class=DURATION, unit=SECONDS` |
| `airFilterLifeTime` | Refrigerator | `device_class=None, unit=None` | `device_class=DURATION, unit=SECONDS` |
| `airFilterLifeTime` | Air Conditioner | `device_class=None, unit=None` | `device_class=DURATION, unit=SECONDS` |
| `hepaFilterLifeTime` | Air Conditioner | `device_class=None, unit=None` | `device_class=DURATION, unit=SECONDS` |
| `UVRuntime` | Air Purifier | `unit="s"` (string) | `unit=UnitOfTime.SECONDS` (constant) |

### Effect
After this fix, users can click on any filter life time entity in the Home Assistant UI and select their preferred time unit display (seconds, minutes, hours, or days). Values will be automatically converted and formatted by HA.

---

## Fixed: Oven and Structured Oven Fahrenheit Temperature Controls

### How Oven Temperature Controls Work
The appliance catalog defines **all possible entities** an appliance type might have across all regional variants. At runtime, the integration only creates entities that are present in the device's reported capabilities — so the correct set of controls is created automatically for each device.

This means:
- **EU devices** — if only `targetTemperatureC` and `targetFoodProbeTemperatureC` are in capabilities, only Celsius controls are created
- **US devices** — if only `targetTemperatureF` and `targetFoodProbeTemperatureF` are in capabilities, only Fahrenheit controls are created  
- **Dual-unit devices** — if both C and F are in capabilities, both controls are created

### Entities (Created When Present in Device Capabilities)

| Entity | Catalog | Unit |
|--------|---------|------|
| `targetTemperatureC` | Oven | °C |
| `targetTemperatureF` | Oven | °F |
| `targetFoodProbeTemperatureC` | Oven | °C |
| `targetFoodProbeTemperatureF` | Oven | °F |
| `upperOven/targetTemperatureC` | Structured Oven | °C |
| `upperOven/targetTemperatureF` | Structured Oven | °F |
| `upperOven/targetFoodProbeTemperatureC` | Structured Oven | °C |
| `upperOven/targetFoodProbeTemperatureF` | Structured Oven | °F |

---

## Fixed: Humidity Sensor Device Classes (Air Conditioner)

The air conditioner catalog's humidity entities were missing proper device classes, causing them to appear as generic numeric sensors without humidity-specific UI handling.

| Entity | Before | After |
|--------|--------|-------|
| `ambientHumidity` | `device_class=None` | `device_class=SensorDeviceClass.HUMIDITY` |
| `targetHumidity` | `device_class=None` | `device_class=NumberDeviceClass.HUMIDITY` |

---

## Fixed: Binary State Sensors (Refrigerator)

Several refrigerator entities with two-state values (`OFF`/`RUNNING`, `OFF`/`ON`) were configured as generic string sensors. They now use `BinarySensorDeviceClass.RUNNING` so Home Assistant displays them correctly as binary on/off states.

| Entity | Before | After |
|--------|--------|-------|
| `extraCavity/applianceState` | `device_class=None` | `BinarySensorDeviceClass.RUNNING` |
| `extraCavity/fanState` | `device_class=None` | `BinarySensorDeviceClass.RUNNING` |
| `iceMaker/applianceState` | `device_class=None` | `BinarySensorDeviceClass.RUNNING` |

---

## Fixed: Water Volume Sensor Device Classes (Refrigerator)

Water filter flow entities were missing `SensorDeviceClass.WATER`, causing them to appear as generic numeric sensors.

| Entity | Before | After |
|--------|--------|-------|
| `waterFilterFlow` | `device_class=None` | `SensorDeviceClass.WATER` |
| `waterFilterFlowBuyThreshold` | `device_class=None` | `SensorDeviceClass.WATER` |
| `waterFilterFlowChangeThreshold` | `device_class=None` | `SensorDeviceClass.WATER` |

---

## Improved: SSE Debug Logging

SSE update log messages now include the full raw JSON payload received from the Electrolux API, making it easier to diagnose SSE-related issues in HA logs.

**Before:**
```
SSE update received for <id>: (incremental: targetTemperatureC = 200.0)
SSE duplicate (unchanged) for <id>: targetTemperatureC = 200.0 (unchanged)
```

**After:**
```
SSE update received for <id>: {"applianceId": "...", "property": "targetTemperatureC", "value": 200.0}
SSE duplicate (unchanged) for <id>: {"applianceId": "...", "property": "targetTemperatureC", "value": 200.0}
```

To see these messages, set the integration log level to `debug` in `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.electrolux: debug
```

---

## AC Climate Entity Temperature Unit

### Problem
Users reported that the climate entity displayed fractional Celsius values (e.g. `22.2°C`) when Home Assistant was configured to use Celsius but the device's `temperatureRepresentation` was set to Fahrenheit.

The root cause: HA's `ClimateEntity.temperature_unit` is a **data contract** — it tells HA the unit of the numbers being provided. When `temperature_unit` returned `°F` (because `temperatureRepresentation` was `FAHRENHEIT`), HA correctly converted the `73°F` value to display in Celsius — producing `22.8°C`. This double-conversion was mathematically correct but fractional and unexpected.

### Root Cause
The previous implementation read `temperatureRepresentation` from the device's live state on every property access and returned that as `temperature_unit`. This caused unit flips at runtime whenever the user changed which unit was displayed on the physical AC panel — forcing HA to re-convert already-correct values.

### Fix
The temperature unit is now determined **once at entity startup** by inspecting the device's static capabilities dict:

| Capabilities contain | `temperature_unit` set to | Temperature properties used |
|---|---|---|
| `targetTemperatureC` | `°C` | `ambientTemperatureC`, `targetTemperatureC` |
| Only `targetTemperatureF` | `°F` | `ambientTemperatureF`, `targetTemperatureF` |
| Neither | `°C` (default) | `ambientTemperatureC`, `targetTemperatureC` |

`temperatureRepresentation` still functions normally — it controls the physical display on the AC unit's panel. The climate entity simply no longer uses it to decide its own unit of measure.

### Effect
| Scenario | Before | After |
|---|---|---|
| HA=°C, device supports C | `22°C` ✅ | `22°C` ✅ |
| HA=°C, `tempRep`=FAHRENHEIT | `22.2°C` ❌ | `22°C` ✅ |
| HA=°F, device supports C | `72°F` ✅ | `72°F` ✅ |
| HA=°C, F-only device (US) | broken ❌ | `22°C` ✅ (HA converts) |

---

## Fixed: Washer Capability Key Names (EWX1493A_ Platform Prefix)

### Background
Electrolux washer firmware embeds a platform code (`EWX1493A_`) in the names of certain capability keys — specifically the `userSelections` sub-keys and the Pre-Wash option. Cross-referencing three independent washer device samples (`WM-EW7F3816DB`, `WD-914611000`, `WD-914611500`) confirmed that every sample consistently uses the `EWX1493A_` prefix. The catalog previously registered these keys without the prefix, meaning the integration was watching for keys that the device never actually reports.

### Corrected Keys

| Old Key (incorrect) | New Key (correct) |
|---|---|
| `preWashPhase` | `userSelections/EWX1493A_preWashPhase` |
| `userSelections/anticreaseNoSteam` | `userSelections/EWX1493A_anticreaseNoSteam` |
| `userSelections/anticreaseWSteam` | `userSelections/EWX1493A_anticreaseWSteam` |
| `userSelections/nightCycle` | `userSelections/EWX1493A_nightCycle` |
| `userSelections/wmEconomy` | `userSelections/EWX1493A_wmEconomy` |
| `userSelections/rinseHold` | `userSelections/EWX1493A_rinseHold` |
| `userSelections/intensive` | `userSelections/EWX1493A_intensive` |
| `userSelections/tcSensor` | `userSelections/EWX1493A_tcSensor` |

> **⚠️ WM/WD users — please verify after updating**
>
> No users have reported breakage related to these entities, which may mean they were silently producing no data with the old key names. After updating, check whether these entities now appear and report correct values. If anything unexpectedly broke on your washer or washer dryer, please open a GitHub issue and upload your diagnostics JSON (Settings → Devices & Services → Electrolux → three-dot menu → Download diagnostics).

---

## Fixed: Food Probe Display Sensors Disappearing When Probe Disconnected

### Problem
When a food probe is physically disconnected from the oven, the API stops reporting `displayFoodProbeTemperatureC` and `displayFoodProbeTemperatureF` in the device's reported state. The integration's entity creation logic treats absence from reported state as "entity doesn't exist" and skips creating those entities — so the food probe temperature sensors would vanish entirely from Home Assistant when the probe was unplugged.

### Fix
The two food probe display sensors are now kept alive on probe-equipped ovens even when the probe is disconnected. They remain as entities and show `unknown` until the probe is reinserted and the API starts reporting values again.

Food probe hardware presence is detected via:
1. **Primary**: `foodProbeInsertionState` in device capabilities — the definitive hardware-presence indicator, only advertised by ovens with a physical probe slot
2. **Fallback**: any of `targetFoodProbeTemperatureC`, `targetFoodProbeTemperatureF`, `displayFoodProbeTemperatureC`, `displayFoodProbeTemperatureF` in capabilities — covers older appliance generations

Ovens without food probe hardware are unaffected — the sensors are not created at all on those models.

### Entities Affected

| Entity | Behavior |
|---|---|
| `displayFoodProbeTemperatureC` | Persists as `unknown` when probe disconnected (probe-equipped ovens only) |
| `displayFoodProbeTemperatureF` | Persists as `unknown` when probe disconnected (probe-equipped ovens only) |

---

## Files Changed

- `custom_components/electrolux/catalog_refrigerator.py` — Filter life time units, binary state sensors, water volume device classes
- `custom_components/electrolux/catalog_air_conditioner.py` — Filter life time units, humidity device classes
- `custom_components/electrolux/catalog_purifier.py` — UV runtime unit constant
- `custom_components/electrolux/catalog_oven.py` — Both C and F target temperature controls present; runtime filters by device capabilities
- `custom_components/electrolux/catalog_steam_oven.py` — Both C and F target temperature controls present; runtime filters by device capabilities
- `custom_components/electrolux/climate.py` — Temperature unit determined from capabilities at startup; removed runtime `temperatureRepresentation` dependency
- `custom_components/electrolux/coordinator.py` — Improved SSE debug logging
- `custom_components/electrolux/catalog_washer.py` — Corrected `EWX1493A_` platform prefix on 8 capability keys; removed 3 keys that belonged to other appliance types
- `custom_components/electrolux/models.py` — Food probe display sensors persist when probe disconnected; food probe hardware detection via `foodProbeInsertionState`
