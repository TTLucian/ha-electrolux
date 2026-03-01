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
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
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
            entity_category=None,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.appliance_status = {
            "properties": {"reported": {"testAttr": 75, "remoteControl": "ENABLED"}}
        }
        entity.reported_state = {"testAttr": 75, "remoteControl": "ENABLED"}
        return entity

    def test_entity_domain(self, number_entity):
        """Test entity domain property."""
        assert number_entity.entity_domain == "number"

    def test_mode_box_for_many_steps(self, mock_coordinator):
        """Test that entities with >100 steps use BOX mode (e.g., time inputs with 1-min steps)."""
        # Create entity with many steps: 1440 steps (0-1439, step=1)
        capability = {
            "access": "readwrite",
            "type": "number",
            "min": 0,
            "max": 1439,
            "step": 1,
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
            unit=UnitOfTime.MINUTES,
            device_class=NumberDeviceClass.DURATION,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:timelapse",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity._get_program_constraint = lambda key: None
        entity._is_locked_by_program = lambda: False
        assert entity.mode == NumberMode.BOX

    def test_mode_slider_for_few_steps(self, mock_coordinator):
        """Test that entities with ≤100 steps use SLIDER mode (e.g., temperature, small time ranges)."""
        # Create entity with few steps: 41 steps (30-230, step=5)
        capability = {
            "access": "readwrite",
            "type": "temperature",
            "min": 30,
            "max": 230,
            "step": 5,
        }
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=None,
            icon="mdi:thermometer",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity._get_program_constraint = lambda key: None
        entity._is_locked_by_program = lambda: False
        assert entity.mode == NumberMode.SLIDER

    def test_mode_box_with_default_fallback_constraints(self, mock_coordinator):
        """Test mode with fallback constraints (0-100, step=1 → 101 steps → BOX)."""
        # Create entity without constraints - will use fallback values
        # DEFAULT_NUMBER_MIN=0, DEFAULT_NUMBER_MAX=100, DEFAULT_NUMBER_STEP=1
        # This gives 101 steps, which is > threshold of 100, so BOX mode
        capability = {"access": "readwrite", "type": "number"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Test Number",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test_number",
            entity_attr="testAttr",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        entity._get_program_constraint = lambda key: None
        entity._is_locked_by_program = lambda: False
        # Fallback constraints: 0-100, step=1 → 101 steps → BOX
        assert entity.mode == NumberMode.BOX

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
        entity.hass = mock_coordinator.hass  # Set hass for the entity
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
        entity.hass = mock_coordinator.hass  # Set hass for the entity
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
        entity.hass = mock_coordinator.hass  # Set hass for the entity
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
        entity.hass = mock_coordinator.hass  # Set hass for the entity
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
            entity_category=None,  # Food probe is not a CONFIG entity
            icon="mdi:thermometer-probe",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.appliance_status = {
            "properties": {"reported": {"foodProbeInsertionState": "NOT_INSERTED"}}
        }
        entity.reported_state = {"foodProbeInsertionState": "NOT_INSERTED"}
        assert entity.native_value == 0.0

    def test_native_max_value_program_specific(self, number_entity):
        """Test max value from program-specific constraints."""
        number_entity._get_program_constraint = MagicMock(return_value=80)
        number_entity._is_locked_by_program = MagicMock(return_value=False)
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

    def test_native_max_value_temperature_fallback_celsius(self, mock_coordinator):
        """Test targetTemperatureC gets proper fallback max (230°C)."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature C",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature_c",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=None,
            icon="mdi:thermometer",
        )
        entity._get_program_constraint = MagicMock(return_value=None)
        entity._is_locked_by_program = MagicMock(return_value=False)
        assert entity.native_max_value == 230.0

    def test_native_max_value_temperature_fallback_fahrenheit(self, mock_coordinator):
        """Test targetTemperatureF gets proper fallback max (446°F)."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature F",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature_f",
            entity_attr="targetTemperatureF",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.FAHRENHEIT,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=None,
            icon="mdi:thermometer",
        )
        entity._get_program_constraint = MagicMock(return_value=None)
        entity._is_locked_by_program = MagicMock(return_value=False)
        assert entity.native_max_value == 446.0

    def test_native_max_value_food_probe_fallback_celsius(self, mock_coordinator):
        """Test targetFoodProbeTemperatureC gets proper fallback max (99°C)."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Food Probe Temperature C",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_food_probe_temperature_c",
            entity_attr="targetFoodProbeTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=None,
            icon="mdi:thermometer-probe",
        )
        entity._get_program_constraint = MagicMock(return_value=None)
        entity._is_locked_by_program = MagicMock(return_value=False)
        assert entity.native_max_value == 99.0

    def test_native_max_value_food_probe_fallback_fahrenheit(self, mock_coordinator):
        """Test targetFoodProbeTemperatureF gets proper fallback max (210°F)."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Food Probe Temperature F",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_food_probe_temperature_f",
            entity_attr="targetFoodProbeTemperatureF",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.FAHRENHEIT,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_category=None,
            icon="mdi:thermometer-probe",
        )
        entity._get_program_constraint = MagicMock(return_value=None)
        entity._is_locked_by_program = MagicMock(return_value=False)
        assert entity.native_max_value == 210.0

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
        number_entity._get_program_constraint = MagicMock(
            side_effect=lambda key: 5 if key == "step" else None
        )
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
        entity.hass = mock_coordinator.hass  # Set hass for the entity
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
            mock_coord._last_update_times = {}
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
            entity_category=None,
            icon="mdi:thermometer-probe",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.reported_state = {"foodProbeInsertionState": "NOT_INSERTED"}

        with pytest.raises(HomeAssistantError, match="Food probe must be inserted"):
            await entity.async_set_native_value(50.0)

    @pytest.mark.asyncio
    async def test_async_set_native_value_not_supported_by_program(self, number_entity):
        """Test setting value when not supported by program raises error."""
        number_entity._is_supported_by_program = MagicMock(return_value=False)
        number_entity.entity_attr = "someControl"  # Not targetFoodProbeTemperatureC

        with pytest.raises(HomeAssistantError, match="not supported by program"):
            await number_entity.async_set_native_value(50.0)

    @pytest.mark.asyncio
    async def test_async_set_native_value_target_temperature_not_supported_by_program(
        self, mock_coordinator
    ):
        """Test setting target temperature when not supported by program shows notification and doesn't proceed."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class="temperature",
            entity_category=None,
            icon="mdi:thermometer",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.reported_state = {"program": "unsupported_program"}
        entity._is_supported_by_program = MagicMock(return_value=False)

        with pytest.raises(HomeAssistantError, match="not supported by program"):
            await entity.async_set_native_value(180.0)

    @pytest.mark.asyncio
    async def test_async_set_native_value_food_probe_temperature_not_supported_by_program(
        self, mock_coordinator, caplog
    ):
        """Test setting food probe temperature when not supported by program raises error."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Food Probe Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="food_probe_temperature",
            entity_attr="targetFoodProbeTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class="temperature",
            entity_category=None,
            icon="mdi:thermometer-probe",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "program": "unsupported_program",
                    "foodProbeInsertionState": "INSERTED",
                    "remoteControl": "ENABLED",
                }
            }
        }
        entity._is_supported_by_program = MagicMock(return_value=False)
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(
            return_value={"result": "success"}
        )
        entity._rate_limit_command = AsyncMock()

        # Mock _get_converted_constraint to return 30.0 for min
        with patch.object(entity, "_get_converted_constraint", return_value=30.0):
            # Mock async_write_ha_state to avoid entity setup issues
            with patch.object(entity, "async_write_ha_state"):
                with pytest.raises(
                    HomeAssistantError,
                    match="not supported by program",
                ):
                    await entity.async_set_native_value(70.0)
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
        """Test that entity remains available even when step is 0 (Entity Availability Rules)."""
        number_entity._get_program_constraint = MagicMock(return_value=0)
        assert number_entity.available

    def test_available_property_supported_by_program(self, number_entity):
        """Test availability based on program support."""
        number_entity._is_supported_by_program = MagicMock(return_value=True)
        assert number_entity.available

    def test_available_property_always_available_regardless_of_program_support(
        self, number_entity
    ):
        """Test that entities are always available regardless of program support (Entity Availability Rules)."""
        number_entity._is_supported_by_program = MagicMock(return_value=False)
        assert number_entity.available  # Should remain available

    def test_available_property_target_temperature_supported_by_program(
        self, mock_coordinator
    ):
        """Test that target temperature is available when supported by program."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class="temperature",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }
        entity._is_supported_by_program = MagicMock(return_value=True)
        assert entity.available

    def test_available_property_target_temperature_not_supported_by_program(
        self, mock_coordinator
    ):
        """Test that target temperature is always available (shows 0 when not supported by program)."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class="temperature",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }
        entity._is_supported_by_program = MagicMock(return_value=False)
        # targetTemperatureC is now always available regardless of program support
        assert entity.available

    def test_available_property_food_probe_temperature_supported_by_program(
        self, mock_coordinator
    ):
        """Test that food probe temperature is available when supported by program."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Food Probe Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="food_probe_temperature",
            entity_attr="targetFoodProbeTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class="temperature",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer-probe",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }
        entity._is_supported_by_program = MagicMock(return_value=True)
        assert entity.available

    def test_available_property_food_probe_temperature_not_supported_by_program(
        self, mock_coordinator
    ):
        """Test that food probe temperature is always available (shows 0 when not supported by program)."""
        capability = {"access": "readwrite", "type": "temperature"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Food Probe Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="food_probe_temperature",
            entity_attr="targetFoodProbeTemperatureC",
            entity_source=None,
            capability=capability,
            unit=UnitOfTemperature.CELSIUS,
            device_class="temperature",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer-probe",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }
        # targetFoodProbeTemperatureC is now always available regardless of program support
        assert entity.available


class TestGetCapabilityConstraint:
    """Tests for _get_capability_constraint helper function."""

    def _fn(self):
        from custom_components.electrolux.number import _get_capability_constraint

        return _get_capability_constraint

    def test_standard_key_present(self):
        """Standard key (min/max/step) is returned directly."""
        fn = self._fn()
        assert fn({"min": 10, "max": 100, "step": 5}, "min") == 10.0
        assert fn({"max": 200}, "max") == 200.0

    def test_standard_key_missing_falls_through(self):
        """Missing standard key tries range/ranges formats."""
        fn = self._fn()
        # No key anywhere → returns None
        assert fn({}, "min") is None

    def test_invalid_key_returns_none(self):
        """Unknown key not in capability dict and not in min/max/step index → None."""
        fn = self._fn()
        # Key not in capability at all, and not a valid constraint key
        assert fn({}, "default") is None
        assert fn({}, "description") is None

    def test_dam_single_range_format_min(self):
        """DAM single-range: range: [min, max, step] → min."""
        fn = self._fn()
        cap = {"range": [10.0, 200.0, 5.0]}
        assert fn(cap, "min") == 10.0

    def test_dam_single_range_format_max(self):
        """DAM single-range: range: [min, max, step] → max."""
        fn = self._fn()
        cap = {"range": [10.0, 200.0, 5.0]}
        assert fn(cap, "max") == 200.0

    def test_dam_single_range_format_step(self):
        """DAM single-range: range: [min, max, step] → step."""
        fn = self._fn()
        cap = {"range": [10.0, 200.0, 5.0]}
        assert fn(cap, "step") == 5.0

    def test_dam_multi_range_format_min(self):
        """DAM multi-range: ranges → smallest min."""
        fn = self._fn()
        cap = {"ranges": [[10.0, 100.0, 5.0], [20.0, 200.0, 10.0]]}
        assert fn(cap, "min") == 10.0

    def test_dam_multi_range_format_max(self):
        """DAM multi-range: ranges → largest max."""
        fn = self._fn()
        cap = {"ranges": [[10.0, 100.0, 5.0], [20.0, 200.0, 10.0]]}
        assert fn(cap, "max") == 200.0

    def test_dam_multi_range_format_step(self):
        """DAM multi-range: ranges → smallest non-zero step."""
        fn = self._fn()
        cap = {"ranges": [[10.0, 100.0, 5.0], [20.0, 200.0, 10.0]]}
        assert fn(cap, "step") == 5.0

    def test_dam_multi_range_zero_step_skipped(self):
        """DAM multi-range: step=0 ranges are skipped."""
        fn = self._fn()
        cap = {"ranges": [[0.0, 60.0, 0.0], [60.0, 120.0, 5.0]]}
        assert fn(cap, "step") == 5.0

    def test_dam_multi_range_no_valid_step_returns_none(self):
        """DAM multi-range: all step=0 → returns None for step."""
        fn = self._fn()
        cap = {"ranges": [[0.0, 60.0, 0.0]]}
        assert fn(cap, "step") is None


class TestNumberAsyncSetNativeValueAdvanced:
    """Additional tests for async_set_native_value covering DAM and locked paths."""

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

    def _make_entity(
        self,
        coordinator,
        entity_attr="testAttr",
        entity_source=None,
        pnc_id="TEST_PNC",
        entity_category=None,
        capability=None,
    ):
        if capability is None:
            capability = {
                "access": "readwrite",
                "type": "number",
                "min": 0,
                "max": 100,
                "step": 1,
            }
        entity = ElectroluxNumber(
            coordinator=coordinator,
            name="Test Number",
            config_entry=coordinator.config_entry,
            pnc_id=pnc_id,
            entity_type=NUMBER,
            entity_name="test_number",
            entity_attr=entity_attr,
            entity_source=entity_source,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=entity_category,
            icon="mdi:test",
        )
        entity.hass = coordinator.hass
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value={"result": "ok"})
        entity._rate_limit_command = AsyncMock()
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }
        entity.async_write_ha_state = MagicMock()
        return entity

    @pytest.mark.asyncio
    async def test_set_native_value_non_dam_with_entity_source(self, mock_coordinator):
        """Non-DAM entity with entity_source wraps command under source key."""
        entity = self._make_entity(
            mock_coordinator,
            entity_source="oven",
            entity_attr="targetTemperatureC",
            capability={
                "access": "readwrite",
                "type": "number",
                "min": 0,
                "max": 300,
                "step": 1,
            },
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)

        with patch(
            "custom_components.electrolux.number.format_command_for_appliance",
            return_value=180.0,
        ):
            await entity.async_set_native_value(180.0)

        call_args = entity.api.execute_appliance_command.call_args[0]  # type: ignore[union-attr]
        assert call_args[1] == {"oven": {"targetTemperatureC": 180.0}}

    @pytest.mark.asyncio
    async def test_set_native_value_dam_target_duration(self, mock_coordinator):
        """DAM appliance with targetDuration wraps command under appliance type."""
        from unittest.mock import PropertyMock

        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetDuration",
            pnc_id="1:TEST_PNC",  # DAM appliance
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)

        mock_appliance = MagicMock()
        mock_appliance.appliance_type = "oven"

        with patch.object(
            type(entity),
            "get_appliance",
            new_callable=PropertyMock,
            return_value=mock_appliance,
        ), patch(
            "custom_components.electrolux.number.format_command_for_appliance",
            return_value=3600,
        ):
            await entity.async_set_native_value(60.0)  # 60 minutes

        call_args = entity.api.execute_appliance_command.call_args[0]  # type: ignore[union-attr]
        # DAM commands are wrapped in {"commands": [...]}
        assert "commands" in call_args[1]

    @pytest.mark.asyncio
    async def test_set_native_value_dam_with_other_entity_source(
        self, mock_coordinator
    ):
        """DAM appliance with non-standard entity_source builds nested command."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="cavityLight",
            entity_source="oven",
            pnc_id="1:TEST_PNC",  # DAM appliance
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)

        with patch(
            "custom_components.electrolux.number.format_command_for_appliance",
            return_value=1,
        ):
            await entity.async_set_native_value(1.0)

        call_args = entity.api.execute_appliance_command.call_args[0]  # type: ignore[union-attr]
        assert "commands" in call_args[1]

    @pytest.mark.asyncio
    async def test_set_native_value_dam_no_entity_source(self, mock_coordinator):
        """DAM appliance with no entity_source uses plain attr command (wrapped in commands list)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="testAttr",
            entity_source=None,
            pnc_id="1:TEST_PNC",  # DAM appliance
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)

        with patch(
            "custom_components.electrolux.number.format_command_for_appliance",
            return_value=50,
        ):
            await entity.async_set_native_value(50.0)

        call_args = entity.api.execute_appliance_command.call_args[0]  # type: ignore[union-attr]
        assert "commands" in call_args[1]

    @pytest.mark.asyncio
    async def test_set_native_value_dam_user_selections_missing_program_uid(
        self, mock_coordinator
    ):
        """DAM appliance with userSelections source but no programUID raises error."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="antiCreaseValue",
            entity_source="userSelections",
            pnc_id="1:TEST_PNC",
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "ENABLED",
                    # userSelections has no programUID
                    "userSelections": {},
                }
            }
        }

        with patch(
            "custom_components.electrolux.number.format_command_for_appliance",
            return_value=30,
        ):
            with pytest.raises(HomeAssistantError, match="state is incomplete"):
                await entity.async_set_native_value(30.0)

    @pytest.mark.asyncio
    async def test_set_native_value_food_probe_locked_by_program(
        self, mock_coordinator
    ):
        """Food probe entity locked but INSERTED and supported → food_probe_locked error."""
        capability = {
            "access": "readwrite",
            "type": "temperature",
            "min": 40,
            "max": 40,
        }
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetFoodProbeTemperatureC",
            capability=capability,
        )
        entity.reported_state = {
            "foodProbeInsertionState": "INSERTED",
            "program": "BEEF",
        }
        entity._is_locked_by_program = MagicMock(return_value=True)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity._get_current_program_name = MagicMock(return_value="BEEF")
        entity._get_locked_value = MagicMock(return_value=40.0)

        with pytest.raises(HomeAssistantError, match="locked"):
            await entity.async_set_native_value(50.0)

    @pytest.mark.asyncio
    async def test_set_native_value_control_locked_by_program(self, mock_coordinator):
        """Non-food-probe entity locked + supported → control_locked error."""
        entity = self._make_entity(mock_coordinator, entity_attr="targetTemperatureC")
        entity.reported_state = {"program": "DEFROST"}
        entity._is_locked_by_program = MagicMock(return_value=True)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity._get_current_program_name = MagicMock(return_value="DEFROST")
        entity._get_locked_value = MagicMock(return_value=40.0)

        with pytest.raises(HomeAssistantError, match="locked"):
            await entity.async_set_native_value(100.0)

    @pytest.mark.asyncio
    async def test_set_native_value_authentication_error_handled(
        self, mock_coordinator
    ):
        """AuthenticationError from API triggers coordinator.handle_authentication_error."""
        from custom_components.electrolux.util import AuthenticationError

        entity = self._make_entity(mock_coordinator)
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)

        mock_coordinator.handle_authentication_error = AsyncMock()

        with patch(
            "custom_components.electrolux.number.execute_command_with_error_handling",
            side_effect=AuthenticationError("token expired"),
        ), patch(
            "custom_components.electrolux.number.format_command_for_appliance",
            return_value=50,
        ), patch.object(
            entity, "coordinator", mock_coordinator
        ):
            await entity.async_set_native_value(50.0)  # Should NOT raise

        mock_coordinator.handle_authentication_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_native_value_generic_exception_re_raised(self, mock_coordinator):
        """Generic exception from API is re-raised."""
        entity = self._make_entity(mock_coordinator)
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)

        with patch(
            "custom_components.electrolux.number.execute_command_with_error_handling",
            side_effect=HomeAssistantError("command validation failed"),
        ), patch(
            "custom_components.electrolux.number.format_command_for_appliance",
            return_value=50,
        ):
            with pytest.raises(HomeAssistantError):
                await entity.async_set_native_value(50.0)


