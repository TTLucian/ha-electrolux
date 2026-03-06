# Release Notes v3.5.4

### HA 2026.x Compatibility — Import Path Updates

Updated all HA import paths to align with the officially recommended locations as of HA 2026.x. While these symbols were still resolvable at runtime via backward-compatible re-exports, using the deprecated paths generates warnings and may break in a future HA release.

**Changes:**

- `EntityCategory` — updated from `homeassistant.helpers.entity` → `homeassistant.const` across all catalog files, `const.py`, and `models.py`
- `ClimateEntityFeature`, `HVACAction`, `HVACMode` — updated from `homeassistant.components.climate` → `homeassistant.components.climate.const` in `climate.py`

**Affected files:** `const.py`, `models.py`, `climate.py`, `catalog_core.py`, `catalog_air_conditioner.py`, `catalog_dishwasher.py`, `catalog_dryer.py`, `catalog_oven.py`, `catalog_purifier.py`, `catalog_refrigerator.py`, `catalog_steam_oven.py`, `catalog_utils.py`, `catalog_washer.py`, `catalog_washer_dryer.py`
