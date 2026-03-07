# Release Notes v3.5.6

## New Features

### Expanded appliance support — 17 new type codes catalogued

Using the SDK's built-in appliance configuration as the authoritative source of API key
mappings, four new catalog files were created and the type-code registry was extended from
12 to 29 supported appliance types. Appliances of these types will now have their
capabilities matched against a rich entity catalog instead of falling back to the generic
auto-discovery mode.

> **⚠️ SDK note:** The catalog entries for new appliance types were derived from
> `electrolux-group-developer-sdk` v0.3.0, which is under active, early development.
> Key names and appliance constants may change between SDK releases. If entities stop
> appearing or commands break after a package update, the SDK may have changed its
> internal mappings — please open an issue.

---

#### Dehumidifier (DH, Husky) — new `catalog_dh.py`

| Capability key | Entity | Notes |
|---|---|---|
| `executeCommand` | Power (button) | ON / OFF |
| `sensorHumidity` | Humidity (sensor) | Current ambient humidity % |
| `targetHumidity` | Target Humidity (number) | Setpoint — range / step read from device |
| `fanSpeedSetting` | Fan Speed (select) | ⚠️ values unverified — read from device capabilities at runtime |
| `mode` | Mode (select) | ⚠️ values unverified — read from device capabilities at runtime |

> **⚠️ `fanSpeedSetting` and `mode` values unverified.**
> The SDK reads these values dynamically from device capabilities rather than defining them statically.
> Placeholder values in the catalog will be replaced by whatever the device actually reports.
> If your dehumidifier shows incorrect options, please [submit a diagnostic](https://github.com/TTLucian/ha-electrolux/issues).

---

#### Robot Vacuum (PUREi9, Gordias, Cybele, 700series) — new `catalog_rvc.py`

Both the older PUREi9 API (integer `robotStatus`, `CleaningCommand`) and the newer
Gordias/Cybele/700series API (string `state`, `cleaningCommand`, `chargingStatus`) are
covered by a single catalog; each device exposes only its own subset of capabilities.

| Capability key | Entity | Notes |
|---|---|---|
| `batteryStatus` | Battery (sensor) | % — common to all robot vacuum models |
| `robotStatus` | Robot Status (sensor) | PUREi9 only — integer 1-14 with human-readable labels |
| `CleaningCommand` | Cleaning Command (select) | PUREi9: play / stop / pause / home |
| `powerMode` | Power Mode (select) | PUREi9: QUIET / SMART / POWER |
| `state` | Cleaning State (sensor) | Gordias/Cybele/700series: string state |
| `chargingStatus` | Charging Status (sensor) | Gordias/Cybele/700series |
| `cleaningCommand` | Cleaning Command (select) | Gordias/Cybele/700series: start / stop / pause / resume / dock |
| `vacuumMode` | Vacuum Mode (select) | Gordias/Cybele/700series — ⚠️ values unverified, see note below |

> **⚠️ `vacuumMode` values unverified for Gordias/Cybele/700series.**
> The catalog currently lists `QUIET / SMART / POWER` (from the SDK). The Electrolux API docs
> describe `quiet / energySaving / standard / powerful` (Gordias) and
> `quiet / energySaving / standard / powerful / max` (Cybele) in the per-room cleaning command.
> Whether the global `vacuumMode` capability uses the same casing and set of values cannot be
> confirmed without a real diagnostic JSON. If your Gordias or Cybele shows incorrect vacuum mode
> options, please [submit a diagnostic](https://github.com/TTLucian/ha-electrolux/issues).

---

#### Induction Hob (HB) — new `catalog_hb.py`

| Capability key | Entity | Notes |
|---|---|---|
| `applianceMode` | Appliance Mode (select) | Top-level operating mode |
| `childLock` | Child Lock (switch) | |
| `keySoundTone` | Key Sound (switch) | |
| `windowNotification` | Window Notification (switch) | |
| `hobHood/hobToHoodFanSpeed` | Hood Fan Speed (select) | Nested under `hobHood` — ⚠️ values unverified, replaced by device capabilities at runtime |
| `hobHood/hobToHoodState` | Hood State (select) | Nested under `hobHood` — ⚠️ values unverified, replaced by device capabilities at runtime |

---

#### Hood / Extractor Fan (HD) — new `catalog_hd.py`

| Capability key | Entity | Notes |
|---|---|---|
| `hoodFanLevel` | Fan Level (select) | ⚠️ values unverified — replaced by device capabilities at runtime |
| `lightIntensity` | Light Intensity (number) | ⚠️ range unverified — replaced by device capabilities at runtime |
| `lightColorTemperature` | Light Colour Temperature (number) | ⚠️ range unverified — replaced by device capabilities at runtime |
| `hoodCharcFilterTimer` | Charcoal Filter Timer (sensor) | Hours until service |
| `hoodGreaseFilterTimer` | Grease Filter Timer (sensor) | Hours until service |
| `tvocFilterTime` | TVOC Filter Time (sensor) | Hours remaining |
| `hoodFilterCharcEnable` | Charcoal Filter Enable (switch) | |
| `drawerStatus` | Drawer (binary sensor) | OPEN / CLOSED |
| `humanCentricLightEventState` | Human-Centric Light (binary sensor) | |
| `hoodAutoSwitchOffEvent` | Auto Switch-Off (binary sensor) | |
| `applianceMode` | Appliance Mode (select) | |
| `soundVolume` | Sound Volume (number) | 0–100 % |
| `targetDuration` | Target Duration (number) | Countdown timer — seconds |

---

### Additional AC and AP variant type codes registered

All AC and AP variant type codes that the SDK defines are now mapped to their respective
catalogs, so these appliances are catalogued from first connection rather than relying on
generic auto-discovery:

| New type codes | Catalog used |
|---|---|
| `CA`, `Azul`, `Bogong`, `Panther`, `Telica` | Air Conditioner |
| `PUREA9`, `Fuji`, `WELLA5`, `WELLA7` | Air Purifier |

---

## Supported Appliances (as of v3.5.6)

| Type | Appliance | Status | Known-Tested Samples |
|------|-----------|--------|----------------------|
| `OV` | Oven | Full | OV-944188772 |
| `SO` | Structured Oven | Full | SO-944035035 |
| `CR` | Combi Refrigerator | Full | CR-925060324 |
| `WM` | Washing Machine | Full | WM-914501128, WM-914915144 |
| `WD` | Washer Dryer | Full | WD-914611000, WD-914611500 |
| `TD` | Tumble Dryer | Full | TD-916098401, TD-916098618, TD-916099548, TD-916099949, TD-916099971 |
| `AC` / `CA` / `Azul` / `Bogong` / `Panther` / `Telica` | Air Conditioner | Full (`AC` verified) | AC-910280820 — CA/Azul/Bogong/Panther/Telica unverified |
| `DAM_AC` | DAM Air Conditioner | Catalog *(unverified)* | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |
| `DW` | Dishwasher | Full | DW-911434654, DW-911434834 |
| `Muju` / `Verbier` / `PUREA9` / `Fuji` / `WELLA5` / `WELLA7` | Air Purifier | Full (Muju/Verbier verified) | UltimateHome 500 (EP53); Verbier — PUREA9/Fuji/WELLA5/WELLA7 unverified |
| `DH` / `Husky` | Dehumidifier | Catalog *(unverified)* | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |
| `PUREi9` / `Gordias` / `Cybele` / `700series` | Robot Vacuum | Catalog *(unverified)* | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |
| `HB` | Induction Hob | Catalog *(unverified)* | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |
| `HD` | Hood / Extractor Fan | Catalog *(unverified)* | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |
| `MW` | Microwave | Stub | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |

### 🔬 Diagnostics wanted — help verify new appliance types

The catalog entries for the appliance types listed as *unverified* above were built from the
Electrolux SDK's internal API mappings. Capability key names are correct per the SDK, but
value ranges, available modes, and model-specific differences can only be confirmed with a
real diagnostic JSON file.

If you own one of these appliances, please download your diagnostics from
**Settings → Devices & Services → Electrolux → three-dot menu → Download diagnostics**
and [open a GitHub issue - Feature request](https://github.com/TTLucian/ha-electrolux/issues) with the file
attached. This is the single most impactful contribution you can make — a diagnostic file
takes 30 seconds to generate and enables full verified support for your appliance type.

| Appliance | Issue title to use |
|-----------|-------------------|
| 🌊 **Dehumidifier** (DH, Husky) | `DH diagnostics — [your model]` |
| 🤖 **Robot Vacuum** (PUREi9, Gordias, Cybele, 700series) | `RVC diagnostics — [your model]` |
| 🍳 **Induction Hob** (HB) | `HB diagnostics — [your model]` |
| 💨 **Hood / Extractor Fan** (HD) | `HD diagnostics — [your model]` |
| ❄️ **DAM Air Conditioner** (DAM_AC) | `DAM_AC diagnostics — [your model]` |
| ❄️ **AC variants** (CA, Azul, Bogong, Panther, Telica) | `AC variant diagnostics — [your type/model]` |
| 💨 **AP variants** (PUREA9, Fuji, WELLA5, WELLA7) | `AP variant diagnostics — [your type/model]` |

---

### DAM_AC — dedicated catalog (bug fix)

**Previous behaviour:** `DAM_AC` appliances had the `DAM_` prefix stripped before catalog
lookup, so they were matched against the standard `AC` catalog. None of the `AC` catalog
keys exist in the DAM_AC API — all controls are nested under the `airConditioner/`
sub-object — so a DAM_AC device produced zero recognised entities.

**Fix:** A dedicated `catalog_dam_ac.py` was created and `DAM_AC` is now registered as its
own type code. The `DAM_` prefix stripping in `models.py` has been removed.

| Capability key | Entity | Notes |
|---|---|---|
| `temperature` | Ambient Temperature (sensor) | Root level (not nested) |
| `airConditioner/applianceState` | State (sensor) | Nested |
| `airConditioner/executeCommand` | Power (select) | on / off |
| `airConditioner/targetTemperature` | Target Temperature (number) | ⚠️ range unverified — replaced by device capabilities at runtime |
| `airConditioner/mode` | Mode (select) | ⚠️ values unverified — replaced by device capabilities at runtime |
| `airConditioner/fanMode` | Fan Mode (select) | ⚠️ values unverified — replaced by device capabilities at runtime |

---

### Air Purifier — Temperature, Humidity and eCO₂ sensors missing (bug fix)

**Affected appliances:** All air purifier variants — `Verbier`, `Muju`, `PUREA9`, `Fuji`, `WELLA5`, `WELLA7`.

**Symptom:** After integrating a Verbier (or any air purifier variant), the Temperature, Humidity
and eCO₂ sensors were never created in Home Assistant, even when the values were present in the
appliance's live state.

**Root cause — integration read `applianceType` from the wrong place.**
The Electrolux API provides `applianceType` in the **appliances list** (`"applianceType": "Verbier"`).
This field is present and correct for every appliance type without exception.

Many appliances — washers, dryers, ovens — *additionally* embed the same value
deep inside their live telemetry at
`appliances_detail[id].state.properties.reported.applianceInfo.applianceType`.
The integration was reading only from that second, optional location. Air purifiers never include
`applianceInfo` in their reported state, so for those appliances `applianceType` always resolved
to `None`.

With no appliance type, the per-type catalog lookup was skipped entirely. The purifier catalog
contains the definitions for `Temp`, `Humidity`, and `ECO2` — sensors that the hardware *does*
report but that are not advertised in the API capabilities — so those entities were never created.


**Fix:** The appliance type is now read from the appliances list at setup time and stored
directly on the `Appliance` object. The reported-state fallback is kept for backward compatibility
but is no longer the primary source.

---

### `userSelections` commands fail with HTTP 500 on legacy appliances (bug fix)

**Affected appliances:** All **legacy** (non-DAM) appliances with `userSelections` sub-properties —
confirmed on Tumble Dryer `TD-916099971`, affects any washer, dryer, or similar appliance with
controls like `antiCreaseValue`, `humidityTarget`, `dryingTime`, etc.

**Symptom:** Changing a `userSelections` entity in Home Assistant (e.g. Anti-Crease duration)
caused an immediate HTTP 500 error from the Electrolux API. The appliance itself was unaffected; the
command was simply rejected.

**Root cause — `programUID` was missing from the command payload.**
The [Electrolux API](https://developer.electrolux.one/documentation/reference) requires that any
write to a `userSelections` sub-property include the `programUID` alongside the changed property:

```json
{
    "userSelections": {
        "programUID": "COTTON_PR_COTTONSECO",
        "antiCreaseValue": 120
    }
}
```

The DAM path already handled this correctly. The legacy path in all four writable entity types
(`number`, `select`, `switch`, `text`) sent the command **without** `programUID`:

```json
{ "userSelections": { "antiCreaseValue": 120 } }   ← HTTP 500
```

**Fix:** The legacy command path in `number.py`, `select.py`, `switch.py`, and `text.py` now reads
`programUID` from the appliance's current reported state and includes it in every `userSelections`
command. If `programUID` is unavailable the command falls back to the old format (no regression for
appliances that do not use `programUID`).


