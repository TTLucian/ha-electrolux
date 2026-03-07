# Release Notes v3.5.3

## New Appliance Support

### Verbier — Air Purifier with Humidification

Added full support for the Verbier appliance type — an Electrolux air purifier with integrated humidification. Previously, this appliance type had no catalog entry: controls and filter sensors were created as generic unnamed entities with no device class, unit, or icon, and air quality sensors (Temperature, Humidity, PM1, PM2.5, PM10, TVOC, eCO2) were missing entirely because they only appear in the device's reported state and not in its capabilities.

**Sensors created:**

| Entity | Description |
|--------|-------------|
| Temperature | Ambient temperature (°C) |
| Humidity | Ambient relative humidity (%) |
| PM1 / PM2.5 / PM10 | Particulate matter concentrations (µg/m³) |
| TVOC | Total volatile organic compounds (ppb) |
| eCO2 | Equivalent CO₂ concentration (ppm) |
| Filter Life / Filter Life 2 | Remaining filter life (%) |
| Filter Type / Filter Type 2 | Installed filter type (enum) |
| Filter 1 / Filter 2 NFC Tag UID | Filter NFC tag identifiers |
| Humidification Filter Reset Date | Date the humidification filter was last reset |
| Water Tray Level Low | Binary alert when water tray needs refilling |
| Signal Strength | Wi-Fi signal quality |
| Scheduling State | Active schedule state |

**Controls:**

| Entity | Description |
|--------|-------------|
| Air Purifier (fan) | Unified fan control — on/off, speed, preset modes |
| Fan Speed | Raw fan speed (1–5) |
| Work Mode | Manual / Auto / PowerOff |
| Humidification | Enable/disable humidification |
| Target Humidity | Humidity setpoint (40–60%, step 10%) |
| Louver Swing | Airflow direction (off / narrow / wide / natural breeze) |
| Quiet Fan | Quiet fan schedule (off / on / when dark) |
| AQI Light | AQI indicator light mode (off / on / ambient) |
| Ionizer | Enable/disable ionizer |
| Safety Lock | Child lock |

**Diagnostics:**

Full set of error sensors (`ErrGasNotResp`, `ErrTempRhNotResp`, `ErrWaterTrayRemoved`, NFC tag errors, etc.) exposed as diagnostic entities.

---

## Bug Fixes

### Fan entity now works correctly for all air purifiers (A9 / Muju / Verbier) ⚠️ Needs testing

**⚠️ Testing requested:** These fixes correct the underlying wiring but have only been verified in automated unit tests — not on real hardware. If you own an A9, Muju, or Verbier purifier, please test the fan entity and report any issues.

The **Air Purifier** fan entity (on/off, speed control, preset modes) was silently broken for all purifier models. The entity appeared in Home Assistant but every command — turn on, turn off, set speed, set preset — was a no-op with an error logged in debug output. Two bugs were found and fixed:

1. **`get_capability()` always returned `None`** — The method was reading capabilities from the wrong place (`appliance_status`), which only holds reported state and connectivity info. It now correctly reads from the appliance's capabilities dict populated during setup.

   *Effect:* Without a valid capability object, `_send_workmode_command()` and `_set_percentage()` both logged an error and returned immediately.

2. **Fan entity not created when appliance was off at setup** — The catalog loop only created the `Workmode/fan` entity if `Workmode` was already present in the reported state. If the purifier was powered off or freshly added, `Workmode` wouldn't be reported yet and the fan entity was never registered in Home Assistant.

   *Effect:* Users who set up the integration while their purifier was off had no fan entity at all until the next restart with the purifier running.

**What works now:**

| Action | Expected behaviour |
|--------|--------------------|
| Turn on | Sets `Workmode` to last active mode (`Manual` if unknown) |
| Turn off | Sets `Workmode` to `PowerOff` |
| Set speed % | Converts percentage to `Fanspeed` value (1–9 for A9, 1–5 for Muju/Verbier) |
| Set preset | Sets `Workmode` to selected mode |
| Preset modes | A9: Manual, Auto — Muju: Manual, Auto, Quiet — Verbier: Manual, Auto |
| Speed levels | A9: 9 levels — Muju: 5 levels — Verbier: 5 levels |


---

**Why were these sensors missing before?**

The Electrolux cloud separates what an appliance *can do* (capabilities) from its *current readings* (reported state). Sensors like Temperature, Humidity, and air quality readings are pushed as reported state values but are not listed as capabilities — so the integration needs an explicit catalog entry to know what unit and device class to assign them. The Verbier appliance type was also not registered at all, so the integration had no catalog to consult even for the controls and filter sensors it does advertise as capabilities.


## Supported Appliances (as of v3.5.3):

| Type | Appliance | Status | Verified Samples |
|------|-----------|--------|-----------------|
| `OV` | Oven | Full | OV-944188772 |
| `SO` | Structured Oven | Full | SO-944035035 |
| `RF` | Refrigerator | Partial | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |
| `CR` | Combi Refrigerator | Full | CR-925060324 |
| `WM` | Washing Machine | Full | WM-914501128, WM-914915144 |
| `WD` | Washer Dryer | Full | WD-914611000, WD-914611500 |
| `TD` | Tumble Dryer | Full | TD-916098401, TD-916098618, TD-916099548, TD-916099949, TD-916099971 |
| `AC` | Air Conditioner | Full | AC-910280820 |
| `DW` | Dishwasher | Full | DW-911434654, DW-911434834 |
| `A9` / `Muju` / `Verbier` | Air Purifier | Full | A9 series; UltimateHome 500 (EP53) |
| `MW` | Microwave | Stub | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |