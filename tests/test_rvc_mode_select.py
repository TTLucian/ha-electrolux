"""Tests for the PUREi9 cleaning mode select ("Läge" in the Electrolux app)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.const import SELECT
from custom_components.electrolux.select import ElectroluxRvcModeSelect


def _make_select(reported: dict[str, Any]) -> ElectroluxRvcModeSelect:
    coordinator = MagicMock()
    coordinator.hass = MagicMock()
    coordinator.config_entry = MagicMock()
    entity = ElectroluxRvcModeSelect(
        coordinator=coordinator,
        name="Robot",
        config_entry=coordinator.config_entry,
        pnc_id="RVC_PNC",
        entity_type=SELECT,
        entity_name="rvcMode",
        entity_attr="rvcMode",
        entity_source=None,
        capability={},
        unit=None,
        device_class=None,
        entity_category=None,
        icon="mdi:fan",
    )
    entity.hass = coordinator.hass
    entity.appliance_status = {"properties": {"reported": reported}}
    entity.reported_state = reported
    return entity


GEN2 = {"powerMode": 2, "robotStatus": 10}
GEN1 = {"ecoMode": True, "robotStatus": 10}


class TestRvcModeSelect:
    def test_translation_key_and_domain(self):
        entity = _make_select(dict(GEN2))
        assert entity.translation_key == "rvcmode"
        assert entity.entity_domain == SELECT

    def test_gen2_options_and_current(self):
        entity = _make_select(dict(GEN2))
        assert entity.options == ["quiet", "smart", "power"]
        assert entity.current_option == "smart"

    @pytest.mark.parametrize(("power_mode", "expected"), [(1, "quiet"), ("3", "power"), (7, None), ("x", None)])
    def test_gen2_current_option(self, power_mode, expected):
        assert _make_select({"powerMode": power_mode}).current_option == expected

    def test_bool_power_mode_is_not_a_level(self):
        assert _make_select({"powerMode": True}).current_option is None

    def test_gen1_options_and_current(self):
        entity = _make_select(dict(GEN1))
        assert entity.options == ["eco", "power"]
        assert entity.current_option == "eco"
        entity.reported_state["ecoMode"] = False
        assert entity.current_option == "power"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("option", "level"), [("quiet", 1), ("smart", 2), ("power", 3)])
    async def test_gen2_select_sends_power_mode(self, option, level):
        entity = _make_select(dict(GEN2))
        with patch(
            "custom_components.electrolux.select.execute_command_with_error_handling", new=AsyncMock()
        ) as mock_execute:
            await entity.async_select_option(option)
        call = mock_execute.await_args
        assert call is not None
        assert call.args[2] == {"powerMode": level}
        assert entity.reported_state["powerMode"] == level

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("option", "level", "eco"), [("eco", 1, True), ("power", 3, False)])
    async def test_gen1_select_sends_power_mode_and_updates_eco(self, option, level, eco):
        entity = _make_select({"ecoMode": not eco})
        with patch(
            "custom_components.electrolux.select.execute_command_with_error_handling", new=AsyncMock()
        ) as mock_execute:
            await entity.async_select_option(option)
        call = mock_execute.await_args
        assert call is not None
        assert call.args[2] == {"powerMode": level}
        assert entity.reported_state["ecoMode"] is eco
        assert "powerMode" not in entity.reported_state

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("reported", "option"), [(GEN1, "smart"), (GEN2, "eco"), (GEN2, "turbo")])
    async def test_unsupported_option_raises(self, reported, option):
        entity = _make_select(dict(reported))
        with (
            patch(
                "custom_components.electrolux.select.execute_command_with_error_handling", new=AsyncMock()
            ) as mock_execute,
            pytest.raises(HomeAssistantError),
        ):
            await entity.async_select_option(option)
        mock_execute.assert_not_awaited()


def _setup_coordinator(appliance_type: str, entities: list[Any]) -> MagicMock:
    appliance = MagicMock()
    appliance.appliance_type = appliance_type
    appliance.pnc_id = "RVC_PNC"
    appliance.name = "Robot"
    appliance.entities = entities
    coordinator = MagicMock()
    coordinator.data = {"appliances": MagicMock()}
    coordinator.data["appliances"].appliances = {"RVC_PNC": appliance}
    return coordinator


class TestRvcModeSetup:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("appliance_type", "expected"), [("PUREi9", 1), ("Gordias", 0)])
    async def test_select_setup_adds_mode_for_purei9_only(self, appliance_type, expected):
        from custom_components.electrolux.select import async_setup_entry

        entry = MagicMock()
        entry.runtime_data = _setup_coordinator(appliance_type, [])
        add_entities = MagicMock()
        await async_setup_entry(MagicMock(), entry, add_entities)
        added = add_entities.call_args.args[0]
        assert sum(isinstance(e, ElectroluxRvcModeSelect) for e in added) == expected

    @pytest.mark.asyncio
    async def test_number_setup_drops_purei9_power_mode(self):
        from custom_components.electrolux.number import async_setup_entry

        power_mode = MagicMock(entity_type=Platform.NUMBER, entity_attr="powerMode")
        other = MagicMock(entity_type=Platform.NUMBER, entity_attr="targetTemperatureC")
        for appliance_type, expected in (("PUREi9", [other]), ("700series", [power_mode, other])):
            entry = MagicMock()
            entry.runtime_data = _setup_coordinator(appliance_type, [power_mode, other])
            add_entities = MagicMock()
            await async_setup_entry(MagicMock(), entry, add_entities)
            assert add_entities.call_args.args[0] == expected
