"""Tests for vacuum.py - ElectroluxVacuum entity."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.vacuum.const import VacuumActivity, VacuumEntityFeature

from custom_components.electrolux.const import VACUUM
from custom_components.electrolux.vacuum import ElectroluxVacuum


def _make_coordinator(battery_min=1, battery_max=6):
    coordinator = MagicMock()
    coordinator.hass = MagicMock()
    coordinator.config_entry = MagicMock()
    appliance_data = MagicMock()
    appliance_data.capabilities = {
        "CleaningCommand": {
            "access": "readwrite",
            "type": "string",
            "values": {
                "play": {},
                "stop": {},
                "pause": {},
                "home": {},
            },
        },
        "powerMode": {
            "access": "readwrite",
            "type": "int",
            "min": 1,
            "max": 3,
        },
        "batteryStatus": {
            "access": "read",
            "type": "int",
            "min": battery_min,
            "max": battery_max,
        },
    }
    appliance = MagicMock()
    appliance.data = appliance_data
    appliances = MagicMock()
    appliances.appliances = {"RVC_PNC": appliance}
    appliances.get_appliance.return_value = appliance
    coordinator.data = {"appliances": appliances}
    return coordinator


def _make_purei9_vacuum(
    battery_min=1, battery_max=6, battery_status=5, robot_status=10
) -> ElectroluxVacuum:
    coordinator = _make_coordinator(battery_min=battery_min, battery_max=battery_max)
    vacuum = ElectroluxVacuum(
        coordinator=coordinator,
        name="Test Vacuum",
        config_entry=coordinator.config_entry,
        pnc_id="RVC_PNC",
        entity_type=VACUUM,
        entity_name="vacuum",
        entity_attr="vacuum",
        entity_source=None,
        capability={},
        unit=None,
        device_class=None,
        entity_category=None,
        icon="mdi:robot-vacuum",
        catalog_entry=None,
        appliance_type="PUREi9",
    )
    vacuum.hass = coordinator.hass
    vacuum.appliance_status = {
        "properties": {
            "reported": {
                "robotStatus": robot_status,
                "powerMode": 2,
                "batteryStatus": battery_status,
            }
        }
    }
    vacuum.reported_state = vacuum.appliance_status["properties"]["reported"]
    return vacuum


def _make_modern_vacuum(
    battery_status=50, state="idle", in_charger=False, appliance_type="Gordias"
) -> ElectroluxVacuum:
    coordinator = _make_coordinator(battery_min=0, battery_max=100)
    vacuum = ElectroluxVacuum(
        coordinator=coordinator,
        name="Test Vacuum Modern",
        config_entry=coordinator.config_entry,
        pnc_id="RVC_MODERN_PNC",
        entity_type=VACUUM,
        entity_name="vacuum",
        entity_attr="vacuum",
        entity_source=None,
        capability={},
        unit=None,
        device_class=None,
        entity_category=None,
        icon="mdi:robot-vacuum",
        catalog_entry=None,
        appliance_type=appliance_type,
    )
    vacuum.hass = coordinator.hass
    vacuum.appliance_status = {
        "properties": {
            "reported": {
                "state": state,
                "vacuumMode": "energySaving",
                "batteryStatus": battery_status,
                "inCharger": in_charger,
            }
        }
    }
    vacuum.reported_state = vacuum.appliance_status["properties"]["reported"]
    return vacuum


class TestElectroluxVacuumPurei9:
    def test_fan_speed_list_uses_numeric_power_modes(self):
        vacuum = _make_purei9_vacuum()

        assert vacuum.fan_speed_list == ["1", "2", "3"]

    def test_battery_level_scales_purei9_levels_to_percentage(self):
        vacuum = _make_purei9_vacuum()

        assert vacuum.battery_level == 80

    def test_battery_level_preserves_true_percentage_ranges(self):
        vacuum = _make_purei9_vacuum(battery_min=1, battery_max=100, battery_status=80)

        assert vacuum.battery_level == 80

    @pytest.mark.asyncio
    async def test_async_set_fan_speed_sends_numeric_power_mode(self):
        vacuum = _make_purei9_vacuum()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_set_fan_speed("3")

        mock_execute.assert_awaited_once()
        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "powerMode"
        assert command == {"powerMode": 3}

    def test_activity_returns_cleaning_for_robot_status_1(self):
        """PUREi9 status 1 = cleaning."""
        vacuum = _make_purei9_vacuum(robot_status=1)
        assert vacuum.activity == VacuumActivity.CLEANING

    def test_activity_returns_paused_for_robot_status_2(self):
        """PUREi9 status 2 = paused cleaning."""
        vacuum = _make_purei9_vacuum(robot_status=2)
        assert vacuum.activity == VacuumActivity.PAUSED

    def test_activity_returns_error_for_robot_status_11(self):
        """PUREi9 status 11 = error."""
        vacuum = _make_purei9_vacuum(robot_status=11)
        assert vacuum.activity == VacuumActivity.ERROR

    def test_activity_returns_returning_for_robot_status_13(self):
        """PUREi9 status 13 = going home."""
        vacuum = _make_purei9_vacuum(robot_status=13)
        assert vacuum.activity == VacuumActivity.RETURNING

    def test_activity_returns_docked_for_robot_status_9(self):
        """PUREi9 status 9 = docked."""
        vacuum = _make_purei9_vacuum(robot_status=9)
        assert vacuum.activity == VacuumActivity.DOCKED

    def test_activity_returns_none_for_invalid_robot_status(self):
        """Invalid robotStatus value returns None."""
        vacuum = _make_purei9_vacuum()
        status: dict[str, Any] = cast(dict, vacuum.appliance_status)
        if "properties" in status and "reported" in status["properties"]:
            status["properties"]["reported"]["robotStatus"] = "invalid"
            vacuum.reported_state = status["properties"]["reported"]
            assert vacuum.activity is None

    def test_activity_returns_none_when_robot_status_missing(self):
        """Missing robotStatus returns None."""
        vacuum = _make_purei9_vacuum()
        status: dict[str, Any] = cast(dict, vacuum.appliance_status)
        if "properties" in status and "reported" in status["properties"]:
            del status["properties"]["reported"]["robotStatus"]
            vacuum.reported_state = status["properties"]["reported"]
            assert vacuum.activity is None

    @pytest.mark.asyncio
    async def test_async_start_sends_play_command(self):
        """PUREi9 start sends CleaningCommand=play."""
        vacuum = _make_purei9_vacuum()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_start()

        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "CleaningCommand"
        assert command == {"CleaningCommand": "play"}

    @pytest.mark.asyncio
    async def test_async_stop_sends_stop_command(self):
        """PUREi9 stop sends CleaningCommand=stop."""
        vacuum = _make_purei9_vacuum()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_stop()

        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "CleaningCommand"
        assert command == {"CleaningCommand": "stop"}

    @pytest.mark.asyncio
    async def test_async_pause_sends_pause_command(self):
        """PUREi9 pause sends CleaningCommand=pause."""
        vacuum = _make_purei9_vacuum()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_pause()

        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "CleaningCommand"
        assert command == {"CleaningCommand": "pause"}

    @pytest.mark.asyncio
    async def test_async_return_to_base_sends_home_command(self):
        """PUREi9 return to base sends CleaningCommand=home."""
        vacuum = _make_purei9_vacuum()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_return_to_base()

        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "CleaningCommand"
        assert command == {"CleaningCommand": "home"}

    def test_battery_level_returns_none_for_invalid_battery_status(self):
        """Invalid batteryStatus value returns None."""
        vacuum = _make_purei9_vacuum()
        status: dict[str, Any] = cast(dict, vacuum.appliance_status)
        if "properties" in status and "reported" in status["properties"]:
            status["properties"]["reported"]["batteryStatus"] = "invalid"
            vacuum.reported_state = status["properties"]["reported"]
            assert vacuum.battery_level is None

    def test_battery_level_returns_none_when_battery_missing(self):
        """Missing batteryStatus returns None."""
        vacuum = _make_purei9_vacuum()
        status: dict[str, Any] = cast(dict, vacuum.appliance_status)
        if "properties" in status and "reported" in status["properties"]:
            del status["properties"]["reported"]["batteryStatus"]
            vacuum.reported_state = status["properties"]["reported"]
            assert vacuum.battery_level is None

    def test_fan_speed_returns_current_power_mode(self):
        """fan_speed property returns current powerMode."""
        vacuum = _make_purei9_vacuum()
        assert vacuum.fan_speed == "2"

    def test_supported_features_includes_all_expected_features(self):
        """Vacuum supports start, stop, pause, return_home, battery, fan_speed."""
        vacuum = _make_purei9_vacuum()
        features = vacuum.supported_features
        assert features & VacuumEntityFeature.START
        assert features & VacuumEntityFeature.STOP
        assert features & VacuumEntityFeature.PAUSE
        assert features & VacuumEntityFeature.RETURN_HOME
        assert features & VacuumEntityFeature.BATTERY
        assert features & VacuumEntityFeature.FAN_SPEED


class TestElectroluxVacuumModern:
    """Test modern appliance types (Cybele, Gordias, 700series)."""

    def test_fan_speed_list_returns_modern_values(self):
        vacuum = _make_modern_vacuum()
        assert vacuum.fan_speed_list == ["energySaving", "max"]

    def test_activity_returns_cleaning_for_in_progress_state(self):
        vacuum = _make_modern_vacuum(state="inProgress")
        assert vacuum.activity == VacuumActivity.CLEANING

    def test_activity_returns_cleaning_for_mopping_state(self):
        vacuum = _make_modern_vacuum(state="mopping")
        assert vacuum.activity == VacuumActivity.CLEANING

    def test_activity_returns_cleaning_for_pit_stop_state(self):
        vacuum = _make_modern_vacuum(state="pitStop")
        assert vacuum.activity == VacuumActivity.CLEANING

    def test_activity_returns_docked_for_station_action(self):
        vacuum = _make_modern_vacuum(state="stationAction")
        assert vacuum.activity == VacuumActivity.DOCKED

    def test_activity_returns_returning_for_going_home(self):
        vacuum = _make_modern_vacuum(state="goingHome")
        assert vacuum.activity == VacuumActivity.RETURNING

    def test_activity_returns_paused_for_paused_state(self):
        vacuum = _make_modern_vacuum(state="paused")
        assert vacuum.activity == VacuumActivity.PAUSED

    def test_activity_returns_idle_when_not_in_charger(self):
        vacuum = _make_modern_vacuum(state="idle", in_charger=False)
        assert vacuum.activity == VacuumActivity.IDLE

    def test_activity_returns_docked_when_idle_and_in_charger(self):
        vacuum = _make_modern_vacuum(state="idle", in_charger=True)
        assert vacuum.activity == VacuumActivity.DOCKED

    def test_activity_returns_docked_when_sleeping_and_in_charger(self):
        vacuum = _make_modern_vacuum(state="sleeping", in_charger=True)
        assert vacuum.activity == VacuumActivity.DOCKED

    def test_activity_returns_idle_when_sleeping_not_in_charger(self):
        vacuum = _make_modern_vacuum(state="sleeping", in_charger=False)
        assert vacuum.activity == VacuumActivity.IDLE

    def test_activity_returns_none_for_unknown_state(self):
        vacuum = _make_modern_vacuum(state="unknown_state")
        assert vacuum.activity is None

    def test_activity_returns_none_when_state_missing(self):
        vacuum = _make_modern_vacuum()
        status: dict[str, Any] = cast(dict, vacuum.appliance_status)
        if "properties" in status and "reported" in status["properties"]:
            del status["properties"]["reported"]["state"]
            vacuum.reported_state = status["properties"]["reported"]
            assert vacuum.activity is None

    @pytest.mark.asyncio
    async def test_async_start_sends_start_global_clean_when_not_paused(self):
        """Modern start sends cleaningCommand=startGlobalClean when not paused."""
        vacuum = _make_modern_vacuum(state="idle")

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_start()

        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "cleaningCommand"
        assert command == {"cleaningCommand": "startGlobalClean"}

    @pytest.mark.asyncio
    async def test_async_start_sends_resume_clean_when_paused(self):
        """Modern start sends cleaningCommand=resumeClean when paused."""
        vacuum = _make_modern_vacuum(state="paused")

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_start()

        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "cleaningCommand"
        assert command == {"cleaningCommand": "resumeClean"}

    @pytest.mark.asyncio
    async def test_async_stop_sends_stop_clean_command(self):
        """Modern stop sends cleaningCommand=stopClean."""
        vacuum = _make_modern_vacuum()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_stop()

        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "cleaningCommand"
        assert command == {"cleaningCommand": "stopClean"}

    @pytest.mark.asyncio
    async def test_async_pause_sends_pause_clean_command(self):
        """Modern pause sends cleaningCommand=pauseClean."""
        vacuum = _make_modern_vacuum()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_pause()

        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "cleaningCommand"
        assert command == {"cleaningCommand": "pauseClean"}

    @pytest.mark.asyncio
    async def test_async_return_to_base_sends_go_to_charger_command(self):
        """Modern return to base sends cleaningCommand=startGoToCharger."""
        vacuum = _make_modern_vacuum()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_return_to_base()

        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "cleaningCommand"
        assert command == {"cleaningCommand": "startGoToCharger"}

    @pytest.mark.asyncio
    async def test_async_set_fan_speed_sends_vacuum_mode_string(self):
        """Modern set fan speed sends vacuumMode as string."""
        vacuum = _make_modern_vacuum()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ) as mock_execute:
            await vacuum.async_set_fan_speed("max")

        call = mock_execute.await_args
        assert call is not None
        _, _, command, attr, _, _ = call.args
        assert attr == "vacuumMode"
        assert command == {"vacuumMode": "max"}

    def test_fan_speed_returns_current_vacuum_mode(self):
        """fan_speed property returns current vacuumMode."""
        vacuum = _make_modern_vacuum()
        assert vacuum.fan_speed == "energySaving"

    def test_battery_level_returns_direct_percentage(self):
        """Modern battery (0-100 range) returns value directly."""
        vacuum = _make_modern_vacuum(battery_status=75)
        assert vacuum.battery_level == 75

    def test_entity_domain_returns_vacuum(self):
        """Entity domain is VACUUM."""
        vacuum = _make_modern_vacuum()
        assert vacuum.entity_domain == "vacuum"


class TestElectroluxVacuumAsyncSetupEntry:
    """Test async_setup_entry platform setup."""

    @pytest.fixture(autouse=True)
    def mock_platform(self):
        with patch(
            "custom_components.electrolux.vacuum.async_get_current_platform"
        ) as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_entities_for_rvc_types(self):
        """async_setup_entry creates vacuum entities for RVC appliance types."""
        from custom_components.electrolux.vacuum import async_setup_entry

        hass = MagicMock()
        entry = MagicMock()
        async_add_entities = MagicMock()

        # Setup coordinator with RVC appliance
        coordinator = MagicMock()
        coordinator.data = {}
        appliance = MagicMock()
        appliance.appliance_type = "Gordias"
        appliance.name = "My Robot"
        appliance.pnc_id = "RVC_PNC_123"
        appliances = MagicMock()
        appliances.appliances = {"app1": appliance}
        coordinator.data["appliances"] = appliances
        entry.runtime_data = coordinator

        with patch(
            "custom_components.electrolux.vacuum.ElectroluxVacuum"
        ) as mock_vacuum_class:
            await async_setup_entry(hass, entry, async_add_entities)

        mock_vacuum_class.assert_called_once()
        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1

    @pytest.mark.asyncio
    async def test_async_setup_entry_skips_non_rvc_appliances(self):
        """async_setup_entry skips appliances that are not RVC types."""
        from custom_components.electrolux.vacuum import async_setup_entry

        hass = MagicMock()
        entry = MagicMock()
        async_add_entities = MagicMock()

        # Setup coordinator with non-RVC appliance
        coordinator = MagicMock()
        coordinator.data = {}
        appliance = MagicMock()
        appliance.appliance_type = "WM"  # Washing machine, not RVC
        appliances = MagicMock()
        appliances.appliances = {"app1": appliance}
        coordinator.data["appliances"] = appliances
        entry.runtime_data = coordinator

        await async_setup_entry(hass, entry, async_add_entities)

        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 0

    @pytest.mark.asyncio
    async def test_async_setup_entry_handles_missing_appliances(self):
        """async_setup_entry handles case where appliances is None."""
        from custom_components.electrolux.vacuum import async_setup_entry

        hass = MagicMock()
        entry = MagicMock()
        async_add_entities = MagicMock()

        # Setup coordinator with no appliances
        coordinator = MagicMock()
        coordinator.data = {}
        entry.runtime_data = coordinator

        await async_setup_entry(hass, entry, async_add_entities)

        async_add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_multiple_rvc_entities(self):
        """async_setup_entry creates entities for multiple RVC appliances."""
        from custom_components.electrolux.vacuum import async_setup_entry

        hass = MagicMock()
        entry = MagicMock()
        async_add_entities = MagicMock()

        # Setup coordinator with multiple RVC appliances
        coordinator = MagicMock()
        coordinator.data = {}
        appliance1 = MagicMock()
        appliance1.appliance_type = "Gordias"
        appliance1.name = "Robot 1"
        appliance1.pnc_id = "RVC_PNC_1"
        appliance2 = MagicMock()
        appliance2.appliance_type = "Cybele"
        appliance2.name = "Robot 2"
        appliance2.pnc_id = "RVC_PNC_2"
        appliances = MagicMock()
        appliances.appliances = {"app1": appliance1, "app2": appliance2}
        coordinator.data["appliances"] = appliances
        entry.runtime_data = coordinator

        with patch(
            "custom_components.electrolux.vacuum.ElectroluxVacuum"
        ) as mock_vacuum_class:
            await async_setup_entry(hass, entry, async_add_entities)

        assert mock_vacuum_class.call_count == 2
        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 2


class TestElectroluxVacuumEdgeCases:
    """Test edge cases and error handling."""

    def test_battery_status_range_handles_exception_in_appliance_access(self):
        """_battery_status_range returns default range when appliance access fails."""
        vacuum = _make_purei9_vacuum()

        # Mock the coordinator data to raise an exception when accessing appliance
        with patch.object(
            vacuum.coordinator, "data", side_effect=RuntimeError("Access error")
        ):
            # Should return the default PUREi9 range despite the exception
            result = vacuum._battery_status_range()
            assert result == (1, 6)

    def test_battery_status_range_handles_missing_capabilities(self):
        """_battery_status_range handles missing battery capability gracefully."""
        vacuum = _make_purei9_vacuum()

        # Mock coordinator to have appliance without batteryStatus capability
        vacuum.coordinator.data["appliances"].appliances[
            "RVC_PNC"
        ].data.capabilities = {"other": {}}

        result = vacuum._battery_status_range()
        # Should return default PUREi9 range
        assert result == (1, 6)

    def test_battery_status_range_handles_invalid_battery_capability(self):
        """_battery_status_range handles non-dict battery capability."""
        vacuum = _make_purei9_vacuum()

        # Mock get_appliance with invalid batteryStatus capability (not a dict)
        vacuum.coordinator.data["appliances"].appliances[
            "RVC_PNC"
        ].data.capabilities = {"batteryStatus": "invalid"}

        result = vacuum._battery_status_range()
        # Should return default PUREi9 range
        assert result == (1, 6)

    @pytest.mark.asyncio
    async def test_send_command_applies_optimistic_update_on_success(self):
        """_send_command applies optimistic update after successful command."""
        vacuum = _make_purei9_vacuum()
        vacuum._apply_optimistic_update = MagicMock()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(),
        ):
            await vacuum._send_command("powerMode", 3)

        vacuum._apply_optimistic_update.assert_called_once_with("powerMode", 3)

    @pytest.mark.asyncio
    async def test_send_command_raises_exception_on_command_failure(self):
        """_send_command re-raises exception when command fails."""
        vacuum = _make_purei9_vacuum()

        with patch(
            "custom_components.electrolux.vacuum.execute_command_with_error_handling",
            new=AsyncMock(side_effect=RuntimeError("Command failed")),
        ):
            with pytest.raises(RuntimeError, match="Command failed"):
                await vacuum._send_command("powerMode", 3)

    def test_battery_level_handles_float_conversion_error(self):
        """battery_level handles ValueError when converting to float."""
        vacuum = _make_purei9_vacuum()
        status: dict[str, Any] = cast(dict, vacuum.appliance_status)
        if "properties" in status and "reported" in status["properties"]:
            status["properties"]["reported"]["batteryStatus"] = "not_a_number"
            vacuum.reported_state = status["properties"]["reported"]

        assert vacuum.battery_level is None

    def test_battery_level_clamps_to_valid_range(self):
        """battery_level clamps battery value to min/max range."""
        vacuum = _make_purei9_vacuum(battery_min=2, battery_max=8, battery_status=1)
        # Battery 1 is below min of 2, should be clamped
        # Expected: (2 - 2) / (8 - 2) * 100 = 0
        assert vacuum.battery_level == 0

    def test_battery_level_high_value_clamp(self):
        """battery_level clamps high battery values."""
        vacuum = _make_purei9_vacuum(battery_min=2, battery_max=8, battery_status=10)
        # Battery 10 is above max of 8, should be clamped to max
        # Expected: (8 - 2) / (8 - 2) * 100 = 100
        assert vacuum.battery_level == 100

    def test_activity_handles_non_integer_robot_status(self):
        """activity handles when robotStatus cannot be converted to int."""
        vacuum = _make_purei9_vacuum()
        status: dict[str, Any] = cast(dict, vacuum.appliance_status)
        if "properties" in status and "reported" in status["properties"]:
            status["properties"]["reported"]["robotStatus"] = 10.5
            vacuum.reported_state = status["properties"]["reported"]

        # Should handle float and convert to int
        assert vacuum.activity == VacuumActivity.DOCKED

    def test_fan_speed_returns_none_when_attribute_missing(self):
        """fan_speed returns None when powerMode/vacuumMode is missing."""
        vacuum = _make_purei9_vacuum()
        status: dict[str, Any] = cast(dict, vacuum.appliance_status)
        if "properties" in status and "reported" in status["properties"]:
            del status["properties"]["reported"]["powerMode"]
            vacuum.reported_state = status["properties"]["reported"]

        assert vacuum.fan_speed is None
