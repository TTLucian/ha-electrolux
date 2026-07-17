# RVC Read-Only Map / Zone Sensors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the Pure i9 robot vacuum's existing persistent-map and cleaning-session data as read-only Home Assistant sensors (closes #130).

**Architecture:** Additive catalog entries in `catalog_rvc.py` keyed to nested `reported`-state paths (the existing catalog-driven creation path in `models.py` auto-creates an entity when `get_state(key)` resolves). Two entries hold list payloads reduced to a scalar by small `native_value` blocks in `sensor.py`, mirroring the existing `alerts` sensor.

**Tech Stack:** Python 3, Home Assistant custom integration, pytest, ruff, black, uv.

## Global Constraints

- Dependency/tooling: run tests and lint via `uv` — `uv run pytest`, `uv run ruff check`, `uv run black` (per `.github/workflows/ci.yml`).
- All new entities: `entity_category=EntityCategory.DIAGNOSTIC`, `entity_registry_enabled_default=False`.
- Entity names: inline `friendly_name` only — no `strings.json` / translation changes.
- Binary sensors in `catalog_rvc.py` use `device_class=None, entity_platform=BINARY_SENSOR` (existing convention, e.g. `autoDustCollection` at `catalog_rvc.py:434`).
- No changes to `coordinator.py`, `models.py`, `entity.py`.
- Full suite must stay green; `ruff` + `black` clean.
- Commit style: Conventional Commits; end message with the repo's `Co-Authored-By` trailer.

---

### Task 1: Scalar map/session sensors (pure catalog)

**Files:**
- Modify: `custom_components/electrolux/catalogs/catalog_rvc.py` (append 5 entries to the `CATALOG_RVC` dict, before its closing `}`)
- Test: `tests/test_catalog.py` (add to `class TestCatalogRobotVacuum`)
- Test: `tests/test_sensor.py` (add a nested-path extraction test)

**Interfaces:**
- Consumes: `ElectroluxDevice` (already imported in `catalog_rvc.py`), `EntityCategory`, `BINARY_SENSOR`, `SensorDeviceClass` (all already imported).
- Produces: catalog keys `persistentMapsCreated/mapId`, `cleaningSession/sessionId`, `cleaningSession/completion`, `cleaningSession/areaCovered`, `mapData/robotPoseReliable`.

- [ ] **Step 1: Write the failing catalog test**

In `tests/test_catalog.py`, inside `class TestCatalogRobotVacuum`, add:

```python
    def test_rvc_has_scalar_map_zone_sensors(self):
        """Robot vacuum catalog exposes read-only map/session scalar sensors (#130)."""
        from homeassistant.const import EntityCategory

        from custom_components.electrolux.catalogs.catalog_rvc import CATALOG_RVC
        from custom_components.electrolux.model import ElectroluxDevice

        scalar_keys = [
            "persistentMapsCreated/mapId",
            "cleaningSession/sessionId",
            "cleaningSession/completion",
            "cleaningSession/areaCovered",
            "mapData/robotPoseReliable",
        ]
        for key in scalar_keys:
            assert key in CATALOG_RVC, f"missing {key}"
            entry = CATALOG_RVC[key]
            assert isinstance(entry, ElectroluxDevice)
            assert entry.entity_category == EntityCategory.DIAGNOSTIC
            assert entry.entity_registry_enabled_default is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_catalog.py::TestCatalogRobotVacuum::test_rvc_has_scalar_map_zone_sensors -v`
Expected: FAIL — `missing persistentMapsCreated/mapId` (KeyError/AssertionError).

- [ ] **Step 3: Add the catalog entries**

In `custom_components/electrolux/catalogs/catalog_rvc.py`, append these entries inside the `CATALOG_RVC` dict (just before the final closing `}`):