class TestNumberMissingCoverage:
    """Tests targeting the remaining missed lines in number.py."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        return coordinator

    def _make_entity(
        self,
        coordinator,
        entity_attr="testAttr",
        entity_source=None,
        pnc_id="TEST_PNC",
        entity_category=None,
        capability=None,
        unit=None,
    ):
        from custom_components.electrolux.number import ElectroluxNumber
        from custom_components.electrolux.const import NUMBER

        if capability is None:
            capability = {
                "access": "readwrite",
                "type": "number",
                "min": 0,
                "max": 100,
                "step": 1,
            }
        entity = ElectroluxNumber(
            coordinator=coordinator,
            name="Test Number",
            config_entry=coordinator.config_entry,
            pnc_id=pnc_id,
            entity_type=NUMBER,
            entity_name="test_number",
            entity_attr=entity_attr,
            entity_source=entity_source,
            capability=capability,
            unit=unit,
            device_class=None,
            entity_category=entity_category,
            icon="mdi:test",
        )
        entity.hass = coordinator.hass
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value={"result": "ok"})
        entity._rate_limit_command = AsyncMock()
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }
        entity.async_write_ha_state = MagicMock()
        return entity

    # ------------------------------------------------------------------ #
    # Line 152: device_class — catalog entry with NumberDeviceClass instance
    # ------------------------------------------------------------------ #

    def test_device_class_catalog_entry_number_device_class(self, mock_coordinator):
        """When catalog_entry.device_class is a NumberDeviceClass instance, it's returned (line 152)."""
        from custom_components.electrolux.number import (
            ElectroluxNumber,
            NumberDeviceClass,
        )
        from custom_components.electrolux.const import NUMBER

        entity = self._make_entity(mock_coordinator)
        mock_catalog = MagicMock()
        mock_catalog.device_class = NumberDeviceClass.TEMPERATURE
        entity._catalog_entry = mock_catalog
        assert entity.device_class == NumberDeviceClass.TEMPERATURE

    # ------------------------------------------------------------------ #
    # Lines 180-186: device_class — base _device_class is NumberDeviceClass / "temperature"
    # ------------------------------------------------------------------ #

    def test_device_class_base_device_class_is_number_device_class(
        self, mock_coordinator
    ):
        """When _device_class is a NumberDeviceClass (no catalog), it's returned (lines 180-182)."""
        from homeassistant.components.number import NumberDeviceClass as NDC

        entity = self._make_entity(mock_coordinator)
        entity._catalog_entry = None
        entity._device_class = NDC.HUMIDITY  # a NumberDeviceClass instance
        assert entity.device_class == NDC.HUMIDITY

    def test_device_class_base_device_class_string_temperature(self, mock_coordinator):
        """When _device_class is the string 'temperature' (no catalog), returns TEMPERATURE (line 184)."""
        from homeassistant.components.number import NumberDeviceClass as NDC

        entity = self._make_entity(mock_coordinator)
        entity._catalog_entry = None
        entity._device_class = "temperature"
        assert entity.device_class == NDC.TEMPERATURE

    # ------------------------------------------------------------------ #
    # Line 192: device_class — capability type "temperature" (no catalog, no _device_class match)
    # ------------------------------------------------------------------ #

    def test_device_class_capability_type_temperature(self, mock_coordinator):
        """When capability.type == 'temperature' (fallback), returns TEMPERATURE (line 192)."""
        from homeassistant.components.number import NumberDeviceClass as NDC

        entity = self._make_entity(
            mock_coordinator,
            capability={"type": "temperature", "min": 0, "max": 300},
        )
        entity._catalog_entry = None
        entity._device_class = None  # won't match NDC or "temperature"
        assert entity.device_class == NDC.TEMPERATURE

    # ------------------------------------------------------------------ #
    # Line 195: device_class returns None when nothing matches
    # ------------------------------------------------------------------ #

    def test_device_class_returns_none_when_no_match(self, mock_coordinator):
        """When no conditions match, device_class returns None (line 195 — technically already covered by existing tests but for completeness)."""
        entity = self._make_entity(
            mock_coordinator,
            capability={"type": "boolean"},
        )
        entity._catalog_entry = None
        entity._device_class = None
        assert entity.device_class is None

    # ------------------------------------------------------------------ #
    # Lines 203, 210, 217: native_value — program default, then oven default, then targetFoodProbeTemperatureC
    # ------------------------------------------------------------------ #

    def test_native_value_uses_program_default_for_temp_control(self, mock_coordinator):
        """When value is None for targetTemperatureC, uses _get_program_constraint(default) (line 203/207)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureC",
            capability={"type": "temperature", "min": 30, "max": 230},
        )
        entity._get_locked_value = MagicMock(return_value=0.0)
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._get_program_constraint = MagicMock(return_value=180.0)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value=None):
            result = entity.native_value

        assert result == 180.0

    def test_native_value_uses_capability_default_for_temp_when_no_program_default(
        self, mock_coordinator
    ):
        """When targetTemperatureC has None program default, falls back to capability.get('default') (line 210)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureC",
            capability={"type": "temperature", "min": 30, "max": 230, "default": 100.0},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._get_program_constraint = MagicMock(return_value=None)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value=None):
            result = entity.native_value

        assert result == 100.0

    def test_native_value_food_probe_temp_uses_program_default(self, mock_coordinator):
        """For targetFoodProbeTemperatureC, program default is used when value is None (line 217)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetFoodProbeTemperatureC",
            capability={"type": "temperature", "min": 40, "max": 99},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._get_program_constraint = MagicMock(return_value=60.0)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value=None):
            result = entity.native_value

        assert result == 60.0

    # ------------------------------------------------------------------ #
    # Lines 227-246: native_value — capability default, TIME_INVALID_OR_NOT_SET, targetDuration fallback
    # ------------------------------------------------------------------ #

    def test_native_value_uses_capability_default_when_value_is_none(
        self, mock_coordinator
    ):
        """When value is None (non-temp control), falls back to capability.get('default') (lines 227-228)."""
        from custom_components.electrolux.const import TIME_INVALID_OR_NOT_SET

        entity = self._make_entity(
            mock_coordinator,
            entity_attr="someAttr",
            capability={"type": "number", "min": 0, "max": 100, "default": 50},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value=None):
            result = entity.native_value

        assert result == 50

    def test_native_value_time_invalid_or_not_set_uses_min(self, mock_coordinator):
        """When capability default is TIME_INVALID_OR_NOT_SET, falls back to min (lines 229-230)."""
        from custom_components.electrolux.const import TIME_INVALID_OR_NOT_SET

        entity = self._make_entity(
            mock_coordinator,
            entity_attr="someAttr",
            capability={
                "type": "number",
                "min": 10,
                "max": 100,
                "default": TIME_INVALID_OR_NOT_SET,
            },
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value=None):
            result = entity.native_value

        assert result == 10

    def test_native_value_target_duration_defaults_to_zero(self, mock_coordinator):
        """When targetDuration has no capability default, value falls back to 0 (lines 231-232)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetDuration",
            capability={"type": "number", "min": 0, "max": 86400},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value=None):
            result = entity.native_value

        assert result == 0

    def test_native_value_non_numeric_returns_none(self, mock_coordinator):
        """Non-numeric value triggers warning and returns None (lines 248-252)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="testAttr",
            capability={"type": "number", "min": 0, "max": 100},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value="bad_value"):
            result = entity.native_value

        assert result is None

    # ------------------------------------------------------------------ #
    # Lines 252-258: native_value — temperature unit rounds value
    # ------------------------------------------------------------------ #

    def test_native_value_temperature_unit_rounds_to_2_decimals(self, mock_coordinator):
        """When unit is a UnitOfTemperature, value is rounded to 2 places (line 258)."""
        from homeassistant.const import UnitOfTemperature

        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureC",
            capability={"type": "temperature", "min": 30, "max": 230},
            unit=UnitOfTemperature.CELSIUS,
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value=180.123456):
            result = entity.native_value

        assert result == round(180.123456, 2)

    # ------------------------------------------------------------------ #
    # Line 278, 280: native_value — clamp to min/max
    # ------------------------------------------------------------------ #

    def test_native_value_clamped_to_min(self, mock_coordinator):
        """Value below min is clamped to min (line 278)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="testAttr",
            capability={"type": "number", "min": 10, "max": 100, "step": 1},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value=3):
            result = entity.native_value

        assert result == 10.0

    def test_native_value_clamped_to_max(self, mock_coordinator):
        """Value above max is clamped to max (line 280)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="testAttr",
            capability={"type": "number", "min": 10, "max": 100, "step": 1},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value=200):
            result = entity.native_value

        assert result == 100.0

    # ------------------------------------------------------------------ #
    # Line 321: _is_locked_by_program — food probe lock (line 321)
    # ------------------------------------------------------------------ #

    def test_is_locked_by_program_food_probe_not_inserted(self, mock_coordinator):
        """Food probe entity locked when not inserted (line 321)."""
        from custom_components.electrolux.const import FOOD_PROBE_STATE_NOT_INSERTED

        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetFoodProbeTemperatureC",
            capability={"type": "temperature", "min": 40, "max": 99},
        )
        entity.reported_state = {
            "foodProbeInsertionState": FOOD_PROBE_STATE_NOT_INSERTED
        }
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity._get_program_constraint = MagicMock(return_value=None)
        assert entity._is_locked_by_program() is True

    # ------------------------------------------------------------------ #
    # Line 345: _is_locked_by_program — zero step
    # ------------------------------------------------------------------ #

    def test_is_locked_by_program_zero_step(self, mock_coordinator):
        """Entity locked when program step == 0 (line 345)."""
        entity = self._make_entity(mock_coordinator, entity_attr="targetTemperatureC")
        entity._get_program_constraint = MagicMock(
            side_effect=lambda k: {"min": 40.0, "max": 60.0, "step": 0.0}.get(k)
        )
        entity._is_supported_by_program = MagicMock(return_value=True)
        assert entity._is_locked_by_program() is True

    # ------------------------------------------------------------------ #
    # Line 370: _get_locked_value — capability default fallback
    # ------------------------------------------------------------------ #

    def test_get_locked_value_uses_capability_default(self, mock_coordinator):
        """_get_locked_value uses capability.default when no program constraints (line 370)."""
        entity = self._make_entity(
            mock_coordinator,
            capability={"type": "number", "min": 5, "max": 100, "default": 42.0},
        )
        entity._get_program_constraint = MagicMock(return_value=None)
        assert entity._get_locked_value() == 42.0

    # ------------------------------------------------------------------ #
    # Lines 388-390: _get_locked_value — global capability min fallback
    # ------------------------------------------------------------------ #

    def test_get_locked_value_uses_capability_min(self, mock_coordinator):
        """_get_locked_value uses capability.min when no default or program constraint (lines 388-390)."""
        entity = self._make_entity(
            mock_coordinator,
            capability={"type": "number", "min": 20, "max": 100},
        )
        entity._get_program_constraint = MagicMock(return_value=None)
        assert entity._get_locked_value() == 20.0

    # ------------------------------------------------------------------ #
    # Line 419: _get_converted_constraint — catalog entry non-numeric warns + returns
    # ------------------------------------------------------------------ #

    def test_get_converted_constraint_catalog_non_numeric_warns_and_falls_through(
        self, mock_coordinator
    ):
        """When catalog val is non-numeric, warns and falls through to capability (line 419)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="testAttr",
            capability={"type": "number", "max": 50},
        )
        mock_catalog = MagicMock()
        mock_catalog.capability_info = {"max": "not-a-number"}
        entity._catalog_entry = mock_catalog
        entity._is_locked_by_program = MagicMock(return_value=False)

        # Should fall through to capability max = 50
        result = entity._get_converted_constraint("max")
        assert result == 50.0

    # ------------------------------------------------------------------ #
    # Lines 429-444: _get_converted_constraint — catalog converts seconds to minutes for time entities
    # ------------------------------------------------------------------ #

    def test_get_converted_constraint_catalog_time_entity_converts_to_minutes(
        self, mock_coordinator
    ):
        """Time entity: catalog value (seconds) is converted to minutes for UI (lines 429-444)."""
        from homeassistant.const import UnitOfTime

        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetDuration",
            unit=UnitOfTime.SECONDS,
        )
        mock_catalog = MagicMock()
        mock_catalog.capability_info = {"max": 3600}  # 3600 seconds = 60 minutes
        entity._catalog_entry = mock_catalog
        entity._is_locked_by_program = MagicMock(return_value=False)

        result = entity._get_converted_constraint("max")
        assert result == 60.0

    # ------------------------------------------------------------------ #
    # Lines 502, 504-506: _get_converted_constraint — targetTemperatureF, targetFoodProbeTemperatureF max fallbacks
    # ------------------------------------------------------------------ #

    def test_get_converted_constraint_target_temp_f_fallback(self, mock_coordinator):
        """targetTemperatureF falls back to TEMP_OVEN_MAX_F when no val (line 485)."""
        from custom_components.electrolux.const import TEMP_OVEN_MAX_F

        # Capability has no max so _get_capability_constraint returns None → triggers fallback
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureF",
            capability={"type": "temperature"},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._catalog_entry = None
        entity._get_program_constraint = MagicMock(return_value=None)

        result = entity._get_converted_constraint("max")
        assert result == float(TEMP_OVEN_MAX_F)

    def test_get_converted_constraint_food_probe_temp_c_fallback(
        self, mock_coordinator
    ):
        """targetFoodProbeTemperatureC falls back to TEMP_PROBE_MAX_C (line 487)."""
        from custom_components.electrolux.const import TEMP_PROBE_MAX_C

        # Capability has no max so _get_capability_constraint returns None → triggers fallback
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetFoodProbeTemperatureC",
            capability={"type": "temperature"},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._catalog_entry = None
        entity._get_program_constraint = MagicMock(return_value=None)

        result = entity._get_converted_constraint("max")
        assert result == float(TEMP_PROBE_MAX_C)

    def test_get_converted_constraint_food_probe_temp_f_fallback(
        self, mock_coordinator
    ):
        """targetFoodProbeTemperatureF falls back to TEMP_PROBE_MAX_F (line 489)."""
        from custom_components.electrolux.const import TEMP_PROBE_MAX_F

        # Capability has no max so _get_capability_constraint returns None → triggers fallback
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetFoodProbeTemperatureF",
            capability={"type": "temperature"},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._catalog_entry = None
        entity._get_program_constraint = MagicMock(return_value=None)

        result = entity._get_converted_constraint("max")
        assert result == float(TEMP_PROBE_MAX_F)

    # ------------------------------------------------------------------ #
    # Line 559: _get_converted_constraint step — temp control uses TEMP_OVEN_STEP
    # ------------------------------------------------------------------ #

    def test_get_converted_constraint_step_for_temp_control_uses_oven_step(
        self, mock_coordinator
    ):
        """Step for targetTemperatureC/F uses TEMP_OVEN_STEP (line 559)."""
        from custom_components.electrolux.const import TEMP_OVEN_STEP

        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureC",
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._catalog_entry = None
        entity._get_program_constraint = MagicMock(
            return_value=0
        )  # step=0 triggers fallback

        result = entity._get_converted_constraint("step")
        assert result == TEMP_OVEN_STEP

    # ------------------------------------------------------------------ #
    # Line 566: _get_converted_constraint step — unknown attr returns DEFAULT_NUMBER_STEP
    # ------------------------------------------------------------------ #

    def test_get_converted_constraint_step_default_fallback(self, mock_coordinator):
        """Step for unknown attr with no val returns DEFAULT_NUMBER_STEP (line 566)."""
        from custom_components.electrolux.const import DEFAULT_NUMBER_STEP

        entity = self._make_entity(
            mock_coordinator,
            entity_attr="unknownAttr",
            capability={"type": "number"},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._catalog_entry = None
        entity._get_program_constraint = MagicMock(
            return_value=0
        )  # step=0 triggers fallback

        result = entity._get_converted_constraint("step")
        assert result == DEFAULT_NUMBER_STEP

    # ------------------------------------------------------------------ #
    # Lines 593-600: async_set_native_value — value below min and above max errors
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_set_value_below_min_raises_error(self, mock_coordinator):
        """Setting value below native_min_value raises HomeAssistantError (lines 593-596)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureC",
            capability={"type": "temperature", "min": 30, "max": 230, "step": 1},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with pytest.raises(HomeAssistantError, match="below minimum"):
            await entity.async_set_native_value(10.0)  # below min=30

    @pytest.mark.asyncio
    async def test_set_value_above_max_raises_error(self, mock_coordinator):
        """Setting value above native_max_value raises HomeAssistantError (lines 597-600)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureC",
            capability={"type": "temperature", "min": 30, "max": 230, "step": 1},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with pytest.raises(HomeAssistantError, match="above maximum"):
            await entity.async_set_native_value(300.0)  # above max=230

    # ------------------------------------------------------------------ #
    # Lines 661-683: async_set_native_value — latamUserSelections path
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_set_value_latam_user_selections_path(self, mock_coordinator):
        """DAM entity with latamUserSelections entity_source sends full block (lines 661-683)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="spinSpeed",
            entity_source="latamUserSelections",
            pnc_id="1:TEST_PNC",
            capability={"type": "number", "min": 0, "max": 1600, "step": 200},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "ENABLED",
                    "latamUserSelections": {"spinSpeed": 800, "programUID": "COTTON"},
                }
            }
        }

        with patch(
            "custom_components.electrolux.number.format_command_for_appliance",
            return_value=1200,
        ):
            await entity.async_set_native_value(1200.0)

        call_args = entity.api.execute_appliance_command.call_args[0]  # type: ignore[union-attr]
        assert "commands" in call_args[1]

    @pytest.mark.asyncio
    async def test_set_value_latam_user_selections_empty_returns_early(
        self, mock_coordinator
    ):
        """When latamUserSelections is empty, method returns without command (line 675)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="spinSpeed",
            entity_source="latamUserSelections",
            pnc_id="1:TEST_PNC",
            capability={"type": "number", "min": 0, "max": 1600, "step": 200},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "ENABLED",
                    # No latamUserSelections key
                }
            }
        }

        with patch(
            "custom_components.electrolux.number.format_command_for_appliance",
            return_value=1200,
        ):
            await entity.async_set_native_value(1200.0)

        # api.execute_appliance_command should NOT have been called
        entity.api.execute_appliance_command.assert_not_called()  # type: ignore[union-attr]

    # ------------------------------------------------------------------ #
    # Line 706: DAM entity userSelections with valid programUID
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_set_value_dam_user_selections_with_valid_program_uid(
        self, mock_coordinator
    ):
        """DAM + userSelections with valid programUID sends full userSelections command (line 706)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="antiCreaseValue",
            entity_source="userSelections",
            pnc_id="1:TEST_PNC",
            capability={"type": "number", "min": 0, "max": 100, "step": 10},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "ENABLED",
                    "userSelections": {"programUID": "COTTON", "antiCreaseValue": 30},
                }
            }
        }

        with patch(
            "custom_components.electrolux.number.format_command_for_appliance",
            return_value=60,
        ):
            await entity.async_set_native_value(60.0)

        call_args = entity.api.execute_appliance_command.call_args[0]  # type: ignore[union-attr]
        assert "commands" in call_args[1]

    # ------------------------------------------------------------------ #
    # Line 780: available delegates to super
    # ------------------------------------------------------------------ #

    def test_available_delegates_to_super(self, mock_coordinator):
        """available property delegates to super().available (line 780)."""
        from unittest.mock import PropertyMock
        from custom_components.electrolux.entity import ElectroluxEntity

        entity = self._make_entity(mock_coordinator)
        with patch.object(
            ElectroluxEntity,
            "available",
            new_callable=PropertyMock,
            return_value=True,
        ):
            assert entity.available is True

    # ------------------------------------------------------------------ #
    # Line 152: mode → SLIDER when native_min/max/step has None or step==0
    # ------------------------------------------------------------------ #

    def test_mode_slider_when_step_is_zero(self, mock_coordinator):
        """When native_step returns 0, mode is SLIDER (line 152)."""
        from homeassistant.components.number import NumberMode
        from unittest.mock import PropertyMock

        entity = self._make_entity(mock_coordinator)
        with patch.object(
            type(entity), "native_step", new_callable=PropertyMock, return_value=0
        ):
            assert entity.mode == NumberMode.SLIDER

    def test_mode_slider_when_max_is_none(self, mock_coordinator):
        """When native_max_value returns None, mode is SLIDER (line 152)."""
        from homeassistant.components.number import NumberMode
        from unittest.mock import PropertyMock

        entity = self._make_entity(mock_coordinator)
        with patch.object(
            type(entity),
            "native_max_value",
            new_callable=PropertyMock,
            return_value=None,
        ):
            assert entity.mode == NumberMode.SLIDER

    # ------------------------------------------------------------------ #
    # Lines 185-186: mode → BOX when num_steps > NUMBER_MODE_SLIDER_MAX_STEPS
    # ------------------------------------------------------------------ #

    def test_mode_box_when_many_steps(self, mock_coordinator):
        """When num_steps > slider max, mode is BOX (lines 185-186)."""
        from homeassistant.components.number import NumberMode
        from unittest.mock import PropertyMock

        entity = self._make_entity(mock_coordinator)
        # 0-1439 min with step 1 = 1440 steps → BOX
        with (
            patch.object(
                type(entity),
                "native_min_value",
                new_callable=PropertyMock,
                return_value=0,
            ),
            patch.object(
                type(entity),
                "native_max_value",
                new_callable=PropertyMock,
                return_value=1439,
            ),
            patch.object(
                type(entity), "native_step", new_callable=PropertyMock, return_value=1
            ),
        ):
            assert entity.mode == NumberMode.BOX

    # ------------------------------------------------------------------ #
    # Line 210: device_class — capability_type "temperature" with _device_class=None string
    # ------------------------------------------------------------------ #

    def test_device_class_returns_none_when_no_catalog_no_device_class_no_temp(
        self, mock_coordinator
    ):
        """Device class is None when capability type isn't temperature (line 202+217)."""
        from homeassistant.components.number import NumberDeviceClass

        entity = self._make_entity(
            mock_coordinator,
            capability={"type": "number", "min": 0, "max": 100, "step": 1},
        )
        entity._catalog_entry = None
        entity._device_class = None
        # capability type is "number" not "temperature", so returns None (line 217)
        assert entity.device_class is None

    # ------------------------------------------------------------------ #
    # Line 248: native_value → None when value stays None (no defaults)
    # ------------------------------------------------------------------ #

    def test_native_value_returns_none_when_no_defaults(self, mock_coordinator):
        """native_value returns None for non-temp, non-duration entity with no defaults (line 248)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="someOtherAttr",
            capability={"type": "number"},  # no min/max/default
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with patch.object(type(entity), "extract_value", return_value=None):
            result = entity.native_value

        assert result is None

    # ------------------------------------------------------------------ #
    # Line 321: food probe NOT_INSERTED (with is_connected=True)
    # ------------------------------------------------------------------ #

    def test_is_locked_food_probe_not_inserted_connected(self, mock_coordinator):
        """food probe locked when NOT_INSERTED and connected (line 321)."""
        from custom_components.electrolux.const import FOOD_PROBE_STATE_NOT_INSERTED

        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetFoodProbeTemperatureC",
        )
        # Use the setter which updates both appliance_status and _reported_state_cache
        entity.reported_state = {
            "connectivityState": "connected",
            "foodProbeInsertionState": FOOD_PROBE_STATE_NOT_INSERTED,
        }
        entity._get_program_constraint = MagicMock(return_value=None)
        entity._is_supported_by_program = MagicMock(return_value=True)
        assert entity._is_locked_by_program() is True

    # ------------------------------------------------------------------ #
    # Line 370: _get_locked_value — global capability default (numeric)
    # ------------------------------------------------------------------ #

    def test_get_locked_value_global_capability_default_numeric(self, mock_coordinator):
        """_get_locked_value returns capability default when no program values (line 370)."""
        entity = self._make_entity(
            mock_coordinator,
            capability={"type": "number", "min": 0, "max": 100, "default": 42.0},
        )
        # program constraint returns None for all keys
        entity._get_program_constraint = MagicMock(return_value=None)
        result = entity._get_locked_value()
        assert result == 42.0

    # ------------------------------------------------------------------ #
    # Lines 388-390: native_unit_of_measurement SECONDS → MINUTES
    # ------------------------------------------------------------------ #

    def test_native_unit_of_measurement_seconds_to_minutes_conversion(
        self, mock_coordinator
    ):
        """SECONDS unit is converted to MINUTES for UI display (lines 388-390)."""
        entity = self._make_entity(
            mock_coordinator,
            unit=UnitOfTime.SECONDS,
        )
        assert entity.native_unit_of_measurement == UnitOfTime.MINUTES

    # ------------------------------------------------------------------ #
    # Line 419: _get_converted_constraint — locked + SECONDS path
    # ------------------------------------------------------------------ #

    def test_get_converted_constraint_locked_time_entity_converts_to_minutes(
        self, mock_coordinator
    ):
        """Locked time entity converts locked_value from seconds to minutes (line 419)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetDuration",
            unit=UnitOfTime.SECONDS,
        )
        entity._is_locked_by_program = MagicMock(return_value=True)
        entity._get_locked_value = MagicMock(return_value=60.0)  # 60 seconds

        result = entity._get_converted_constraint("max")
        assert result == 1.0  # 60 seconds → 1 minute

    # ------------------------------------------------------------------ #
    # Line 444: catalog non-numeric falls through, catalog time entity seconds→minutes
    # ------------------------------------------------------------------ #

    def test_get_converted_constraint_catalog_numeric_seconds_to_minutes(
        self, mock_coordinator
    ):
        """Catalog numeric value for time entity is converted from seconds to minutes (line 444)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetDuration",
            unit=UnitOfTime.SECONDS,
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        mock_catalog = MagicMock()
        mock_catalog.capability_info = {"max": 3600}  # 3600 seconds = 60 minutes
        entity._catalog_entry = mock_catalog

        result = entity._get_converted_constraint("max")
        assert result == 60.0

    # ------------------------------------------------------------------ #
    # Lines 504-506: _get_converted_constraint step with val from time conversion
    # ------------------------------------------------------------------ #

    def test_get_converted_constraint_step_time_entity_converts_to_minutes(
        self, mock_coordinator
    ):
        """Step for time entity with val is converted from seconds to minutes (lines 504-506)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetDuration",
            unit=UnitOfTime.SECONDS,
            capability={"type": "number", "step": 60},  # 60 seconds step = 1 minute
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._catalog_entry = None
        entity._get_program_constraint = MagicMock(return_value=60)  # 60s step

        result = entity._get_converted_constraint("step")
        assert result == 1.0  # 60 seconds → 1 minute

    # ------------------------------------------------------------------ #
    # Lines 611-618: async_set_native_value range errors
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_set_native_value_below_min_raises(self, mock_coordinator):
        """Value below min raises HomeAssistantError with 'below minimum' (lines 611-618)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureC",
            capability={"type": "temperature", "min": 30, "max": 230, "step": 5},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with pytest.raises(HomeAssistantError, match="below minimum"):
            await entity.async_set_native_value(5.0)

    @pytest.mark.asyncio
    async def test_set_native_value_above_max_raises(self, mock_coordinator):
        """Value above max raises HomeAssistantError with 'above maximum' (lines 611-618)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureC",
            capability={"type": "temperature", "min": 30, "max": 230, "step": 5},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        entity.reported_state = {"connectivityState": "connected"}

        with pytest.raises(HomeAssistantError, match="above maximum"):
            await entity.async_set_native_value(999.0)

    # ------------------------------------------------------------------ #
    # Line 798: available delegates to ElectroluxEntity.available
    # ------------------------------------------------------------------ #

    def test_available_property_returns_super_result_false(self, mock_coordinator):
        """available delegates to super and can return False too (line 798)."""
        from unittest.mock import PropertyMock
        from custom_components.electrolux.entity import ElectroluxEntity

        entity = self._make_entity(mock_coordinator)
        with patch.object(
            ElectroluxEntity,
            "available",
            new_callable=PropertyMock,
            return_value=False,
        ):
            assert entity.available is False

    # ------------------------------------------------------------------ #
    # TARGETED FIXES — for lines that appeared covered but weren't in
    # the full-suite coverage run
    # ------------------------------------------------------------------ #

    # Line 185-186: catalog device_class is NumberDeviceClass (not "temperature" string)
    def test_device_class_catalog_non_temperature_number_device_class(
        self, mock_coordinator
    ):
        """Catalog device_class = HUMIDITY hits isinstance branch (lines 185-186)."""
        from homeassistant.components.number import NumberDeviceClass

        entity = self._make_entity(mock_coordinator)
        mock_catalog = MagicMock()
        mock_catalog.device_class = NumberDeviceClass.HUMIDITY  # NOT "temperature"
        entity._catalog_entry = mock_catalog
        assert entity.device_class == NumberDeviceClass.HUMIDITY

    # Line 210: native_value returns None when offline (entity_attr != "connectivityState")
    def test_native_value_returns_none_when_offline(self, mock_coordinator):
        """native_value returns None when offline and attr != connectivityState (line 210)."""
        entity = self._make_entity(mock_coordinator, entity_attr="targetTemperatureC")
        # Set disconnected state
        entity.reported_state = {"connectivityState": "disconnected"}
        result = entity.native_value
        assert result is None

    # Line 217: locked_value time conversion in native_value
    def test_native_value_locked_seconds_to_minutes(self, mock_coordinator):
        """Locked time entity: locked_value converted seconds->minutes in native_value (line 217)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetDuration",
            unit=UnitOfTime.SECONDS,
            capability={"type": "number", "min": 0, "max": 86400, "default": 3600},
        )
        entity.reported_state = {"connectivityState": "connected"}
        # Make entity locked (min=max = step=0)
        entity._get_program_constraint = MagicMock(
            side_effect=lambda k: {"min": 60.0, "max": 60.0, "step": 1.0}.get(k)
        )
        entity._is_supported_by_program = MagicMock(return_value=True)
        # 60 seconds locked value → 1 minute displayed
        result = entity.native_value
        assert result == 1.0

    # Line 321: _is_locked_by_program return False for time entities
    def test_is_locked_returns_false_for_target_duration(self, mock_coordinator):
        """targetDuration is never locked by program (line 321 = return False for time entities)."""
        entity = self._make_entity(mock_coordinator, entity_attr="targetDuration")
        entity._get_program_constraint = MagicMock(return_value=None)
        entity._is_supported_by_program = MagicMock(
            return_value=False
        )  # even if unsupported
        assert entity._is_locked_by_program() is False

    def test_is_locked_returns_false_for_program(self, mock_coordinator):
        """program entity is never locked (line 321 = return False for program attr)."""
        entity = self._make_entity(mock_coordinator, entity_attr="program")
        entity._get_program_constraint = MagicMock(return_value=None)
        entity._is_supported_by_program = MagicMock(return_value=False)
        assert entity._is_locked_by_program() is False

    # Line 370: _get_locked_value uses program min fallback
    def test_get_locked_value_uses_program_min_when_no_default(self, mock_coordinator):
        """_get_locked_value returns program_min when program_default is None (line 370)."""
        entity = self._make_entity(mock_coordinator)
        entity._get_program_constraint = MagicMock(
            side_effect=lambda k: {"default": None, "min": 55.0}.get(k)
        )
        # program_default = None, program_min = 55.0 → returns 55.0
        assert entity._get_locked_value() == 55.0

    # Line 390: native_unit_of_measurement returns MINUTES for SECONDS unit
    def test_native_unit_measurement_seconds_unit_returns_minutes(
        self, mock_coordinator
    ):
        """SECONDS unit returns MINUTES from native_unit_of_measurement (line 390)."""
        entity = self._make_entity(mock_coordinator, unit=UnitOfTime.SECONDS)
        assert entity.native_unit_of_measurement == UnitOfTime.MINUTES

    # Line 444: catalog numeric val for NON-time entity returns float(cat_val)
    def test_get_converted_constraint_catalog_non_time_returns_float(
        self, mock_coordinator
    ):
        """Catalog constraint for non-time entity returns float(cat_val) directly (line 444)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureC",
            capability={"type": "temperature"},
            unit=UnitOfTemperature.CELSIUS,  # NOT SECONDS → hit line 444
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        mock_catalog = MagicMock()
        mock_catalog.capability_info = {"max": 230}
        entity._catalog_entry = mock_catalog

        result = entity._get_converted_constraint("max")
        assert result == 230.0

    # Lines 504-506: step where val=None from program+capability fallback
    def test_get_converted_constraint_step_no_program_no_capability(
        self, mock_coordinator
    ):
        """Step with no catalog, no program, no capability constraint uses DEFAULT_NUMBER_STEP (lines 504-506)."""
        from custom_components.electrolux.const import DEFAULT_NUMBER_STEP

        entity = self._make_entity(
            mock_coordinator,
            entity_attr="someAttr",
            capability={"type": "number"},  # no step defined
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._catalog_entry = None
        entity._get_program_constraint = MagicMock(return_value=None)  # no program step

        result = entity._get_converted_constraint("step")
        # No val → hits lines 504-506: get from capability (None), returns float(None or DEFAULT_NUMBER_STEP)
        assert result == DEFAULT_NUMBER_STEP

    # Lines 611-618: appliance offline in async_set_native_value
    @pytest.mark.asyncio
    async def test_set_native_value_raises_when_appliance_offline(
        self, mock_coordinator
    ):
        """Raises HomeAssistantError when appliance offline after range check (lines 611-618)."""
        entity = self._make_entity(
            mock_coordinator,
            entity_attr="targetTemperatureC",
            capability={"type": "temperature", "min": 30, "max": 230, "step": 5},
        )
        entity._is_locked_by_program = MagicMock(return_value=False)
        entity._is_supported_by_program = MagicMock(return_value=True)
        # NOT connected — offline
        entity.reported_state = {"connectivityState": "disconnected"}

        with pytest.raises(HomeAssistantError, match="offline"):
            await entity.async_set_native_value(100.0)

    # Line 798: available delegates to ElectroluxEntity.available (True)
    def test_available_delegates_to_entity_super_true(self, mock_coordinator):
        """available delegates to super().available (line 798) — returns True case."""
        from unittest.mock import PropertyMock
        from custom_components.electrolux.entity import ElectroluxEntity

        entity = self._make_entity(mock_coordinator)
        with patch.object(
            ElectroluxEntity,
            "available",
            new_callable=PropertyMock,
            return_value=True,
        ):
            assert entity.available is True
