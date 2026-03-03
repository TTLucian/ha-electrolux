## Overview

v3.4.2 introduces smart state-aware availability for `executeCommand` buttons. Every START, STOPRESET, PAUSE, and RESUME button is now automatically enabled or greyed out based on what the appliance's API actually accepts in its current state — derived directly from the conditional capability rules embedded in real diagnostic samples.

**IMPROVEMENTS:**

- **State-aware `executeCommand` buttons**: `executeCommand` button entities (START, STOPRESET, PAUSE, RESUME) are now enabled only when the appliance's current `applianceState` is one where the Electrolux API accepts that command. When the state is outside the valid set the button is greyed out — pressing it would produce an API error anyway. Each appliance type has its own independently verified rules cross-referenced against real diagnostic JSON samples:

  | Appliance | Button | Enabled when `applianceState` is… |
  |-----------|--------|-----------------------------------|
  | Oven | START | `READY_TO_START`, `END_OF_CYCLE` |
  | Oven | STOPRESET | `RUNNING`, `PAUSED`, `DELAYED_START` |
  | Steam Oven | START | `OFF` |
  | Steam Oven | STOPRESET | `RUNNING` |
  | Washer / Washer-Dryer | START | `READY_TO_START` |
  | Washer / Washer-Dryer | STOPRESET | `PAUSED`, `END_OF_CYCLE` |
  | Washer / Washer-Dryer | PAUSE | `RUNNING`, `DELAYED_START` |
  | Washer / Washer-Dryer | RESUME | `PAUSED` |
  | Dryer | START | `READY_TO_START`, `IDLE` |
  | Dryer | STOPRESET | `PAUSED`, `END_OF_CYCLE`, `ANTICREASE` |
  | Dryer | PAUSE | `RUNNING`, `DELAYED_START` |
  | Dryer | RESUME | `PAUSED` |
  | Dishwasher | START | `READY_TO_START`, `IDLE` |
  | Dishwasher | STOPRESET | `PAUSED`, `END_OF_CYCLE`, `DELAYED_START` |
  | Dishwasher | PAUSE | `RUNNING` |
  | Dishwasher | RESUME | `PAUSED` |

  AC power and refrigerator ice maker ON/OFF have no state restriction and are always available.

  Rules sourced from: OV-944188772, SO-944035035, WM-914915144, WD-914611500, WD-914611000, TD-916098401, TD-916098618, TD-916099949, TD-916099971, DW-911434654, DW-911434834

---

## Supported Appliances (as of v3.4.2)

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
