"""Test Entity Availability Rules for Electrolux integration."""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.const import NUMBER, SELECT
from custom_components.electrolux.number import ElectroluxNumber
from custom_components.electrolux.select import ElectroluxSelect


class TestEntityAvailabilityRules:
    """Test Entity Availability Rules - entities must remain available but constrained when not supported by program."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        return coordinator

    @pytest.fixture
    def mock_capability_temperature(self):
        """Create a mock temperature capability."""
        return {
            "access": "readwrite",
            "type": "temperature",
            "min": 30,
            "max": 250,
            "step": 5,
            "default": 180,
        }

    @pytest.fixture
    def mock_capability_select(self):
        """Create a mock select capability."""
        return {
            "access": "readwrite",
            "type": "string",
            "values": {
                "option1": {"label": "Option 1"},
                "option2": {"label": "Option 2"},
                "option3": {"label": "Option 3"},
            },
        }

    # ============================================================================
    # NUMBER ENTITY TESTS - Clamping Behavior
    # ============================================================================

    def test_number_entity_always_available_regardless_of_program_support(
        self, mock_coordinator, mock_capability_temperature
    ):
        """Test that number entities are always available, even when not supported by program."""
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=mock_capability_temperature,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"program": "unsupported_program"}}
        }
        entity.reported_state = {"program": "unsupported_program"}

        # Mock _is_supported_by_program to return False
        entity._is_supported_by_program = MagicMock(return_value=False)

        # Entity should still be available
        assert entity.available is True

    def test_number_entity_shows_minimum_value_when_not_supported_by_program(
        self, mock_coordinator, mock_capability_temperature
    ):
        """Test that number entities show minimum value when not supported by program."""
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=mock_capability_temperature,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"program": "unsupported_program"}}
        }
        entity.reported_state = {"program": "unsupported_program"}

        # Mock _is_supported_by_program to return False
        entity._is_supported_by_program = MagicMock(return_value=False)

        # Should return minimum value (30) when not supported
        assert entity.native_value == 30.0

    def test_number_entity_shows_zero_fallback_when_no_minimum_defined(
        self, mock_coordinator
    ):
        """Test that number entities show 0 when no minimum is defined and not supported by program."""
        capability_no_min = {
            "access": "readwrite",
            "type": "number",
            "max": 100,
            "step": 1,
        }

        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Generic Number",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="generic_number",
            entity_attr="genericAttr",
            entity_source=None,
            capability=capability_no_min,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:counter",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"program": "unsupported_program"}}
        }
        entity.reported_state = {"program": "unsupported_program"}

        # Mock _is_supported_by_program to return False
        entity._is_supported_by_program = MagicMock(return_value=False)

        # Should return 0.0 as fallback when no minimum defined
        assert entity.native_value == 0.0

    @pytest.mark.asyncio
    async def test_number_entity_prevents_modification_when_not_supported_by_program(
        self, mock_coordinator, mock_capability_temperature
    ):
        """Test that number entities prevent modification when not supported by program."""
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=mock_capability_temperature,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"program": "unsupported_program"}}
        }
        entity.reported_state = {"program": "unsupported_program"}

        # Mock _is_supported_by_program to return False
        entity._is_supported_by_program = MagicMock(return_value=False)

        # Attempting to set value should raise HomeAssistantError
        with pytest.raises(
            HomeAssistantError, match="not supported by current program"
        ):
            await entity.async_set_native_value(200.0)

    @pytest.mark.asyncio
    async def test_food_probe_temperature_prevents_modification_when_not_supported_by_program(
        self, mock_coordinator
    ):
        """Test that food probe temperature entities prevent modification when not supported by program."""
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Food Probe Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="food_probe_temperature",
            entity_attr="targetFoodProbeTemperatureC",
            entity_source=None,
            capability={
                "access": "readwrite",
                "type": "temperature",
                "min": 30,
                "max": 99,
                "step": 1,
            },
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer-probe",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"program": "DOUGH_PROVING"}}
        }
        entity.reported_state = {"program": "DOUGH_PROVING"}

        # Mock _is_supported_by_program to return False
        entity._is_supported_by_program = MagicMock(return_value=False)

        # Attempting to set value should raise HomeAssistantError with specific message
        with pytest.raises(
            HomeAssistantError,
            match="Target food probe temperature control not supported by current program 'DOUGH_PROVING'",
        ):
            await entity.async_set_native_value(50.0)

    # ============================================================================
    # SELECT ENTITY TESTS - Empty Selection Behavior
    # ============================================================================

    def test_select_entity_always_available_regardless_of_program_support(
        self, mock_coordinator, mock_capability_select
    ):
        """Test that select entities are always available, even when not supported by program."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            name="Test Select",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="testSelect",
            entity_source=None,
            capability=mock_capability_select,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:menu",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"program": "unsupported_program"}}
        }
        entity.reported_state = {"program": "unsupported_program"}

        # Mock _is_supported_by_program to return False
        entity._is_supported_by_program = MagicMock(return_value=False)

        # Entity should still be available
        assert entity.available is True

    def test_select_entity_shows_empty_selection_when_not_supported_by_program(
        self, mock_coordinator, mock_capability_select
    ):
        """Test that select entities show empty selection when not supported by program."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            name="Test Select",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="testSelect",
            entity_source=None,
            capability=mock_capability_select,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:menu",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"program": "unsupported_program"}}
        }
        entity.reported_state = {"program": "unsupported_program"}

        # Mock _is_supported_by_program to return False
        entity._is_supported_by_program = MagicMock(return_value=False)

        # Should show empty selection when not supported
        assert entity.current_option == ""

    @pytest.mark.asyncio
    async def test_select_entity_prevents_selection_when_not_supported_by_program(
        self, mock_coordinator, mock_capability_select
    ):
        """Test that select entities prevent selection when not supported by program."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            name="Test Select",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="testSelect",
            entity_source=None,
            capability=mock_capability_select,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:menu",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"program": "unsupported_program"}}
        }
        entity.reported_state = {"program": "unsupported_program"}

        # Mock _is_supported_by_program to return False
        entity._is_supported_by_program = MagicMock(return_value=False)

        # Attempting to select option should raise HomeAssistantError
        with pytest.raises(
            HomeAssistantError, match="not supported by current program"
        ):
            await entity.async_select_option("Option 1")

    def test_select_entity_shows_filtered_options_based_on_program_constraints(
        self, mock_coordinator, mock_capability_select
    ):
        """Test that select entities filter options based on program constraints."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            name="Test Select",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="testSelect",
            entity_source=None,
            capability=mock_capability_select,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:menu",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"program": "test_program"}}
        }
        entity.reported_state = {"program": "test_program"}

        # Mock program constraints to only allow option1 and option2
        entity._get_program_constraint = MagicMock(return_value=["option1", "option2"])

        # Should only show allowed options
        options = entity.options
        assert "Option 1" in options
        assert "Option 2" in options
        assert "Option 3" not in options

    # ============================================================================
    # INTEGRATION TESTS - Multiple Entity Types
    # ============================================================================

    def test_multiple_number_entities_clamped_when_program_not_supported(
        self, mock_coordinator
    ):
        """Test that multiple number entities are properly clamped when not supported."""
        # Test targetTemperatureC
        temp_entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability={
                "access": "readwrite",
                "type": "temperature",
                "min": 50,
                "max": 250,
            },
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        temp_entity.hass = mock_coordinator.hass
        temp_entity.appliance_status = {
            "properties": {"reported": {"program": "unsupported"}}
        }
        temp_entity.reported_state = {"program": "unsupported"}
        temp_entity._is_supported_by_program = MagicMock(return_value=False)

        # Test targetFoodProbeTemperatureC
        probe_entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Food Probe Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="food_probe_temperature",
            entity_attr="targetFoodProbeTemperatureC",
            entity_source=None,
            capability={
                "access": "readwrite",
                "type": "temperature",
                "min": 30,
                "max": 99,
            },
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer-probe",
        )
        probe_entity.hass = mock_coordinator.hass
        probe_entity.appliance_status = {
            "properties": {"reported": {"program": "unsupported"}}
        }
        probe_entity.reported_state = {"program": "unsupported"}
        probe_entity._is_supported_by_program = MagicMock(return_value=False)

        # Both should be available and show minimum values
        assert temp_entity.available is True
        assert temp_entity.native_value == 50.0

        assert probe_entity.available is True
        assert probe_entity.native_value == 30.0

    def test_entities_remain_available_when_program_changes(
        self, mock_coordinator, mock_capability_temperature, mock_capability_select
    ):
        """Test that entities remain available when program changes."""
        # Create entities
        temp_entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=mock_capability_temperature,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        temp_entity.hass = mock_coordinator.hass

        select_entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            name="Test Select",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="testSelect",
            entity_source=None,
            capability=mock_capability_select,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:menu",
        )
        select_entity.hass = mock_coordinator.hass

        # Test with program that doesn't support entities
        appliance_status_unsupported = {
            "properties": {"reported": {"program": "unsupported_program"}}
        }
        temp_entity.appliance_status = appliance_status_unsupported
        temp_entity.reported_state = {"program": "unsupported_program"}
        temp_entity._is_supported_by_program = MagicMock(return_value=False)

        select_entity.appliance_status = appliance_status_unsupported
        select_entity.reported_state = {"program": "unsupported_program"}
        select_entity._is_supported_by_program = MagicMock(return_value=False)

        # Entities should remain available
        assert temp_entity.available is True
        assert select_entity.available is True

        # Should show constrained values
        assert temp_entity.native_value == 30.0  # min value
        assert select_entity.current_option == ""  # empty selection

        # Test with program that supports entities
        appliance_status_supported = {
            "properties": {
                "reported": {"program": "supported_program", "targetTemperatureC": 200}
            }
        }
        temp_entity.appliance_status = appliance_status_supported
        temp_entity.reported_state = {
            "program": "supported_program",
            "targetTemperatureC": 200,
        }
        temp_entity._is_supported_by_program = MagicMock(return_value=True)

        select_entity.appliance_status = appliance_status_supported
        select_entity.reported_state = {
            "program": "supported_program",
            "testSelect": "option1",
        }
        select_entity._is_supported_by_program = MagicMock(return_value=True)

        # Entities should still be available
        assert temp_entity.available is True
        assert select_entity.available is True

        # Should show actual values
        assert temp_entity.native_value == 200.0
        assert select_entity.current_option == "Option 1"
