"""Test binary sensor platform for Electrolux."""

from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.electrolux.binary_sensor import (
    ElectroluxBinarySensor,
    infer_boolean_from_enum,
)
from custom_components.electrolux.const import BINARY_SENSOR


class TestInferBooleanFromEnum:
    """Test the infer_boolean_from_enum helper function."""

    def test_negative_patterns(self):
        """Test negative patterns return False."""
        assert infer_boolean_from_enum("NOT_INSERTED") is False
        assert infer_boolean_from_enum("NOT_AVAILABLE") is False
        assert infer_boolean_from_enum("NO_WATER") is False
        assert infer_boolean_from_enum("STEAM_TANK_EMPTY") is False
        assert infer_boolean_from_enum("DISCONNECTED") is False
        assert infer_boolean_from_enum("DISABLED") is False
        assert infer_boolean_from_enum("UNAVAILABLE") is False

    def test_positive_patterns(self):
        """Test positive patterns return True."""
        assert infer_boolean_from_enum("INSERTED") is True
        assert infer_boolean_from_enum("INSTALLED") is True
        assert infer_boolean_from_enum("STEAM_TANK_FULL") is True
        assert infer_boolean_from_enum("WATER_FULL") is True
        assert infer_boolean_from_enum("CONNECTED") is True
        assert infer_boolean_from_enum("ENABLED") is True
        assert infer_boolean_from_enum("AVAILABLE") is True
        assert infer_boolean_from_enum("DETECTED") is True

    def test_case_insensitive(self):
        """Test function is case insensitive."""
        assert infer_boolean_from_enum("not_inserted") is False
        assert infer_boolean_from_enum("inserted") is True
        assert infer_boolean_from_enum("installed") is True
        assert infer_boolean_from_enum("Not_Available") is False

    def test_underscore_handling(self):
        """Test underscores are handled properly."""
        assert infer_boolean_from_enum("NOT_INSERTED") is False
        assert infer_boolean_from_enum("STEAM_TANK_EMPTY") is False
        assert infer_boolean_from_enum("TANK_FULL") is True

    def test_unknown_defaults_to_true(self):
        """Test unknown values default to True."""
        assert infer_boolean_from_enum("UNKNOWN_STATE") is True
        assert infer_boolean_from_enum("SOME_VALUE") is True


