```markdown
## Overview

v3.4.3 is a maintenance release that fixes a command-sending bug affecting dryers and washers, and improves internal code quality.

---

**BUG FIXES:**

- **Dryer / Washer controls failing to send commands**: Controls such as Anti-Crease duration, Humidity Target, Dryness Level, Eco/Night mode, and other cycle-selection settings were returning a `Capability not found` error when changed from Home Assistant. The integration was sending the command in the wrong format — the fix ensures these settings are correctly delivered to the appliance. Affected appliances: TD / WM / WD (non-DAM models).

---

**IMPROVEMENTS:**

- **Internal code restructuring**: The main utility module was split into dedicated modules for error handling, token management, and API client logic. No behaviour change — this improves maintainability and makes the codebase easier to navigate and extend.

- **Internal test coverage**: Expanded automated test coverage across core modules — models, coordinator, initialisation, diagnostics, and fan — reducing the risk of regressions in future releases.

---

## Supported Appliances (as of v3.4.3)

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

```