```python
    # --- Pure i9 read-only map / cleaning-session data (#130) ---
    "persistentMapsCreated/mapId": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:map",
        entity_registry_enabled_default=False,
        friendly_name="Persistent Map ID",
    ),
    "cleaningSession/sessionId": ElectroluxDevice(
        capability_info={"access": "read", "type": "int"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:counter",
        entity_registry_enabled_default=False,
        friendly_name="Cleaning Session ID",
    ),
    "cleaningSession/completion": ElectroluxDevice(
        capability_info={"access": "read", "type": "string"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:flag-checkered",
        entity_registry_enabled_default=False,
        friendly_name="Cleaning Completion",
    ),
    "cleaningSession/areaCovered": ElectroluxDevice(
        capability_info={"access": "read", "type": "number"},
        device_class=None,
        unit="m²",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:ruler-square",
        entity_registry_enabled_default=False,
        friendly_name="Area Covered",
    ),
    "mapData/robotPoseReliable": ElectroluxDevice(
        capability_info={"access": "read", "type": "boolean"},
        device_class=None,
        entity_platform=BINARY_SENSOR,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:crosshairs-gps",
        entity_registry_enabled_default=False,
        friendly_name="Robot Pose Reliable",
    ),
```

- [ ] **Step 4: Run catalog test to verify it passes**

Run: `uv run pytest tests/test_catalog.py::TestCatalogRobotVacuum::test_rvc_has_scalar_map_zone_sensors -v`
Expected: PASS.

- [ ] **Step 5: Write a nested-path extraction test**

This proves a nested-path catalog key resolves through `extract_value`. In `tests/test_sensor.py`, add a new class at the end of the file:

```python
class TestRvcMapZoneSensors:
    """Read-only Pure i9 map/zone sensors (#130)."""

    def _sensor(self, mock_coordinator, entity_attr, entity_source, reported):
        entity = ElectroluxSensor(
            coordinator=mock_coordinator,
            name="Test",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SENSOR,
            entity_name=entity_attr,
            entity_attr=entity_attr,
            entity_source=entity_source,
            capability={"access": "read", "type": "string"},
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:map",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "applianceId": "test_appliance",
            "properties": {"reported": reported, "desired": {}, "metadata": {}},
        }
        entity.reported_state = reported
        return entity

    def test_persistent_map_id_extracts_nested_scalar(self, mock_coordinator):
        entity = self._sensor(
            mock_coordinator,
            entity_attr="mapId",
            entity_source="persistentMapsCreated",
            reported={"persistentMapsCreated": {"mapId": "abc-123"}},
        )
        assert entity.native_value == "Abc-123"
```

Note: `native_value` title-cases plain strings (`abc-123` → `Abc-123`); assert the processed form.

- [ ] **Step 6: Run the extraction test**

Run: `uv run pytest tests/test_sensor.py::TestRvcMapZoneSensors::test_persistent_map_id_extracts_nested_scalar -v`
Expected: PASS (no production change needed — this validates the existing extract path).

- [ ] **Step 7: Lint + commit**

```bash
uv run ruff check custom_components/electrolux/catalogs/catalog_rvc.py tests/test_catalog.py tests/test_sensor.py
uv run black custom_components/electrolux/catalogs/catalog_rvc.py tests/test_catalog.py tests/test_sensor.py
git add custom_components/electrolux/catalogs/catalog_rvc.py tests/test_catalog.py tests/test_sensor.py
git commit -m "feat(catalog/rvc): add read-only map/session scalar sensors (#130)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Derived "map zone count" sensor

**Files:**
- Modify: `custom_components/electrolux/catalogs/catalog_rvc.py` (append 1 entry)
- Modify: `custom_components/electrolux/sensor.py` (`native_value`, add a block after `value = self.extract_value()`)
- Test: `tests/test_sensor.py` (`TestRvcMapZoneSensors`)

**Interfaces:**
- Consumes: `self.json_path` (str, `entity.py:1031`) = `"mapData/mapMatch/zones"` for this entity; `self.extract_value()` returns the raw `list`.
- Produces: catalog key `mapData/mapMatch/zones`; `native_value` returns `int` (zone count) or `None`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_sensor.py`, inside `class TestRvcMapZoneSensors`, add:

