"""Test number platform for Electrolux."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.number import NumberDeviceClass, NumberMode
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.const import NUMBER
from custom_components.electrolux.number import ElectroluxNumber


class TestElectroluxNumber:
    """Test the Electrolux Number entity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        """Create a mock capability."""
        return {
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 100,
            "step": 1,
            "default": 50,
        }

    @pytest.fixture
    def number_entity(self, mock_coordinator, mock_capability):
        """Create a test number entity."""
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Test Number",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test_number",
            entity_attr="testAttr",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.appliance_status = {
            "properties": {"reported": {"testAttr": 75, "remoteControl": "ENABLED"}}
        }
        entity.reported_state = {"testAttr": 75, "remoteControl": "ENABLED"}
        return entity

    def test_entity_domain(self, number_entity):
        """Test entity domain property."""
        assert number_entity.entity_domain == "number"

    def test_mode_box_for_time_entities(self, mock_coordinator, mock_capability):
        """Test that time entities use BOX mode."""
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Start Time",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="start_time",
            entity_attr="startTime",
            entity_source=None,
            capability=mock_capability,
            unit=UnitOfTime.MINUTES,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:clock-start",
        )
        assert entity.mode == NumberMode.BOX

    def test_mode_slider_for_non_time_entities(self, number_entity):
        """Test that non-time entities use SLIDER mode."""
        assert number_entity.mode == NumberMode.SLIDER

    def test_device_class_temperature(self, mock_coordinator):
        """Test temperature device class mapping."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        assert entity.device_class == NumberDeviceClass.TEMPERATURE

    def test_native_value_basic(self, number_entity):
        """Test basic native value retrieval."""
        assert number_entity.native_value == 75

    def test_native_value_time_conversion_target_duration(self, mock_coordinator):
        """Test time conversion for targetDuration (seconds to minutes)."""
        capability = {
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 86400,  # 24 hours in seconds
            "step": 60,
            "default": 3600,
        }
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Duration",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_duration",
            entity_attr="targetDuration",
            entity_source=None,
            capability=capability,
            unit=UnitOfTime.SECONDS,  # Updated to SECONDS
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timelapse",
        )
        entity.appliance_status = {
            "properties": {"reported": {"targetDuration": 3600}}
        }  # 3600 seconds
        entity.reported_state = {"targetDuration": 3600}
        assert entity.native_value == 60  # 60 minutes

    def test_native_value_time_conversion_start_time(self, mock_coordinator):
        """Test time conversion for startTime (seconds to minutes)."""
        capability = {
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 86400,  # 24 hours in seconds
            "step": 60,
            "default": 0,
        }
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Start Time",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="start_time",
            entity_attr="startTime",
            entity_source=None,
            capability=capability,
            unit=UnitOfTime.SECONDS,  # Updated to SECONDS
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:clock-start",
        )
        entity.appliance_status = {
            "properties": {"reported": {"startTime": 1800}}
        }  # 1800 seconds
        entity.reported_state = {"startTime": 1800}
        assert entity.native_value == 30  # 30 minutes

    def test_native_value_start_time_invalid(self, mock_coordinator, mock_capability):
        """Test startTime returns None for invalid time (-1)."""
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Start Time",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="start_time",
            entity_attr="startTime",
            entity_source=None,
            capability=mock_capability,
            unit=UnitOfTime.SECONDS,  # Updated to SECONDS
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:clock-start",
        )
        entity.appliance_status = {"properties": {"reported": {"startTime": -1}}}
        entity.reported_state = {"startTime": -1}
        assert entity.native_value is None

    def test_native_value_food_probe_not_inserted(self, mock_coordinator):
        """Test food probe temperature returns 0 when not inserted."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Food Probe Temp",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="food_probe_temp",
            entity_attr="targetFoodProbeTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class="temperature",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer-probe",
        )
        entity.appliance_status = {
            "properties": {"reported": {"foodProbeInsertionState": "NOT_INSERTED"}}
        }
        entity.reported_state = {"foodProbeInsertionState": "NOT_INSERTED"}
        assert entity.native_value == 0.0

    def test_native_max_value_program_specific(self, number_entity):
        """Test max value from program-specific constraints."""
        number_entity._get_program_constraint = MagicMock(return_value=80)
        assert number_entity.native_max_value == 80

    def test_native_max_value_capability_fallback(self, number_entity):
        """Test max value from capability fallback."""
        number_entity._get_program_constraint = MagicMock(return_value=None)
        assert number_entity.native_max_value == 100

    def test_native_max_value_time_conversion(self, mock_coordinator):
        """Test max value time conversion for time entities."""
        capability = {
            "access": "readwrite",
            "type": "number",
            "max": 7200,
        }  # 7200 seconds
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Time Entity",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="time_entity",
            entity_attr="testTime",
            entity_source=None,
            capability=capability,
            unit=UnitOfTime.SECONDS,  # Updated to SECONDS
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:clock",
        )
        entity._get_program_constraint = MagicMock(return_value=None)
        assert entity.native_max_value == 120  # 7200 seconds = 120 minutes

    def test_native_min_value_program_specific(self, number_entity):
        """Test min value from program-specific constraints."""
        number_entity._get_program_constraint = MagicMock(return_value=20)
        assert number_entity.native_min_value == 20

    def test_native_min_value_capability_fallback(self, number_entity):
        """Test min value from capability fallback."""
        number_entity._get_program_constraint = MagicMock(return_value=None)
        number_entity.capability = {"min": 10}
        assert number_entity.native_min_value == 10

    def test_native_step_program_specific(self, number_entity):
        """Test step value from program-specific constraints."""
        number_entity._get_program_constraint = MagicMock(return_value=5)
        assert number_entity.native_step == 5

    def test_native_step_time_conversion(self, mock_coordinator):
        """Test step value time conversion for time entities."""
        capability = {
            "access": "readwrite",
            "type": "number",
            "step": 300,
        }  # 300 seconds
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Time Entity",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="time_entity",
            entity_attr="testTime",
            entity_source=None,
            capability=capability,
            unit=UnitOfTime.SECONDS,  # Updated to SECONDS
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:clock",
        )
        entity._get_program_constraint = MagicMock(return_value=None)
        assert entity.native_step == 5  # 300 seconds = 5 minutes

    @pytest.mark.asyncio
    async def test_async_set_native_value_basic(
        self, mock_coordinator, mock_capability
    ):
        """Test basic value setting."""
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Test Number",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test_number",
            entity_attr="targetDuration",  # Use a supported entity
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock()  # Make it async
        entity._rate_limit_command = AsyncMock()
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        # Mock async_write_ha_state to avoid hass requirement
        entity.async_write_ha_state = MagicMock()

        # Check that the method returns True
        assert entity._is_supported_by_program()

        with patch.object(entity, "_is_supported_by_program", return_value=True), patch(
            "custom_components.electrolux.number.format_command_for_appliance"
        ) as mock_format, patch.object(entity, "coordinator") as mock_coord:
            mock_coord.async_request_refresh = AsyncMock()
            mock_format.return_value = 42
            await entity.async_set_native_value(42.0)

            mock_format.assert_called_once_with(
                entity.capability, "targetDuration", 42.0
            )
            entity.api.execute_appliance_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_native_value_food_probe_not_inserted(
        self, mock_coordinator
    ):
        """Test setting food probe temperature when not inserted raises error."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Food Probe Temp",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="food_probe_temp",
            entity_attr="targetFoodProbeTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class="temperature",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer-probe",
        )
        entity.reported_state = {"foodProbeInsertionState": "NOT_INSERTED"}

        with pytest.raises(HomeAssistantError, match="Food probe must be inserted"):
            await entity.async_set_native_value(50.0)

    @pytest.mark.asyncio
    async def test_async_set_native_value_not_supported_by_program(self, number_entity):
        """Test setting value when not supported by program raises error."""
        number_entity._is_supported_by_program = MagicMock(return_value=False)

        with pytest.raises(
            HomeAssistantError, match="not supported by the current program"
        ):
            await number_entity.async_set_native_value(50.0)

    @pytest.mark.asyncio
    async def test_async_set_native_value_time_conversion(self, mock_coordinator):
        """Test that time values are converted from minutes to seconds when setting."""
        capability = {"access": "readwrite", "type": "number", "max": 7200, "step": 60}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Duration",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_duration",
            entity_attr="targetDuration",
            entity_source=None,
            capability=capability,
            unit=UnitOfTime.SECONDS,  # Updated to SECONDS
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timelapse",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock()  # Make it async
        entity._rate_limit_command = AsyncMock()
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        # Mock async_write_ha_state to avoid hass requirement
        entity.async_write_ha_state = MagicMock()

        with patch(
            "custom_components.electrolux.number.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = 1800  # 30 minutes in seconds
            await entity.async_set_native_value(30.0)  # 30 minutes

            # Verify the value was converted to seconds before formatting
            mock_format.assert_called_once()
            args = mock_format.call_args[0]
            assert args[2] == 1800  # Should be converted to seconds

    def test_available_property_step_zero(self, number_entity):
        """Test that entity is unavailable when step is 0."""
        number_entity._get_program_constraint = MagicMock(return_value=0)
        assert not number_entity.available

    def test_available_property_supported_by_program(self, number_entity):
        """Test availability based on program support."""
        number_entity._is_supported_by_program = MagicMock(return_value=True)
        assert number_entity.available

    def test_available_property_not_supported_by_program(self, number_entity):
        """Test that entity is unavailable when not supported by program."""
        number_entity._is_supported_by_program = MagicMock(return_value=False)
        assert not number_entity.available
