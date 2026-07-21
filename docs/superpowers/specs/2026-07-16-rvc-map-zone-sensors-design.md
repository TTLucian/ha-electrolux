# RVC read-only map / zone sensors (#130)

Closes #130. Follow-up to #81 / #82. Sibling of #131 (zone-control write support — out of scope here).

## Goal

Surface the Pure i9 robot vacuum's existing persistent-map and cleaning-session
data as **read-only** Home Assistant entities. No write/control capability, no new
entity platform, no coordinator changes. Purely additive.

## Background

Pure i9 (`PUREi9` / `Gordias` / `Cybele` / `700series` → `CATALOG_RVC`) reports rich
map/zone data under `state.properties.reported`, but none of it is exposed today.
The write side (`CustomPlay/persistentMapId`, `CustomPlay/zones`, type `custom`) is
tracked separately in #131.

Data confirmed against the diagnostics JSON attached to #81
(`900277253730002731100106`).

## How entity creation works (existing mechanism)

`models.py` `Appliance.setup()` (lines ~637-702) is catalog-driven. For each
`catalog_rvc` key **not** present in API capabilities, an entity is created **iff**
`get_state(key) is not None`.

- `get_state` (`models.py:243`) splits the key on `/` and walks reported state to
  **arbitrary depth** — so a catalog key of `mapData/mapMatch/zones` resolves.
- `get_entity_attr` (`api.py:158`) = `rpartition("/")[-1]` → leaf (`zones`).
- `get_category`/entity_source = `rpartition("/")[0]` → parent (`mapData/mapMatch`).
- `json_path` (`entity.py:1031`) = `f"{entity_source}/{entity_attr}"` → full path.
- `extract_value` (`entity.py:992-1021`) returns the leaf value (scalar, list, or dict).

This is the same pattern PR #120 used for the Telica AC catalog additions.

## Entities

All entries: `EntityCategory.DIAGNOSTIC`, `entity_registry_enabled_default=False`
(raw map data is power-user / automation material, not everyday UI).

### Scalar sensors (pure catalog, zero code)

| Catalog key | Platform | Value | Unit / class |
|---|---|---|---|
| `persistentMapsCreated/mapId` | Sensor | active persistent map UUID | string |
| `cleaningSession/sessionId` | Sensor | last/current cleaning session id | int |
| `cleaningSession/completion` | Sensor | e.g. `cleaningFinishedSuccessfulInCharger` | string |
| `cleaningSession/areaCovered` | Sensor | area covered last session (`9.92`) | `m²`, no device_class |
| `mapData/robotPoseReliable` | Binary sensor | robot pose reliable | bool |

### Derived sensors (small `native_value` handling in `sensor.py`)

| Catalog key | Platform | Value |
|---|---|---|
| `mapData/mapMatch/zones` | Sensor | **`len(list)`** → number of zones on the persistent map |
| `cleaningSession/zoneStatus` | Sensor | **`"{finished}/{total}"`** summary; per-zone `{id: status}` in `extra_state_attributes` |

`extract_value` returns the raw list for both; `native_value` reduces it.

## Code changes

### `custom_components/electrolux/catalogs/catalog_rvc.py`
Add the 7 `ElectroluxDevice` entries above. No new imports required:
`SensorDeviceClass`, `EntityCategory`, and the `BINARY_SENSOR` const are already
imported. Binary sensor entries follow the existing RVC convention
(`device_class=None, entity_platform=BINARY_SENSOR`, e.g. `autoDustCollection` at
`catalog_rvc.py:434`), not `BinarySensorDeviceClass`. Use inline `friendly_name`
(no `strings.json`, matching #120).

### `custom_components/electrolux/sensor.py` — `native_value`
Two blocks, keyed on `self.json_path` (full path, collision-safe — not the generic
leaf `zones`/`zoneStatus`):

```python
# Number of zones on the persistent map
if self.json_path and self.json_path.endswith("mapData/mapMatch/zones"):
    return len(value) if isinstance(value, list) else None

# Cleaning zone status summary: "2/3 finished"
if self.json_path and self.json_path.endswith("cleaningSession/zoneStatus"):
    if not isinstance(value, list) or not value:
        return None
    finished = sum(1 for z in value if isinstance(z, dict) and z.get("status") == "finished")
    return f"{finished}/{len(value)} finished"
```

`extra_state_attributes` gains a `cleaningSession/zoneStatus` branch returning
`{z["id"]: z["status"] for z in value}` (mirrors the existing `alerts` branch).

Placement: before the generic `str`/`title()` normalization so the list is not
stringified.

## Explicitly out of scope / dropped

- **Cleaning duration** — `cleaningSession/cleaningDuration` = `11250000000`, i.e.
  .NET 100-ns ticks (`÷1e7 ≈ 1125 s`). Unit ambiguity risks shipping mislabeled data.
  Skip rather than guess. Can revisit with confirmation from a second diagnostics file.
- **Timestamps** (`startTime`, `eventTime`, `lastUpdate`) — tz/format parsing risk; not
  requested by the issue.
- **Zone control / selection / trigger** — `CustomPlay/*` write path → #131.
- **`mapData` geometry** (`robotPose`, `chargerPoses`, `vertices`) — dicts/nested lists,
  no useful scalar rendering.

## Testing

- `tests/test_catalog.py` — assert the 7 new keys load as `ElectroluxDevice`s in
  `CATALOG_RVC` (mirror existing `test_purifier_*` / `test_refrigerator_*` patterns).
- `tests/test_sensor.py` — `native_value` for the two derived sensors:
  - `mapData/mapMatch/zones`: list of 5 → `5`; empty list → `None`; non-list → `None`.
  - `cleaningSession/zoneStatus`: `[finished, finished, terminated]` → `"2/3 finished"`;
    empty/missing → `None`; `extra_state_attributes` maps id→status.
- No snapshot files exist for RVC (`tests/` has none) — none to add/update; keeps in
  line with the repo convention of not introducing snapshots for a new entity set here.
- Full suite must stay green; `ruff` + `black` clean.

## Note (adjacent, not fixed here)

Routing map (`catalog_core.py:214`) keys on `"PUREi9"`. Issue #82's reported type code
is `"Purei9"` (lowercase i) — a possible routing miss for that specific unit. Not part
of #130; flag on #82.
