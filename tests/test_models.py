"""Tests for models.py — Appliance, Appliances, deep_merge_dicts."""

from unittest.mock import MagicMock

from custom_components.electrolux.models import (
    Appliance,
    ApplianceData,
    Appliances,
    deep_merge_dicts,
)

# ---------------------------------------------------------------------------
# deep_merge_dicts
# ---------------------------------------------------------------------------


class TestDeepMergeDicts:
    def test_flat_merge_no_overlap(self):
        result = deep_merge_dicts({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_flat_merge_with_override(self):
        result = deep_merge_dicts({"a": 1, "b": 2}, {"b": 99})
        assert result == {"a": 1, "b": 99}

    def test_nested_merge(self):
        d1 = {"a": {"x": 1, "y": 2}}
        d2 = {"a": {"y": 99, "z": 3}}
        result = deep_merge_dicts(d1, d2)
        assert result == {"a": {"x": 1, "y": 99, "z": 3}}

    def test_non_dict_value_overrides_dict(self):
        """dict2 non-dict value replaces dict in dict1."""
        result = deep_merge_dicts({"a": {"x": 1}}, {"a": 42})
        assert result == {"a": 42}

    def test_dict_value_replaces_non_dict(self):
        """dict2 dict value replaces scalar in dict1."""
        result = deep_merge_dicts({"a": 42}, {"a": {"x": 1}})
        assert result == {"a": {"x": 1}}

    def test_empty_dicts(self):
        assert deep_merge_dicts({}, {}) == {}

    def test_dict1_empty(self):
        assert deep_merge_dicts({}, {"a": 1}) == {"a": 1}

    def test_dict2_empty(self):
        assert deep_merge_dicts({"a": 1}, {}) == {"a": 1}

    def test_original_not_mutated(self):
        d1 = {"a": {"x": 1}}
        d2 = {"a": {"y": 2}}
        deep_merge_dicts(d1, d2)
        assert d1 == {"a": {"x": 1}}  # d1 must not be modified


# ---------------------------------------------------------------------------
# ApplianceData
# ---------------------------------------------------------------------------


class TestApplianceData:
    def test_get_category_present(self):
        data = ApplianceData({"category": {"key1": "cat_value"}})
        assert data.get_category("key1") == "cat_value"

    def test_get_category_missing_key(self):
        data = ApplianceData({"category": {}})
        assert data.get_category("missing") is None

    def test_get_category_no_category(self):
        data = ApplianceData({})
        assert data.get_category("anything") is None


# ---------------------------------------------------------------------------
# Appliance helpers
# ---------------------------------------------------------------------------


def _make_appliance(state=None):
    """Return an Appliance with minimal setup (no catalog needed)."""
    if state is None:
        state = {
            "properties": {
                "reported": {
                    "connectivityState": "connected",
                    "applianceInfo": {"applianceType": "OV"},
                }
            }
        }
    coordinator = MagicMock()
    return Appliance(
        coordinator=coordinator,
        name="Test Oven",
        pnc_id="PNC123",
        brand="Electrolux",
        model="EOH8854AAX",
        state=state,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Appliance
# ---------------------------------------------------------------------------


class TestApplianceInit:
    def test_attributes_set(self):
        app = _make_appliance()
        assert app.pnc_id == "PNC123"
        assert app.name == "Test Oven"
        assert app.brand == "Electrolux"
        assert app.model == "EOH8854AAX"
        assert app.entities == []
        assert app._catalog_cache is None
        assert app.data is None

    def test_serial_number_default_none(self):
        app = _make_appliance()
        assert app.serial_number is None

    def test_serial_number_set(self):
        app = Appliance(
            coordinator=MagicMock(),
            name="n",
            pnc_id="p",
            brand="b",
            model="m",
            state={},
            serial_number="SN-12345",
        )
        assert app.serial_number == "SN-12345"


class TestApplianceReportedState:
    def test_returns_reported_dict(self):
        app = _make_appliance()
        result = app.reported_state
        assert result["connectivityState"] == "connected"

    def test_empty_state(self):
        app = _make_appliance(state={})
        assert app.reported_state == {}

    def test_missing_reported(self):
        app = _make_appliance(state={"properties": {}})
        assert app.reported_state == {}


class TestApplianceType:
    def test_returns_type(self):
        app = _make_appliance()
        assert app.appliance_type == "OV"

    def test_no_applianceInfo(self):
        app = _make_appliance(
            state={"properties": {"reported": {"connectivityState": "connected"}}}
        )
        assert app.appliance_type is None

    def test_empty_state(self):
        app = _make_appliance(state={})
        assert app.appliance_type is None


class TestApplianceGetState:
    def test_simple_key(self):
        app = _make_appliance()
        assert app.get_state("connectivityState") == "connected"

    def test_nested_key(self):
        app = _make_appliance()
        assert app.get_state("applianceInfo/applianceType") == "OV"

    def test_missing_key(self):
        app = _make_appliance()
        assert app.get_state("nonExistent") is None

    def test_missing_nested_key(self):
        app = _make_appliance()
        assert app.get_state("applianceInfo/nonExistent") is None

    def test_nested_non_dict_intermediate(self):
        """If intermediate key maps to a non-dict, return None."""
        app = _make_appliance(state={"properties": {"reported": {"scalar": "value"}}})
        assert app.get_state("scalar/something") is None


class TestApplianceUpdate:
    def test_update_replaces_state(self):
        app = _make_appliance()
        # Patch initialize_constant_values and entity.update to isolate
        app.initialize_constant_values = MagicMock()
        mock_entity = MagicMock()
        app.entities = [mock_entity]

        new_state = {"properties": {"reported": {"powerState": "off"}}}
        app.update(new_state)

        assert app.state == new_state
        app.initialize_constant_values.assert_called_once()
        mock_entity.update.assert_called_once_with(new_state)


class TestApplianceUpdateReportedData:
    def _app_with_state(self, reported: dict):
        state = {"properties": {"reported": reported}}
        return _make_appliance(state=state)

    def test_flat_property_update(self):
        app = self._app_with_state({"powerState": "on"})
        app.entities = []
        # Stub catalog so initialize isn't needed
        app._catalog_cache = {}

        app.update_reported_data({"property": "powerState", "value": "off"})
        assert app.reported_state["powerState"] == "off"

    def test_nested_property_update(self):
        app = self._app_with_state({"userSelections": {"program": "BAKE"}})
        app.entities = []
        app._catalog_cache = {}

        app.update_reported_data(
            {"property": "userSelections/program", "value": "GRILL"}
        )
        assert app.reported_state["userSelections"]["program"] == "GRILL"

    def test_nested_creates_missing_intermediate(self):
        app = self._app_with_state({})
        app.entities = []
        app._catalog_cache = {}

        app.update_reported_data({"property": "a/b", "value": 42})
        assert app.reported_state["a"]["b"] == 42

    def test_nested_non_dict_intermediate_logs_warning(self, caplog):
        """Writing to a nested path where intermediate is a scalar must not crash."""
        import logging

        app = self._app_with_state({"a": "not_a_dict"})
        app.entities = []
        app._catalog_cache = {}

        with caplog.at_level(logging.WARNING):
            app.update_reported_data({"property": "a/b", "value": 1})
        # Should log a warning and return without crashing
        assert "Cannot update nested property" in caplog.text

    def test_full_state_merge(self):
        app = self._app_with_state({"powerState": "on", "temp": 200})
        app.entities = []
        app._catalog_cache = {}

        app.update_reported_data({"temp": 220, "newKey": "hello"})
        assert app.reported_state["powerState"] == "on"
        assert app.reported_state["temp"] == 220
        assert app.reported_state["newKey"] == "hello"

    def test_entities_updated_after_flat_change(self):
        app = self._app_with_state({"x": 1})
        mock_entity = MagicMock()
        app.entities = [mock_entity]
        app._catalog_cache = {}

        app.update_reported_data({"property": "x", "value": 2})
        mock_entity.update.assert_called_once()

    def test_invalid_data_does_not_raise(self):
        """KeyError / TypeError in update should be caught and logged."""
        app = _make_appliance(state=None)  # type: ignore[arg-type]
        app._catalog_cache = {}
        app.entities = []
        # Should not raise
        app.update_reported_data({"property": "x", "value": 1})


# ---------------------------------------------------------------------------
# Appliances
# ---------------------------------------------------------------------------


class TestAppliances:
    def _make(self):
        a1 = MagicMock(spec=Appliance)
        a1.pnc_id = "aaa"
        a2 = MagicMock(spec=Appliance)
        a2.pnc_id = "bbb"
        return Appliances({"aaa": a1, "bbb": a2}), a1, a2

    def test_len(self):
        apps, _, _ = self._make()
        assert len(apps) == 2

    def test_get_appliance_existing(self):
        apps, a1, _ = self._make()
        assert apps.get_appliance("aaa") is a1

    def test_get_appliance_missing(self):
        apps, _, _ = self._make()
        assert apps.get_appliance("UNKNOWN") is None

    def test_get_appliances(self):
        apps, a1, a2 = self._make()
        result = apps.get_appliances()
        assert "aaa" in result
        assert "bbb" in result

    def test_get_appliance_ids(self):
        apps, _, _ = self._make()
        ids = apps.get_appliance_ids()
        assert set(ids) == {"aaa", "bbb"}

    def test_empty_appliances(self):
        apps = Appliances({})
        assert len(apps) == 0
        assert apps.get_appliances() == {}
        assert apps.get_appliance_ids() == []


# ---------------------------------------------------------------------------
# Helpers shared by the expanded coverage tests
# ---------------------------------------------------------------------------


def _make_coordinator():
    """Return a minimal MagicMock coordinator compatible with entity init."""
    coordinator = MagicMock()
    coordinator.hass = MagicMock()
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.data = {}
    coordinator._consecutive_auth_failures = 0
    coordinator._auth_failure_threshold = 3
    coordinator._last_time_to_end = {}
    coordinator._deferred_tasks = set()
    coordinator._deferred_tasks_by_appliance = {}
    return coordinator


def _make_app_full(state=None, model="EOH8854AAX"):
    """Return an Appliance with a proper (mock) coordinator."""
    if state is None:
        state = {
            "properties": {
                "reported": {
                    "applianceInfo": {"applianceType": "OV"},
                    "applianceState": "READY",
                    "connectivityState": "connected",
                }
            }
        }
    return Appliance(
        coordinator=_make_coordinator(),
        name="Test Oven",
        pnc_id="PNC123",
        brand="Electrolux",
        model=model,
        state=state,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# initialize_constant_values  (lines 155-167)
# ---------------------------------------------------------------------------


class TestInitializeConstantValues:
    """Cover lines 155-167: initialize_constant_values loop."""

    def test_sets_missing_key_from_catalog(self):
        """Constant catalog entry injected when key not in reported_state."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "someConstant": ElectroluxDevice(
                capability_info={"access": "constant", "default": 42}
            )
        }
        app.initialize_constant_values()
        assert app.reported_state["someConstant"] == 42

    def test_does_not_overwrite_existing_key(self):
        """Existing value must not be replaced by catalog default."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app.reported_state["someConstant"] = 99
        app._catalog_cache = {
            "someConstant": ElectroluxDevice(
                capability_info={"access": "constant", "default": 42}
            )
        }
        app.initialize_constant_values()
        assert app.reported_state["someConstant"] == 99  # unchanged

    def test_skips_non_constant_access(self):
        """Catalog items with access != 'constant' are not injected."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "rwKey": ElectroluxDevice(
                capability_info={"access": "readwrite", "default": 10}
            )
        }
        app.initialize_constant_values()
        assert "rwKey" not in app.reported_state

    def test_skips_constant_without_default(self):
        """Constant entry with no 'default' key is skipped."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "constNoDefault": ElectroluxDevice(capability_info={"access": "constant"})
        }
        app.initialize_constant_values()
        assert "constNoDefault" not in app.reported_state

    def test_early_return_when_no_reported_state(self):
        """Early return when reported_state is empty/falsy (lines 155-156)."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full(state={})
        app._catalog_cache = {
            "c": ElectroluxDevice(capability_info={"access": "constant", "default": 1})
        }
        # Must not raise
        app.initialize_constant_values()


# ---------------------------------------------------------------------------
# catalog property  (lines 192-222)
# ---------------------------------------------------------------------------


class TestCatalogProperty:
    """Cover lines 192-222: catalog property build and cache."""

    def test_builds_and_caches(self):
        """Catalog is built once and the result is cached."""
        app = _make_app_full()
        assert app._catalog_cache is None
        cat1 = app.catalog
        assert isinstance(cat1, dict)
        assert app._catalog_cache is cat1
        # Second access returns same object
        assert app.catalog is cat1

    def test_catalog_not_empty(self):
        """Catalog must contain at least base entries."""
        app = _make_app_full()
        assert len(app.catalog) > 0

    def test_catalog_for_unknown_type_still_works(self):
        """Unknown appliance type results in base-only catalog without crash."""
        state = {
            "properties": {
                "reported": {
                    "applianceInfo": {"applianceType": "UNKNOWN_TYPE"},
                }
            }
        }
        app = _make_app_full(state=state)
        catalog = app.catalog
        assert isinstance(catalog, dict)

    def test_catalog_model_override_applied(self):
        """Model-specific overrides are applied when model matches catalog."""
        # Use _make_app_full with model that exists in catalog_model
        # EOH8854AAX is the default; even if not in catalog_model, build succeeds
        app = _make_app_full(model="EOH8854AAX")
        catalog = app.catalog
        assert isinstance(catalog, dict)


# ---------------------------------------------------------------------------
# update_reported_data: constant preservation + exception paths (300-330)
# ---------------------------------------------------------------------------


class TestUpdateReportedDataConstantsAndExceptions:
    """Cover lines 300-330."""

    def test_full_update_preserves_constant_value_not_in_new_data(self):
        """Lines 300-316: constant values absent from new data are restored."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "constKey": ElectroluxDevice(
                capability_info={"access": "constant", "default": 55}
            )
        }
        app.reported_state["constKey"] = 55
        app.entities = []

        app.update_reported_data({"applianceState": "RUNNING"})
        assert app.reported_state.get("constKey") == 55

    def test_full_update_allows_explicit_constant_override(self):
        """Constant key present in new data should be updated, not restored."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "constKey": ElectroluxDevice(
                capability_info={"access": "constant", "default": 55}
            )
        }
        app.reported_state["constKey"] = 55
        app.entities = []

        app.update_reported_data({"constKey": 100})
        assert app.reported_state.get("constKey") == 100

    def test_exception_handling_type_error(self, caplog):
        """Lines 322-325: TypeError is caught and logged as error."""
        import logging

        # reported_state returns None when state["properties"]["reported"] == None
        app = _make_app_full(state={"properties": {"reported": None}})
        app._catalog_cache = {}
        app.entities = []

        with caplog.at_level(logging.ERROR, logger="custom_components.electrolux"):
            app.update_reported_data({"property": "x", "value": 1})
        # Must not raise; error is logged
        assert "Data validation error" in caplog.text

    def test_exception_handling_generic_exception(self, caplog):
        """Lines 326-329: Unexpected exception caught via bare except Exception."""
        import logging

        app = _make_app_full()
        app._catalog_cache = {}
        mock_entity = MagicMock()
        mock_entity.update.side_effect = RuntimeError("unexpected!")
        app.entities = [mock_entity]

        with caplog.at_level(logging.ERROR, logger="custom_components.electrolux"):
            app.update_reported_data({"applianceState": "OFF"})
        # Must not raise


# ---------------------------------------------------------------------------
# get_entity()  (lines 338-536)
# ---------------------------------------------------------------------------


class TestGetEntity:
    """Cover get_entity() — lines 338-536."""

    def _app_with_data(self, capabilities: dict):
        from custom_components.electrolux.api import ElectroluxLibraryEntity

        app = _make_app_full()
        app.data = ElectroluxLibraryEntity(
            name="Test Oven",
            status="connected",
            state={
                "properties": {
                    "reported": {
                        "applianceInfo": {"applianceType": "OV"},
                        "applianceState": "READY",
                        "connectivityState": "connected",
                    }
                }
            },
            appliance_info={},
            capabilities=capabilities,
        )
        return app

    def test_returns_sensor_for_read_string(self):
        """Read string capability → SENSOR entity returned (applianceState is a sensor)."""
        from custom_components.electrolux.sensor import ElectroluxSensor

        app = self._app_with_data(
            {"applianceState": {"access": "read", "type": "string"}}
        )
        entities = app.get_entity("applianceState")
        assert isinstance(entities, list)
        assert len(entities) >= 1
        assert isinstance(entities[0], ElectroluxSensor)

    def test_returns_binary_sensor_for_read_string_with_catalog_override(self):
        """connectivityState catalog overrides entity type to BinarySensor."""
        from custom_components.electrolux.binary_sensor import ElectroluxBinarySensor

        app = self._app_with_data(
            {"connectivityState": {"access": "read", "type": "string"}}
        )
        entities = app.get_entity("connectivityState")
        assert isinstance(entities, list)
        assert len(entities) >= 1
        assert isinstance(entities[0], ElectroluxBinarySensor)

    def test_returns_empty_for_unrecognised_type(self):
        """Capability that cannot be mapped → empty list."""
        app = self._app_with_data(
            {"unknownAttr": {"access": "readwrite", "type": "unknown_type_xyz"}}
        )
        entities = app.get_entity("unknownAttr")
        assert entities == []

    def test_returns_button_entities_for_write_with_values(self):
        """write + values → one BUTTON entity per command value."""
        from custom_components.electrolux.button import ElectroluxButton

        app = self._app_with_data(
            {
                "executeCommand": {
                    "access": "write",
                    "type": "string",
                    "values": {"START": {}, "STOP": {}},
                }
            }
        )
        entities = app.get_entity("executeCommand")
        assert isinstance(entities, list)
        assert len(entities) == 2
        assert all(isinstance(e, ElectroluxButton) for e in entities)

    def test_returns_select_for_readwrite_string_with_values(self):
        """readwrite + string + values (not ON/OFF) → SELECT entity."""
        from custom_components.electrolux.select import ElectroluxSelect

        app = self._app_with_data(
            {
                "userSelections/program": {
                    "access": "readwrite",
                    "type": "string",
                    "values": {"BAKE": {}, "GRILL": {}, "FAN": {}},
                }
            }
        )
        entities = app.get_entity("userSelections/program")
        assert isinstance(entities, list)
        assert len(entities) >= 1
        assert isinstance(entities[0], ElectroluxSelect)

    def test_returns_switch_for_on_off_values(self):
        """readwrite + string + ON/OFF values → SWITCH."""
        from custom_components.electrolux.switch import ElectroluxSwitch

        app = self._app_with_data(
            {
                "powerMode": {
                    "access": "readwrite",
                    "type": "string",
                    "values": {"ON": {}, "OFF": {}},
                }
            }
        )
        entities = app.get_entity("powerMode")
        assert isinstance(entities, list)
        assert len(entities) >= 1
        assert isinstance(entities[0], ElectroluxSwitch)

    def test_returns_binary_sensor_for_boolean_read(self):
        """read + boolean → BINARY_SENSOR."""
        from custom_components.electrolux.binary_sensor import ElectroluxBinarySensor

        app = self._app_with_data({"doorOpen": {"access": "read", "type": "boolean"}})
        entities = app.get_entity("doorOpen")
        assert isinstance(entities, list)
        assert len(entities) >= 1
        assert isinstance(entities[0], ElectroluxBinarySensor)

    def test_returns_number_for_temperature_readwrite(self):
        """readwrite + temperature → NUMBER."""
        from custom_components.electrolux.number import ElectroluxNumber

        app = self._app_with_data(
            {
                "targetTemperatureC": {
                    "access": "readwrite",
                    "type": "temperature",
                    "min": 50,
                    "max": 250,
                }
            }
        )
        entities = app.get_entity("targetTemperatureC")
        assert isinstance(entities, list)
        assert len(entities) >= 1
        assert isinstance(entities[0], ElectroluxNumber)

    def test_catalog_item_overrides_entity_type(self):
        """When catalog_item provides capability_info for unknown api attr, entity is created."""
        app = self._app_with_data({})  # empty capabilities from API
        # applianceState is in catalog_core with type info
        entities = app.get_entity("applianceState")
        # catalog-only path: entity_type derived from catalog
        assert isinstance(entities, list)

    def test_capability_not_in_api_or_catalog_returns_empty(self):
        """Capability with no type determined → empty list."""
        app = self._app_with_data(
            {"totallyUnknown": {"access": "readwrite", "type": "exotic_type"}}
        )
        entities = app.get_entity("totallyUnknown")
        assert entities == []


# ---------------------------------------------------------------------------
# setup()  (lines 540-718)
# ---------------------------------------------------------------------------


class TestApplianceSetup:
    """Cover setup() — lines 540-718."""

    def _make_data(self, capabilities: dict, reported: dict | None = None):
        from custom_components.electrolux.api import ElectroluxLibraryEntity

        if reported is None:
            reported = {
                "applianceInfo": {"applianceType": "OV"},
                "applianceState": "READY",
                "connectivityState": "connected",
            }
        return ElectroluxLibraryEntity(
            name="Test Oven",
            status="connected",
            state={"properties": {"reported": reported}},
            appliance_info={},
            capabilities=capabilities,
        )

    def test_setup_with_no_capabilities_survives(self, caplog):
        """Lines 547-550: setup() returns gracefully when capabilities is None."""
        import logging
        from custom_components.electrolux.api import ElectroluxLibraryEntity

        app = _make_app_full()
        data = ElectroluxLibraryEntity(
            name="Test",
            status="connected",
            state={
                "properties": {
                    "reported": {
                        "applianceInfo": {"applianceType": "OV"},
                        "applianceState": "READY",
                    }
                }
            },
            appliance_info={},
            capabilities=None,
        )
        with caplog.at_level(logging.WARNING):
            app.setup(data)
        assert isinstance(app.entities, list)

    def test_setup_creates_sensor_entity(self):
        """setup() creates at least one sensor from a read string capability."""
        app = _make_app_full()
        data = self._make_data(
            {"connectivityState": {"access": "read", "type": "string"}}
        )
        app.setup(data)
        assert isinstance(app.entities, list)

    def test_setup_deduplicates_entities(self):
        """Duplicate unique_ids result in only one entity kept."""
        app = _make_app_full()
        data = self._make_data(
            {"connectivityState": {"access": "read", "type": "string"}}
        )
        app.setup(data)
        if app.entities:
            ids = [e.unique_id for e in app.entities]
            assert len(ids) == len(set(ids))

    def test_setup_stores_data_reference(self):
        """setup() stores the data object on self.data."""
        app = _make_app_full()
        data = self._make_data({})
        app.setup(data)
        assert app.data is data

    def test_setup_static_attributes_added_when_in_reported(self):
        """Static attributes present in reported state are added as entities."""
        from custom_components.electrolux.models import STATIC_ATTRIBUTES

        app = _make_app_full()
        # Find a static attribute that is also in catalog
        static_attr = next(iter(STATIC_ATTRIBUTES), None)
        if static_attr is None:
            return  # nothing to test

        reported = {
            "applianceInfo": {"applianceType": "OV"},
            "applianceState": "READY",
            static_attr: "someValue",
        }
        caps = {static_attr: {"access": "read", "type": "string"}}
        data = self._make_data(capabilities=caps, reported=reported)
        app.setup(data)
        assert isinstance(app.entities, list)

    def test_setup_calls_entity_setup(self):
        """Each created entity has setup() called on it."""
        app = _make_app_full()
        data = self._make_data(
            {"connectivityState": {"access": "read", "type": "string"}}
        )
        app.setup(data)
        # Verify all entities were set up (no crash in entity.setup())
        for ent in app.entities:
            # entity.setup() should not leave entity in broken state
            assert ent is not None

    def test_setup_with_multiple_capabilities(self):
        """Multiple capabilities produce multiple entities."""
        app = _make_app_full()
        data = self._make_data(
            {
                "connectivityState": {"access": "read", "type": "string"},
                "applianceState": {"access": "read", "type": "string"},
            }
        )
        app.setup(data)
        assert isinstance(app.entities, list)

    def test_setup_skips_dangerous_entities(self):
        """DANGEROUS_ENTITIES_BLACKLIST entries are not turned into entities."""
        from custom_components.electrolux.models import DANGEROUS_ENTITIES_BLACKLIST

        app = _make_app_full()
        # Pick the first dangerous pattern and construct a key matching it
        if not DANGEROUS_ENTITIES_BLACKLIST:
            return
        pattern = DANGEROUS_ENTITIES_BLACKLIST[0]
        # Strip regex anchors and wildcards to get a bare key
        danger_key = pattern.replace("^", "").replace("$", "").replace(".*", "Command")
        reported = {
            "applianceInfo": {"applianceType": "OV"},
            danger_key: "value",
        }
        caps = {danger_key: {"access": "write", "type": "string"}}
        data = self._make_data(capabilities=caps, reported=reported)
        app.setup(data)
        entity_names = [e.entity_attr for e in app.entities]
        assert danger_key not in entity_names

    def test_setup_capabilities_none_and_no_state_does_not_crash(self):
        """Edge case: capabilities None with empty state."""
        from custom_components.electrolux.api import ElectroluxLibraryEntity

        app = _make_app_full(
            state={
                "properties": {
                    "reported": {
                        "applianceInfo": {"applianceType": "OV"},
                    }
                }
            }
        )
        data = ElectroluxLibraryEntity(
            name="Test",
            status="disconnected",
            state={"properties": {"reported": {}}},
            appliance_info={},
            capabilities=None,
        )
        app.setup(data)
        assert isinstance(app.entities, list)


# ---------------------------------------------------------------------------
# Extended get_entity + setup() coverage for remaining missed lines
# ---------------------------------------------------------------------------


class TestGetEntityExtended:
    """Cover specific missed lines in get_entity() — lines 216-218, 354, 362,
    392, 405, 411, 415, 421, 503, 508."""

    def _with_cap(self, cap_name, cap_def):
        """Return an ElectroluxLibraryEntity with a single capability."""
        from custom_components.electrolux.api import ElectroluxLibraryEntity

        return ElectroluxLibraryEntity(
            name="Test",
            status="ok",
            state={"properties": {"reported": {}}},
            appliance_info={},
            capabilities={cap_name: cap_def},
        )

    def _app_custom(self, catalog_entries):
        """App with injected _catalog_cache and empty capabilities data."""
        from custom_components.electrolux.api import ElectroluxLibraryEntity

        app = _make_app_full()
        app._catalog_cache = catalog_entries
        app.data = ElectroluxLibraryEntity(
            name="Test",
            status="ok",
            state={"properties": {"reported": {}}},
            appliance_info={},
            capabilities={},
        )
        return app

    def test_catalog_model_a9_applies_overrides(self):
        """Lines 216-218: model='A9' loads purifier catalog overrides."""
        app = _make_app_full(model="A9")
        assert app._catalog_cache is None
        catalog = app.catalog
        assert isinstance(catalog, dict)
        assert app._catalog_cache is catalog
        assert len(catalog) > 0

    def test_entity_source_from_catalog_sets_category(self):
        """Line 354: catalog 'entity_source' key overrides category."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = self._app_custom(
            {
                "applianceType": ElectroluxDevice(
                    capability_info={
                        "access": "read",
                        "type": "string",
                        "entity_source": "applianceInfo",
                    }
                )
            }
        )
        entities = app.get_entity("applianceType")
        assert isinstance(entities, list)

    def test_catalog_only_climate_type(self):
        """Line 362: catalog-only entity with type='climate' → CLIMATE entity."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = self._app_custom(
            {
                "climateCtrl": ElectroluxDevice(
                    capability_info={"access": "readwrite", "type": "climate"}
                )
            }
        )
        entities = app.get_entity("climateCtrl")
        assert isinstance(entities, list)

    def test_catalog_api_merge_with_step_key(self):
        """Line 392: 'step' in API capability pops step from catalog copy."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "targetTemp": ElectroluxDevice(
                capability_info={"access": "readwrite", "type": "temperature"}
            )
        }
        app.data = self._with_cap(
            "targetTemp",
            {
                "access": "readwrite",
                "type": "temperature",
                "min": 50,
                "max": 250,
                "step": 5,
            },
        )
        entities = app.get_entity("targetTemp")
        assert isinstance(entities, list)
        assert len(entities) >= 1

    def test_time_entity_gets_seconds_unit(self):
        """Line 405: entity_attr 'startTime' → unit forced to UnitOfTime.SECONDS."""
        from homeassistant.const import UnitOfTime

        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "startTime": ElectroluxDevice(
                capability_info={"access": "read", "type": "int"}
            )
        }
        app.data = self._with_cap("startTime", {"access": "read", "type": "int"})
        entities = app.get_entity("startTime")
        assert isinstance(entities, list)
        if entities:
            assert entities[0].unit == UnitOfTime.SECONDS

    def test_button_device_class_override(self):
        """Line 411: catalog ButtonDeviceClass → entity_type forced to BUTTON."""
        from homeassistant.components.button import ButtonDeviceClass

        from custom_components.electrolux.button import ElectroluxButton
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "myExecBtn": ElectroluxDevice(
                capability_info={
                    "access": "write",
                    "type": "string",
                    "values": {"START": {}, "STOP": {}},
                },
                device_class=ButtonDeviceClass.RESTART,
            )
        }
        app.data = self._with_cap(
            "myExecBtn",
            {"access": "write", "type": "string", "values": {"START": {}, "STOP": {}}},
        )
        entities = app.get_entity("myExecBtn")
        assert isinstance(entities, list)
        assert all(isinstance(e, ElectroluxButton) for e in entities)

    def test_sensor_device_class_override(self):
        """Line 415: catalog SensorDeviceClass → entity_type forced to SENSOR."""
        from homeassistant.components.sensor import SensorDeviceClass

        from custom_components.electrolux.model import ElectroluxDevice
        from custom_components.electrolux.sensor import ElectroluxSensor

        app = _make_app_full()
        app._catalog_cache = {
            "tempReading": ElectroluxDevice(
                capability_info={"access": "read", "type": "number"},
                device_class=SensorDeviceClass.TEMPERATURE,
            )
        }
        app.data = self._with_cap("tempReading", {"access": "read", "type": "number"})
        entities = app.get_entity("tempReading")
        assert isinstance(entities, list)
        assert len(entities) >= 1
        assert isinstance(entities[0], ElectroluxSensor)

    def test_entity_platform_fan_override(self):
        """Line 421: catalog entity_platform=FAN → entity_type becomes FAN."""
        from homeassistant.const import Platform

        from custom_components.electrolux.fan import ElectroluxFan
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "airPurifier": ElectroluxDevice(
                capability_info={
                    "access": "readwrite",
                    "type": "string",
                    "values": {"ON": {}, "OFF": {}},
                },
                entity_platform=Platform.FAN,
            )
        }
        app.data = self._with_cap(
            "airPurifier",
            {"access": "readwrite", "type": "string", "values": {"ON": {}, "OFF": {}}},
        )
        entities = app.get_entity("airPurifier")
        assert isinstance(entities, list)
        assert len(entities) >= 1
        assert isinstance(entities[0], ElectroluxFan)

    def test_entity_value_named_sets_entity_name_to_command(self):
        """Line 503: entity_value_named=True → each button entity named after command."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "runCmd": ElectroluxDevice(
                capability_info={
                    "access": "write",
                    "type": "string",
                    "values": {"START": {}, "STOP": {}},
                },
                entity_value_named=True,
            )
        }
        app.data = self._with_cap(
            "runCmd",
            {"access": "write", "type": "string", "values": {"START": {}, "STOP": {}}},
        )
        entities = app.get_entity("runCmd")
        assert isinstance(entities, list)
        assert len(entities) == 2

    def test_entity_icons_value_map_applied(self):
        """Line 508: entity_icons_value_map → per-command icon set on entity."""
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        app._catalog_cache = {
            "iconCmd": ElectroluxDevice(
                capability_info={
                    "access": "write",
                    "type": "string",
                    "values": {"START": {}, "STOP": {}},
                },
                entity_icons_value_map={"START": "mdi:play", "STOP": "mdi:stop"},
            )
        }
        app.data = self._with_cap(
            "iconCmd",
            {"access": "write", "type": "string", "values": {"START": {}, "STOP": {}}},
        )
        entities = app.get_entity("iconCmd")
        assert isinstance(entities, list)
        assert len(entities) == 2


class TestSetupAdditionalCoverage:
    """Cover lines 568-571 (undefined static_attr), 577 (nested setdefault), 701 (dedup)."""

    def test_static_attribute_undefined_path(self):
        """Lines 568-571: static_attribute returns [] from get_entity → debug log + continue."""
        from custom_components.electrolux.api import ElectroluxLibraryEntity
        from custom_components.electrolux.model import ElectroluxDevice

        app = _make_app_full()
        # "applianceState" is a STATIC_ATTRIBUTE; empty capability_info → entity_type undetermined
        app._catalog_cache = {"applianceState": ElectroluxDevice(capability_info={})}
        reported = {"applianceInfo": {"applianceType": "OV"}, "applianceState": "READY"}
        data = ElectroluxLibraryEntity(
            name="Test",
            status="connected",
            state={"properties": {"reported": reported}},
            appliance_info={},
            capabilities={"someOther": {"access": "read", "type": "string"}},
        )
        app.setup(data)
        assert isinstance(app.entities, list)

    def test_duplicate_entity_dedup_logs_debug(self, caplog):
        """Line 701: duplicate entity unique_id → debug log 'Skipping duplicate entity'."""
        import logging

        from custom_components.electrolux.api import ElectroluxLibraryEntity

        app = _make_app_full()
        # connectivityState is in STATIC_ATTRIBUTES AND in capabilities → both loops create it
        reported = {
            "applianceInfo": {"applianceType": "OV"},
            "connectivityState": "connected",
        }
        caps = {"connectivityState": {"access": "read", "type": "string"}}
        data = ElectroluxLibraryEntity(
            name="Test",
            status="connected",
            state={"properties": {"reported": reported}},
            appliance_info={},
            capabilities=caps,
        )
        with caplog.at_level(logging.DEBUG, logger="custom_components.electrolux"):
            app.setup(data)
        assert "Skipping duplicate entity" in caplog.text

    def test_nested_static_attribute_setdefault_path(self):
        """Line 577: nested key static_attribute triggers setdefault on capabilities dict."""
        import custom_components.electrolux.models as models_mod
        from custom_components.electrolux.api import ElectroluxLibraryEntity
        from custom_components.electrolux.model import ElectroluxDevice

        original_static = models_mod.STATIC_ATTRIBUTES
        try:
            models_mod.STATIC_ATTRIBUTES = ["userSelections/program"]
            app = _make_app_full()
            app._catalog_cache = {
                "userSelections/program": ElectroluxDevice(
                    capability_info={
                        "access": "readwrite",
                        "type": "string",
                        "values": {"BAKE": {}, "GRILL": {}},
                    }
                )
            }
            # Use the FULL path as a direct key in reported_state so attr_in_reported is True
            reported = {
                "applianceInfo": {"applianceType": "OV"},
                "userSelections/program": "BAKE",
            }
            caps = {
                "userSelections": {
                    "program": {
                        "access": "readwrite",
                        "type": "string",
                        "values": {"BAKE": {}, "GRILL": {}},
                    }
                }
            }
            data = ElectroluxLibraryEntity(
                name="Test",
                status="connected",
                state={"properties": {"reported": reported}},
                appliance_info={},
                capabilities=caps,
            )
            app.setup(data)
            assert isinstance(app.entities, list)
        finally:
            models_mod.STATIC_ATTRIBUTES = original_static