```python
    def test_zone_count_returns_list_length(self, mock_coordinator):
        entity = self._sensor(
            mock_coordinator,
            entity_attr="zones",
            entity_source="mapData/mapMatch",
            reported={"mapData": {"mapMatch": {"zones": [{}, {}, {}, {}, {}]}}},
        )
        assert entity.native_value == 5

    def test_zone_count_empty_list_is_none(self, mock_coordinator):
        entity = self._sensor(
            mock_coordinator,
            entity_attr="zones",
            entity_source="mapData/mapMatch",
            reported={"mapData": {"mapMatch": {"zones": []}}},
        )
        assert entity.native_value is None

    def test_zone_count_missing_is_none(self, mock_coordinator):
        entity = self._sensor(
            mock_coordinator,
            entity_attr="zones",
            entity_source="mapData/mapMatch",
            reported={"mapData": {"mapMatch": {}}},
        )
        assert entity.native_value is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest "tests/test_sensor.py::TestRvcMapZoneSensors" -k zone_count -v`
Expected: FAIL — `test_zone_count_returns_list_length` gets a stringified list, not `5`.

- [ ] **Step 3: Add the catalog entry**

In `catalog_rvc.py`, append inside `CATALOG_RVC` (after the Task 1 block):

```python
    # Derived: number of zones on the persistent map (#130)
    "mapData/mapMatch/zones": ElectroluxDevice(
        capability_info={"access": "read", "type": "list"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:shape-outline",
        entity_registry_enabled_default=False,
        friendly_name="Map Zone Count",
    ),
```

- [ ] **Step 4: Add the `native_value` reduction**

In `custom_components/electrolux/sensor.py`, in `ElectroluxSensor.native_value`, immediately after the line `value = self.extract_value()` (currently line 126), insert:

```python
        # RVC (#130): reduce the persistent-map zone list to a count
        if self.json_path == "mapData/mapMatch/zones":
            return len(value) if isinstance(value, list) and value else None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest "tests/test_sensor.py::TestRvcMapZoneSensors" -k zone_count -v`
Expected: PASS (all 3).

- [ ] **Step 6: Lint + commit**

```bash
uv run ruff check custom_components/electrolux/catalogs/catalog_rvc.py custom_components/electrolux/sensor.py tests/test_sensor.py
uv run black custom_components/electrolux/catalogs/catalog_rvc.py custom_components/electrolux/sensor.py tests/test_sensor.py
git add custom_components/electrolux/catalogs/catalog_rvc.py custom_components/electrolux/sensor.py tests/test_sensor.py
git commit -m "feat(sensor/rvc): add derived map zone count sensor (#130)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Derived "cleaning zone status" summary sensor

**Files:**
- Modify: `custom_components/electrolux/catalogs/catalog_rvc.py` (append 1 entry)
- Modify: `custom_components/electrolux/sensor.py` (`native_value` + `extra_state_attributes`)
- Test: `tests/test_sensor.py` (`TestRvcMapZoneSensors`)

**Interfaces:**
- Consumes: `self.json_path` = `"cleaningSession/zoneStatus"`; `self.extract_value()` returns a `list[dict]`, each dict shaped `{"id": str, "status": str, "powerMode": int}`.
- Produces: catalog key `cleaningSession/zoneStatus`; `native_value` returns `str` like `"2/3 finished"` or `None`; `extra_state_attributes` returns `{zone_id: status}`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_sensor.py`, inside `class TestRvcMapZoneSensors`, add:

```python
    ZONE_STATUS = [
        {"id": "z1", "status": "finished", "powerMode": 1},
        {"id": "z2", "status": "finished", "powerMode": 1},
        {"id": "z3", "status": "terminated", "powerMode": 1},
    ]

    def test_zone_status_summary(self, mock_coordinator):
        entity = self._sensor(
            mock_coordinator,
            entity_attr="zoneStatus",
            entity_source="cleaningSession",
            reported={"cleaningSession": {"zoneStatus": self.ZONE_STATUS}},
        )
        assert entity.native_value == "2/3 finished"

    def test_zone_status_empty_is_none(self, mock_coordinator):
        entity = self._sensor(
            mock_coordinator,
            entity_attr="zoneStatus",
            entity_source="cleaningSession",
            reported={"cleaningSession": {"zoneStatus": []}},
        )
        assert entity.native_value is None

    def test_zone_status_extra_attributes(self, mock_coordinator):
        entity = self._sensor(
            mock_coordinator,
            entity_attr="zoneStatus",
            entity_source="cleaningSession",
            reported={"cleaningSession": {"zoneStatus": self.ZONE_STATUS}},
        )
        assert entity.extra_state_attributes == {
            "z1": "finished",
            "z2": "finished",
            "z3": "terminated",
        }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest "tests/test_sensor.py::TestRvcMapZoneSensors" -k zone_status -v`
