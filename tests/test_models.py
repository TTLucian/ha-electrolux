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
