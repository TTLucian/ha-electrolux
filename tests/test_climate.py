"""Tests for Electrolux climate platform."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import (
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature

from custom_components.electrolux.climate import ElectroluxClimate
from custom_components.electrolux.const import CLIMATE
from custom_components.electrolux.models import ApplianceState


@pytest.fixture
def ac_device_data():
    """Create mock AC device data."""
    return {
        "current_state": {
            "properties": {
                "reported": {
                    "applianceState": "RUNNING",
                    "mode": "COOL",
                    "ambientTemperatureC": 25.0,
                    "targetTemperatureC": 22.0,
                    "temperatureRepresentation": "CELSIUS",
                    "fanSpeedSetting": "AUTO",
                    "verticalSwing": "OFF",
                    "remoteControl": "ENABLED",
                    "applianceInfo": {
                        "applianceType": "AC",
                    },
                }
            }
        },
        "capabilities": {},
    }


class TestElectroluxClimate:
    """Test the Electrolux Climate entity."""

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
    def mock_appliance(self, ac_device_data):
        """Create a mock appliance."""
        appliance = MagicMock()
        appliance.appliance_type = "AC"
        appliance.pnc_id = "910280820_00:53501748-443E0777C770"
        appliance.name = "Ar condicionado"
        appliance.brand = "Electrolux"
        appliance.model = "910280820"
        appliance.state = ac_device_data["current_state"]
        appliance.reported_state = ac_device_data["current_state"]["properties"][
            "reported"
        ]
        appliance.get_cached_catalog.return_value = ac_device_data["capabilities"]
        return appliance

    @pytest.fixture
    def climate_entity(self, mock_appliance, mock_coordinator):
        """Create a test climate entity."""
        # Mock capability structure for air conditioner
        capability = {
            "mode": {
                "values": {
                    "AUTO": {},
                    "COOL": {},
                    "HEAT": {},
                    "DRY": {},
                    "FANONLY": {},
                }
            },
            "fanSpeedSetting": {
                "values": {
                    "AUTO": {},
                    "LOW": {},
                    "MIDDLE": {},
                    "HIGH": {},
                }
            },
            "verticalSwing": {
                "values": {
                    "OFF": {},
                    "ON": {},
                }
            },
            "targetTemperatureC": {
                "min": 16,
                "max": 30,
            },
        }

        entity = ElectroluxClimate(
            coordinator=mock_coordinator,
            name="Test AC",
            config_entry=mock_coordinator.config_entry,
            pnc_id=mock_appliance.pnc_id,
            entity_type=CLIMATE,
            entity_name="climate",
            entity_attr="climate",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:air-conditioner",
            catalog_entry=None,
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = mock_appliance.state
        entity._reported_state_cache = mock_appliance.reported_state
        # Mock methods that access appliance
        entity.get_state_attr = lambda path: mock_appliance.reported_state.get(path)
        return entity

    def test_entity_domain(self, climate_entity):
        """Test entity domain property."""
        assert climate_entity.entity_domain == CLIMATE

    def test_supported_features(self, climate_entity):
        """Test supported features."""
        from homeassistant.components.climate import ClimateEntityFeature

        features = climate_entity.supported_features
        assert features & ClimateEntityFeature.TARGET_TEMPERATURE
        assert features & ClimateEntityFeature.FAN_MODE
        assert features & ClimateEntityFeature.SWING_MODE

    def test_temperature_unit_celsius(self, climate_entity, mock_appliance):
        """Test temperature unit returns Celsius."""
        mock_appliance.reported_state["temperatureRepresentation"] = "CELSIUS"
        assert climate_entity.temperature_unit == UnitOfTemperature.CELSIUS

    def test_temperature_unit_fahrenheit(self, climate_entity, mock_appliance):
        """Test temperature unit returns Fahrenheit."""
        mock_appliance.reported_state["temperatureRepresentation"] = "FAHRENHEIT"
        assert climate_entity.temperature_unit == UnitOfTemperature.FAHRENHEIT

    def test_temperature_unit_default(self, climate_entity, mock_appliance):
        """Test temperature unit defaults to Celsius."""
        mock_appliance.reported_state.pop("temperatureRepresentation", None)
        assert climate_entity.temperature_unit == UnitOfTemperature.CELSIUS

    def test_current_temperature_celsius(self, climate_entity, mock_appliance):
        """Test current temperature from Celsius value."""
        mock_appliance.reported_state["ambientTemperatureC"] = 25.0
        assert climate_entity.current_temperature == 25.0

    def test_current_temperature_fahrenheit(self, climate_entity, mock_appliance):
        """Test current temperature from Fahrenheit value."""
        mock_appliance.reported_state.pop("ambientTemperatureC", None)
        mock_appliance.reported_state["ambientTemperatureF"] = 77.0
        assert climate_entity.current_temperature == 77.0

    def test_current_temperature_none(self, climate_entity, mock_appliance):
        """Test current temperature returns None when missing."""
        mock_appliance.reported_state.pop("ambientTemperatureC", None)
        mock_appliance.reported_state.pop("ambientTemperatureF", None)
        assert climate_entity.current_temperature is None

    def test_target_temperature_celsius(self, climate_entity, mock_appliance):
        """Test target temperature from Celsius value."""
        mock_appliance.reported_state["targetTemperatureC"] = 22.0
        assert climate_entity.target_temperature == 22.0

    def test_target_temperature_fahrenheit(self, climate_entity, mock_appliance):
        """Test target temperature from Fahrenheit value."""
        mock_appliance.reported_state.pop("targetTemperatureC", None)
        mock_appliance.reported_state["targetTemperatureF"] = 71.6
        assert climate_entity.target_temperature == 71.6

    def test_target_temperature_none(self, climate_entity, mock_appliance):
        """Test target temperature returns None when missing."""
        mock_appliance.reported_state.pop("targetTemperatureC", None)
        mock_appliance.reported_state.pop("targetTemperatureF", None)
        assert climate_entity.target_temperature is None

    def test_hvac_mode_off(self, climate_entity, mock_appliance):
        """Test HVAC mode returns OFF when appliance is off."""
        mock_appliance.reported_state["applianceState"] = "OFF"
        assert climate_entity.hvac_mode == HVACMode.OFF

    def test_hvac_mode_auto(self, climate_entity, mock_appliance):
        """Test HVAC mode returns AUTO."""
        mock_appliance.reported_state["applianceState"] = "RUNNING"
        mock_appliance.reported_state["mode"] = "AUTO"
        assert climate_entity.hvac_mode == HVACMode.AUTO

    def test_hvac_mode_cool(self, climate_entity, mock_appliance):
        """Test HVAC mode returns COOL."""
        mock_appliance.reported_state["applianceState"] = "RUNNING"
        mock_appliance.reported_state["mode"] = "COOL"
        assert climate_entity.hvac_mode == HVACMode.COOL

    def test_hvac_mode_heat(self, climate_entity, mock_appliance):
        """Test HVAC mode returns HEAT."""
        mock_appliance.reported_state["applianceState"] = "RUNNING"
        mock_appliance.reported_state["mode"] = "HEAT"
        assert climate_entity.hvac_mode == HVACMode.HEAT

    def test_hvac_mode_dry(self, climate_entity, mock_appliance):
        """Test HVAC mode returns DRY."""
        mock_appliance.reported_state["applianceState"] = "RUNNING"
        mock_appliance.reported_state["mode"] = "DRY"
        assert climate_entity.hvac_mode == HVACMode.DRY

    def test_hvac_mode_fan_only(self, climate_entity, mock_appliance):
        """Test HVAC mode returns FAN_ONLY."""
        mock_appliance.reported_state["applianceState"] = "RUNNING"
        mock_appliance.reported_state["mode"] = "FANONLY"
        assert climate_entity.hvac_mode == HVACMode.FAN_ONLY

    def test_hvac_modes_list(self, climate_entity):
        """Test HVAC modes list from capabilities."""
        modes = climate_entity.hvac_modes
        assert HVACMode.OFF in modes
        assert HVACMode.AUTO in modes
        assert HVACMode.COOL in modes
        assert HVACMode.DRY in modes
        assert HVACMode.FAN_ONLY in modes

    def test_hvac_action_cooling(self, climate_entity, mock_appliance):
        """Test HVAC action returns COOLING."""
        mock_appliance.reported_state["applianceState"] = "RUNNING"
        mock_appliance.reported_state["mode"] = "COOL"
        assert climate_entity.hvac_action == HVACAction.COOLING

    def test_hvac_action_heating(self, climate_entity, mock_appliance):
        """Test HVAC action returns HEATING."""
        mock_appliance.reported_state["applianceState"] = "RUNNING"
        mock_appliance.reported_state["mode"] = "HEAT"
        assert climate_entity.hvac_action == HVACAction.HEATING

    def test_hvac_action_idle(self, climate_entity, mock_appliance):
        """Test HVAC action returns IDLE."""
        mock_appliance.reported_state["applianceState"] = "IDLE"
        assert climate_entity.hvac_action == HVACAction.IDLE

    def test_hvac_action_off(self, climate_entity, mock_appliance):
        """Test HVAC action returns OFF."""
        mock_appliance.reported_state["applianceState"] = "OFF"
        assert climate_entity.hvac_action == HVACAction.OFF

    def test_fan_mode(self, climate_entity, mock_appliance):
        """Test fan mode property."""
        mock_appliance.reported_state["fanSpeedSetting"] = "AUTO"
        assert climate_entity.fan_mode == "auto"

    def test_fan_modes_list(self, climate_entity):
        """Test fan modes list from capabilities."""
        modes = climate_entity.fan_modes
        assert "auto" in modes
        assert "low" in modes
        assert "middle" in modes
        assert "high" in modes

    def test_swing_mode(self, climate_entity, mock_appliance):
        """Test swing mode property."""
        mock_appliance.reported_state["verticalSwing"] = "OFF"
        assert climate_entity.swing_mode == "off"

    def test_swing_modes_list(self, climate_entity):
        """Test swing modes list from capabilities."""
        modes = climate_entity.swing_modes
        assert "off" in modes
        assert "on" in modes

    def test_min_temp_from_capability(self, climate_entity):
        """Test min temperature from capabilities."""
        assert climate_entity.min_temp == 16.0

    def test_min_temp_default(self, mock_coordinator):
        """Test min temperature default value."""
        entity = ElectroluxClimate(
            coordinator=mock_coordinator,
            name="Test AC",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=CLIMATE,
            entity_name="climate",
            entity_attr="climate",
            entity_source=None,
            capability={},  # Empty capability
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:air-conditioner",
            catalog_entry=None,
        )
        assert entity.min_temp == 16.0

    def test_max_temp_from_capability(self, climate_entity):
        """Test max temperature from capabilities."""
        assert climate_entity.max_temp == 30.0

    def test_max_temp_default(self, mock_coordinator):
        """Test max temperature default value."""
        entity = ElectroluxClimate(
            coordinator=mock_coordinator,
            name="Test AC",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=CLIMATE,
            entity_name="climate",
            entity_attr="climate",
            entity_source=None,
            capability={},  # Empty capability
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:air-conditioner",
            catalog_entry=None,
        )
        assert entity.max_temp == 30.0

    @pytest.mark.asyncio
    async def test_async_set_temperature_celsius(self, climate_entity, mock_appliance):
        """Test setting temperature in Celsius."""
        climate_entity._send_command = AsyncMock()
        mock_appliance.reported_state["temperatureRepresentation"] = "CELSIUS"

        await climate_entity.async_set_temperature(temperature=24.0)

        climate_entity._send_command.assert_called_once_with("targetTemperatureC", 24.0)

    @pytest.mark.asyncio
    async def test_async_set_temperature_fahrenheit(
        self, climate_entity, mock_appliance
    ):
        """Test setting temperature in Fahrenheit."""
        climate_entity._send_command = AsyncMock()
        mock_appliance.reported_state["temperatureRepresentation"] = "FAHRENHEIT"

        await climate_entity.async_set_temperature(temperature=75.0)

        climate_entity._send_command.assert_called_once_with("targetTemperatureF", 75.0)

    @pytest.mark.asyncio
    async def test_async_set_temperature_no_value(self, climate_entity):
        """Test setting temperature with no value does nothing."""
        climate_entity._send_command = AsyncMock()

        await climate_entity.async_set_temperature()

        climate_entity._send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_set_hvac_mode_off(self, climate_entity):
        """Test setting HVAC mode to OFF."""
        climate_entity._send_command = AsyncMock()

        await climate_entity.async_set_hvac_mode(HVACMode.OFF)

        climate_entity._send_command.assert_called_once_with("executeCommand", "OFF")

    @pytest.mark.asyncio
    async def test_async_set_hvac_mode_cool(self, climate_entity):
        """Test setting HVAC mode to COOL."""
        climate_entity._send_command = AsyncMock()

        await climate_entity.async_set_hvac_mode(HVACMode.COOL)

        assert climate_entity._send_command.call_count == 2
        calls = climate_entity._send_command.call_args_list
        assert calls[0][0] == ("executeCommand", "ON")
        assert calls[1][0] == ("mode", "COOL")

    @pytest.mark.asyncio
    async def test_async_set_hvac_mode_auto(self, climate_entity):
        """Test setting HVAC mode to AUTO."""
        climate_entity._send_command = AsyncMock()

        await climate_entity.async_set_hvac_mode(HVACMode.AUTO)

        assert climate_entity._send_command.call_count == 2
        calls = climate_entity._send_command.call_args_list
        assert calls[0][0] == ("executeCommand", "ON")
        assert calls[1][0] == ("mode", "AUTO")

    @pytest.mark.asyncio
    async def test_async_set_hvac_mode_heat(self, climate_entity):
        """Test setting HVAC mode to HEAT."""
        climate_entity._send_command = AsyncMock()

        await climate_entity.async_set_hvac_mode(HVACMode.HEAT)

        assert climate_entity._send_command.call_count == 2
        calls = climate_entity._send_command.call_args_list
        assert calls[0][0] == ("executeCommand", "ON")
        assert calls[1][0] == ("mode", "HEAT")

    @pytest.mark.asyncio
    async def test_async_set_hvac_mode_dry(self, climate_entity):
        """Test setting HVAC mode to DRY."""
        climate_entity._send_command = AsyncMock()

        await climate_entity.async_set_hvac_mode(HVACMode.DRY)

        assert climate_entity._send_command.call_count == 2
        calls = climate_entity._send_command.call_args_list
        assert calls[0][0] == ("executeCommand", "ON")
        assert calls[1][0] == ("mode", "DRY")

    @pytest.mark.asyncio
    async def test_async_set_hvac_mode_fan_only(self, climate_entity):
        """Test setting HVAC mode to FAN_ONLY."""
        climate_entity._send_command = AsyncMock()

        await climate_entity.async_set_hvac_mode(HVACMode.FAN_ONLY)

        assert climate_entity._send_command.call_count == 2
        calls = climate_entity._send_command.call_args_list
        assert calls[0][0] == ("executeCommand", "ON")
        assert calls[1][0] == ("mode", "FANONLY")

    @pytest.mark.asyncio
    async def test_async_set_fan_mode(self, climate_entity):
        """Test setting fan mode."""
        climate_entity._send_command = AsyncMock()

        await climate_entity.async_set_fan_mode("low")

        climate_entity._send_command.assert_called_once_with("fanMode", "LOW")

    @pytest.mark.asyncio
    async def test_async_set_swing_mode(self, climate_entity):
        """Test setting swing mode."""
        climate_entity._send_command = AsyncMock()

        await climate_entity.async_set_swing_mode("on")

        climate_entity._send_command.assert_called_once_with("swingMode", "ON")

    @pytest.mark.asyncio
    async def test_send_command_legacy_appliance(self, climate_entity, mock_appliance):
        """Test sending command to legacy appliance."""
        mock_api = AsyncMock()
        climate_entity.api = mock_api

        with patch.object(
            type(climate_entity),
            "is_dam_appliance",
            new_callable=lambda: property(lambda self: False),
        ):
            with patch(
                "custom_components.electrolux.climate.execute_command_with_error_handling",
                AsyncMock(),
            ) as mock_execute:
                await climate_entity._send_command("targetTemperatureC", 24.0)

                mock_execute.assert_called_once()
                call_args = mock_execute.call_args[0]
                command = call_args[2]
                assert command == {"targetTemperatureC": 24.0}

    @pytest.mark.asyncio
    async def test_send_command_dam_appliance(self, climate_entity, mock_appliance):
        """Test sending command to DAM appliance."""
        climate_entity.entity_source = "airConditioner"
        mock_api = AsyncMock()
        climate_entity.api = mock_api

        with patch.object(
            type(climate_entity),
            "is_dam_appliance",
            new_callable=lambda: property(lambda self: True),
        ):
            with patch(
                "custom_components.electrolux.climate.execute_command_with_error_handling",
                AsyncMock(),
            ) as mock_execute:
                await climate_entity._send_command("targetTemperatureC", 24.0)

                mock_execute.assert_called_once()
                call_args = mock_execute.call_args[0]
                command = call_args[2]
                assert "commands" in command
                assert len(command["commands"]) == 1
                assert "airConditioner" in command["commands"][0]
                assert (
                    command["commands"][0]["airConditioner"]["targetTemperatureC"]
                    == 24.0
                )

    @pytest.mark.asyncio
    async def test_send_command_error_handling(self, climate_entity):
        """Test error handling in send command."""
        mock_api = AsyncMock()
        climate_entity.api = mock_api

        with patch.object(
            type(climate_entity),
            "is_dam_appliance",
            new_callable=lambda: property(lambda self: False),
        ):
            with patch(
                "custom_components.electrolux.climate.execute_command_with_error_handling",
                AsyncMock(side_effect=Exception("Command failed")),
            ):
                with pytest.raises(Exception, match="Command failed"):
                    await climate_entity._send_command("targetTemperatureC", 24.0)


# Appliance Type Detection Tests (Bug Fix Verification)


def test_appliance_type_detection(ac_device_data: dict) -> None:
    """Test that appliance_type property correctly reads from applianceInfo."""
    from custom_components.electrolux.models import Appliance

    mock_coordinator = MagicMock()

    appliance = Appliance(
        coordinator=mock_coordinator,
        name="Test AC",
        pnc_id="910280820_00:53501748-443E0777C770",
        brand="Electrolux",
        model="910280820",
        state=ac_device_data["current_state"],
    )

    # Verify appliance_type is correctly detected as "AC"
    assert appliance.appliance_type == "AC"


def test_appliance_type_detection_oven() -> None:
    """Test that appliance_type property correctly reads for non-AC appliances."""
    from custom_components.electrolux.models import Appliance

    mock_coordinator = MagicMock()

    oven_state = cast(
        ApplianceState,
        {
            "applianceId": "test_oven_123",
            "connectionState": "connected",
            "status": "enabled",
            "properties": {
                "reported": {
                    "applianceInfo": {"applianceType": "OV"},  # Oven, not AC
                    "applianceState": "OFF",
                }
            },
        },
    )

    appliance = Appliance(
        coordinator=mock_coordinator,
        name="Test Oven",
        pnc_id="test_oven_123",
        brand="Electrolux",
        model="TESTOV",
        state=oven_state,
    )

    # Verify appliance_type is correctly detected as "OV"
    assert appliance.appliance_type == "OV"


def test_appliance_type_detection_missing() -> None:
    """Test that appliance_type returns None when applianceInfo is missing."""
    from custom_components.electrolux.models import Appliance

    mock_coordinator = MagicMock()

    state_without_appliance_info = cast(
        ApplianceState,
        {
            "applianceId": "test_unknown_123",
            "connectionState": "connected",
            "status": "enabled",
            "properties": {
                "reported": {
                    # Missing applianceInfo
                    "applianceState": "OFF",
                }
            },
        },
    )

    appliance = Appliance(
        coordinator=mock_coordinator,
        name="Test Unknown",
        pnc_id="test_unknown_123",
        brand="Electrolux",
        model="TESTXXX",
        state=state_without_appliance_info,
    )

    # Verify appliance_type returns None when missing
    assert appliance.appliance_type is None


def test_climate_entity_filtering(ac_device_data: dict) -> None:
    """Test that climate entity creation logic filters by appliance_type."""
    from custom_components.electrolux.models import Appliance

    mock_coordinator = MagicMock()

    # Create AC appliance
    ac_appliance = Appliance(
        coordinator=mock_coordinator,
        name="Test AC",
        pnc_id="910280820_00:53501748-443E0777C770",
        brand="Electrolux",
        model="910280820",
        state=ac_device_data["current_state"],
    )

    # Create Oven appliance
    oven_state = cast(
        ApplianceState,
        {
            "applianceId": "test_oven_123",
            "connectionState": "connected",
            "status": "enabled",
            "properties": {
                "reported": {
                    "applianceInfo": {"applianceType": "OV"},
                    "applianceState": "OFF",
                }
            },
        },
    )
    oven_appliance = Appliance(
        coordinator=mock_coordinator,
        name="Test Oven",
        pnc_id="test_oven_123",
        brand="Electrolux",
        model="TESTOV",
        state=oven_state,
    )

    # Simulate climate entity creation logic
    assert ac_appliance.appliance_type == "AC"  # Should create climate entity
    assert oven_appliance.appliance_type == "OV"  # Should NOT create climate entity