Expected: FAIL — summary/attributes not implemented.

- [ ] **Step 3: Add the catalog entry**

In `catalog_rvc.py`, append inside `CATALOG_RVC` (after the Task 2 block):

```python
    # Derived: last cleaning-session zone status summary (#130)
    "cleaningSession/zoneStatus": ElectroluxDevice(
        capability_info={"access": "read", "type": "list"},
        device_class=None,
        unit=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_icon="mdi:map-marker-check",
        entity_registry_enabled_default=False,
        friendly_name="Cleaning Zone Status",
    ),
```

- [ ] **Step 4: Add the `native_value` summary block**

In `sensor.py` `native_value`, directly below the Task 2 zone-count block (still right after `value = self.extract_value()`), insert:

```python
        # RVC (#130): summarise cleaning-session zone statuses as "<finished>/<total> finished"
        if self.json_path == "cleaningSession/zoneStatus":
            if not isinstance(value, list) or not value:
                return None
            finished = sum(
                1
                for zone in value
                if isinstance(zone, dict) and zone.get("status") == "finished"
            )
            return f"{finished}/{len(value)} finished"
```

- [ ] **Step 5: Add the `extra_state_attributes` branch**

In `sensor.py`, in `ElectroluxSensor.extra_state_attributes`, insert at the very top of the method body (before `if self.entity_attr == "alerts":`):

```python
        # RVC (#130): expose per-zone status detail
        if self.json_path == "cleaningSession/zoneStatus":
            value = self.extract_value()
            if isinstance(value, list):
                return {
                    zone["id"]: zone.get("status")
                    for zone in value
                    if isinstance(zone, dict) and "id" in zone
                }
            return {}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest "tests/test_sensor.py::TestRvcMapZoneSensors" -k zone_status -v`
Expected: PASS (all 3).

- [ ] **Step 7: Lint + commit**

```bash
uv run ruff check custom_components/electrolux/catalogs/catalog_rvc.py custom_components/electrolux/sensor.py tests/test_sensor.py
uv run black custom_components/electrolux/catalogs/catalog_rvc.py custom_components/electrolux/sensor.py tests/test_sensor.py
git add custom_components/electrolux/catalogs/catalog_rvc.py custom_components/electrolux/sensor.py tests/test_sensor.py
git commit -m "feat(sensor/rvc): add cleaning zone status summary sensor (#130)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Full-suite verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -q`
Expected: all pass, no new failures.

- [ ] **Step 2: Lint the whole change**

Run: `uv run ruff check custom_components/electrolux tests && uv run black --check custom_components/electrolux tests`
Expected: clean.

- [ ] **Step 3: Confirm entity count sanity (optional manual check)**

Confirm the 7 new keys are present:

Run: `uv run python -c "from custom_components.electrolux.catalogs.catalog_rvc import CATALOG_RVC; print([k for k in CATALOG_RVC if k in {'persistentMapsCreated/mapId','cleaningSession/sessionId','cleaningSession/completion','cleaningSession/areaCovered','mapData/robotPoseReliable','mapData/mapMatch/zones','cleaningSession/zoneStatus'}])"`
Expected: all 7 keys listed.

---

## Self-Review

**Spec coverage:**
- Persistent map id → Task 1 (`persistentMapsCreated/mapId`). ✓
- Number of zones → Task 2 (`mapData/mapMatch/zones`, derived count). ✓
- Cleaning-session zone statuses → Task 3 (`cleaningSession/zoneStatus`, summary + attrs). ✓
- Bonus scalars (session id, completion, area covered, pose reliable) → Task 1. ✓
- Dropped duration / timestamps → not implemented (per spec). ✓
- No coordinator/model/entity changes, no strings.json → honored. ✓
- Adjacent `PUREi9`/`Purei9` routing note → out of scope, flagged in spec only. ✓

**Placeholder scan:** none — every code/test step contains full content.

**Type consistency:** `self.json_path` compared with exact strings matching each catalog key's `entity_source/entity_attr`; `native_value` returns `int|str|None`; `extra_state_attributes` returns `dict`. `_sensor` test helper signature reused across Tasks 1-3. Consistent.