class TestElectroluxBinarySensor:
    """Test the Electrolux Binary Sensor entity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.config_entry = MagicMock()
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        """Create a mock capability."""
        return {
            "access": "read",
            "type": "boolean",
        }

    @pytest.fixture
    def binary_sensor_entity(self, mock_coordinator, mock_capability):
        """Create a test binary sensor entity."""
        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Test Binary Sensor",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="test_binary_sensor",
            entity_attr="testAttr",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
        )
        entity.appliance_status = {"properties": {"reported": {"testAttr": True}}}
        entity.reported_state = {"testAttr": True}
        return entity

    def test_entity_domain(self, binary_sensor_entity):
        """Test entity domain property."""
        assert binary_sensor_entity.entity_domain == "binary_sensor"

    def test_name_with_friendly_name(self, mock_coordinator, mock_capability):
        """Test name property uses friendly name mapping."""
        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Original Name",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="ovwater_tank_empty",  # This has a friendly name mapping
            entity_attr="waterTankEmpty",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
        )
        assert entity.name == "Water Tank Status"

    def test_name_fallback_to_catalog(self, mock_coordinator, mock_capability):
        """Test name property falls back to catalog friendly name."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            friendly_name="Catalog Friendly Name",
        )

        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Original Name",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="test_sensor",
            entity_attr="testAttr",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        assert entity.name == "Catalog friendly name"

    def test_invert_false_by_default(self, binary_sensor_entity):
        """Test invert property defaults to False."""
        assert binary_sensor_entity.invert is False

    def test_invert_from_catalog(self, mock_coordinator, mock_capability):
        """Test invert property from catalog entry."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            state_invert=True,
        )

        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Test Binary Sensor",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="test_binary_sensor",
            entity_attr="testAttr",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        assert entity.invert is True

    def test_is_on_boolean_true(self, binary_sensor_entity):
        """Test is_on returns True for boolean True."""
        binary_sensor_entity.reported_state = {"testAttr": True}
        assert binary_sensor_entity.is_on is True

    def test_is_on_boolean_false(self, binary_sensor_entity):
        """Test is_on returns False for boolean False."""
        binary_sensor_entity.appliance_status = {
            "properties": {"reported": {"testAttr": False}}
        }
        binary_sensor_entity.reported_state = {"testAttr": False}
        assert binary_sensor_entity.is_on is False

    def test_is_on_string_conversion(self, binary_sensor_entity):
        """Test is_on converts string values using string_to_boolean."""
        binary_sensor_entity.appliance_status = {
            "properties": {"reported": {"testAttr": "ON"}}
        }
        binary_sensor_entity.reported_state = {"testAttr": "ON"}
        assert binary_sensor_entity.is_on is True

    def test_is_on_with_invert(self, mock_coordinator, mock_capability):
        """Test is_on with invert enabled."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            state_invert=True,
        )

        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Test Binary Sensor",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="test_binary_sensor",
            entity_attr="testAttr",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        entity.appliance_status = {"properties": {"reported": {"testAttr": True}}}
        entity.reported_state = {"testAttr": True}
        assert entity.is_on is False  # Inverted

    def test_is_on_constant_access(self, mock_coordinator):
        """Test is_on with constant access capability."""
        capability = {
            "access": "constant",
            "type": "boolean",
            "default": True,
        }
        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Test Binary Sensor",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="test_binary_sensor",
            entity_attr="testAttr",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
        )
        assert entity.is_on is True

    def test_is_on_food_probe_insertion_state(self, mock_coordinator, mock_capability):
        """Test generic enum handling for food probe insertion state."""
        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Food Probe",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="foodProbeInsertionState",
            entity_attr="foodProbeInsertionState",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
        )
        entity.extract_value = MagicMock(return_value="INSERTED")
        assert entity.is_on is True

        entity.extract_value = MagicMock(return_value="NOT_INSERTED")
        assert entity.is_on is False

    def test_is_on_water_tank_empty(self, mock_coordinator, mock_capability):
        """Test special handling for water tank empty sensor."""
        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Water Tank Status",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="waterTankEmpty",
            entity_attr="waterTankEmpty",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
        )
        # Set entity_key for special handling check
        entity.entity_key = "watertankempty"

        # Tank is empty - should be True (tank IS empty)
        entity.reported_state = {"waterTankEmpty": "STEAM_TANK_EMPTY"}
        assert entity.is_on is True

        # Tank is full - should be False (tank is NOT empty)
        entity.reported_state = {"waterTankEmpty": "STEAM_TANK_FULL"}
        assert entity.is_on is False

    def test_is_on_water_tray_insertion_state(self, mock_coordinator, mock_capability):
        """Test generic enum handling for water tray insertion state sensor."""
        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Water Tray",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="waterTrayInsertionState",
            entity_attr="waterTrayInsertionState",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
        )
        # Tray is inserted - should be On
        entity.extract_value = MagicMock(return_value="INSERTED")
        assert entity.is_on is True

        # Tray is not inserted - should be Off
        entity.extract_value = MagicMock(return_value="NOT_INSERTED")
        assert entity.is_on is False

    def test_is_on_generic_enum_handling(self, mock_coordinator, mock_capability):
        """Test generic enum value handling for unknown appliances."""
        # Test with an unknown binary sensor that has enum values
        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Filter Status",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="filterInstalled",  # Not in special handling list
            entity_attr="filterInstalled",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
        )

        # Test negative patterns - mock extract_value to return enum strings
        entity.extract_value = MagicMock(return_value="NOT_AVAILABLE")
        assert entity.is_on is False

        entity.extract_value = MagicMock(return_value="DISCONNECTED")
        assert entity.is_on is False

        entity.extract_value = MagicMock(return_value="FILTER_EMPTY")
        assert entity.is_on is False

        # Test positive patterns
        entity.extract_value = MagicMock(return_value="INSTALLED")
        assert entity.is_on is True

        entity.extract_value = MagicMock(return_value="CONNECTED")
        assert entity.is_on is True

        entity.extract_value = MagicMock(return_value="FILTER_FULL")
        assert entity.is_on is True

        # Test unknown values default to True
        entity.extract_value = MagicMock(return_value="UNKNOWN_STATE")
        assert entity.is_on is True

    def test_is_on_with_state_mapping(self, mock_coordinator, mock_capability):
        """Test is_on with state mapping fallback."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            state_mapping="testAttr",
        )

        entity = ElectroluxBinarySensor(
            coordinator=mock_coordinator,
            name="Test Binary Sensor",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name="test_binary_sensor",
            entity_attr="testAttr",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        entity.extract_value = MagicMock(return_value=None)
        entity.get_state_attr = MagicMock(return_value=True)
        assert entity.is_on is True

    def test_is_on_none_value_with_cached_value(self, binary_sensor_entity):
        """Test is_on uses cached value when extract_value returns None."""
        binary_sensor_entity.extract_value = MagicMock(return_value=None)
        binary_sensor_entity._cached_value = False
        assert binary_sensor_entity.is_on is False


class TestBinarySensorMissingPaths:
    """Tests for previously uncovered binary sensor paths."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.config_entry = MagicMock()
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {"access": "read", "type": "boolean"}

    def _make_entity(
        self,
        coordinator,
        capability,
        entity_attr,
        entity_name,
        catalog_entry=None,
        name="Test",
    ):
        entity = ElectroluxBinarySensor(
            coordinator=coordinator,
            name=name,
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BINARY_SENSOR,
            entity_name=entity_name,
            entity_attr=entity_attr,
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        entity.is_connected = MagicMock(return_value=True)
        return entity

    def test_name_returns_self_name_when_no_friendly_name_and_no_catalog(
        self, mock_coordinator, mock_capability
    ):
        """Test name returns _name when entity_name not in FRIENDLY_NAMES and no catalog_entry."""
        entity = self._make_entity(
            mock_coordinator,
            mock_capability,
            "unknownAttr",
            "unknown_entity",
            name="My Sensor",
        )
        assert entity.name == "My Sensor"

    def test_is_on_returns_none_when_offline(self, mock_coordinator, mock_capability):
        """Test is_on returns None when appliance is offline (entity_attr != connectivityState)."""
        entity = self._make_entity(
            mock_coordinator, mock_capability, "someAttr", "some_entity"
        )
        entity.is_connected = MagicMock(return_value=False)
        assert entity.is_on is None

    def test_is_on_connectivity_state_not_blocked_offline(
        self, mock_coordinator, mock_capability
    ):
        """Test connectivityState sensor is NOT blocked when offline (line 133 bypass)."""
        entity = self._make_entity(
            mock_coordinator, mock_capability, "connectivityState", "some_entity"
        )
        entity.is_connected = MagicMock(return_value=False)
        entity.extract_value = MagicMock(return_value="disconnected")
        # should not return None — connectivityState is special
        result = entity.is_on
        assert result is not None

    def test_is_on_food_probe_supported_present(
        self, mock_coordinator, mock_capability
    ):
        """Test is_on for foodProbeSupported when foodProbeInsertionState is in reported state."""
        entity = self._make_entity(
            mock_coordinator, mock_capability, "foodProbeSupported", "test"
        )
        entity._reported_state_cache = {"foodProbeInsertionState": "INSERTED"}
        entity.extract_value = MagicMock(return_value=None)
        assert entity.is_on is True

    def test_is_on_food_probe_supported_absent(self, mock_coordinator, mock_capability):
        """Test is_on for foodProbeSupported when foodProbeInsertionState is absent."""
        entity = self._make_entity(
            mock_coordinator, mock_capability, "foodProbeSupported", "test"
        )
        entity._reported_state_cache = {}
        entity.extract_value = MagicMock(return_value=None)
        assert entity.is_on is False

    def test_is_on_water_tank_empty_no_live_value(
        self, mock_coordinator, mock_capability
    ):
        """Test is_on for watertankempty returns False when waterTankEmpty not in reported_state."""
        entity = self._make_entity(
            mock_coordinator, mock_capability, "waterTankEmpty", "watertankempty"
        )
        # entity_key = "watertankempty" (lowercased waterTankEmpty)
        entity._reported_state_cache = {}  # No waterTankEmpty key
        entity.extract_value = MagicMock(return_value=None)
        assert entity.is_on is False
