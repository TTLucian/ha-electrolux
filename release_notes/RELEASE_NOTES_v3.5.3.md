# Release Notes v3.5.3

## New Appliance Support

### Verbier — Air Purifier with Humidification

Added full support for the Verbier appliance type — an Electrolux air purifier with integrated humidification. This model was previously unrecognised by the integration and produced no entities.

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

**Why were these sensors missing before?**

The Electrolux cloud separates what an appliance *can do* (capabilities) from its *current readings* (reported state). Sensors like Temperature, Humidity, and air quality readings are pushed as reported state values but are not listed as capabilities — so the integration needs an explicit catalog entry to know what unit and device class to assign them. The Verbier appliance type was also not registered at all, so the integration had no catalog to consult even for the controls and filter sensors it does advertise as capabilities.


## Supported Appliances (as of v3.5.3):

| Type | Appliance | Status | Verified Samples |
|------|-----------|--------|-----------------|
| `OV` | Oven | Full | OV-944188772 |
| `SO` | Steam Oven | Full | SO-944035035 |
| `RF` | Refrigerator | Partial | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |
| `CR` | Combined Refrigerator | Full | CR-925060324 |
| `WM` | Washing Machine | Full | WM-914501128, WM-914915144 |
| `WD` | Washer-Dryer | Full | WD-914611000, WD-914611500 |
| `TD` | Tumble Dryer | Full | TD-916098401, TD-916098618, TD-916099548, TD-916099949, TD-916099971 |
| `AC` | Air Conditioner | Full | AC-910280820 |
| `DW` | Dishwasher | Full | DW-911434654, DW-911434834 |
| `A9` / `Muju` / `Verbier` | Air Purifier | Full | A9 series; UltimateHome 500 (EP53) |
| `MW` | Microwave | Stub | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |