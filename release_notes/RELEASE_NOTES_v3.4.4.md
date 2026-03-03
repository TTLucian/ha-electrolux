## Overview

v3.4.4 is a bug-fix release targeting two regressions reported by dryer users.

---

**BUG FIXES:**

- **Anti-crease (and other stepped controls) returning HTTP 500**: Setting `Anti-Crease Duration` or any other dryer control with a step value other than 1 (e.g. step=30 for anti-crease, step=10 for drying time) was failing with `INTERNAL_SERVER_ERROR` from the Electrolux API. The integration was sending the value as a float (e.g. `90.0`) instead of an integer (`90`) — the API rejects floats for integer-stepped fields. Fixed: values are now converted to `int` whenever the value is a whole number and the step has no fractional part. Affected appliances: TD / WM / WD (non-DAM models).

- **Duplicate "Appliance care and maintenance" entities**: After a previous update, up to 30+ internal maintenance counter entities (e.g. `Appliance care and maintenance 0 maint 1 ID`, `maint 2 threshold`, etc.) were being created for dryers and washers that expose the `applianceCareAndMaintenance*` capability group. These are low-level internal service counters with no user-facing value and no friendly names. They are now suppressed via the attributes blacklist. Existing installations will see these entities become unavailable — they can be safely removed from the entity registry via **Settings → Devices & Services → Entities**.

---

## Supported Appliances (as of v3.4.4)

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
| `A9` / `Muju` | Air Purifier | Full | A9 series; UltimateHome 500 (EP53) |
| `MW` | Microwave | Stub | *(no samples — [submit yours](https://github.com/TTLucian/ha-electrolux/issues))* |