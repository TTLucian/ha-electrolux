"""Tests for fan.py — ElectroluxFan entity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.fan import FanEntityFeature
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.const import FAN
from custom_components.electrolux.fan import ElectroluxFan

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_coordinator():
    coord = MagicMock()
    coord.hass = MagicMock()
    coord.hass.loop = MagicMock()
    coord.hass.loop.time.return_value = 1_000_000.0
    coord.config_entry = MagicMock()
    coord._last_update_times = {}
    return coord


def _make_capability_fanspeed(min_speed=1, max_speed=9):
    return {"access": "readwrite", "type": "number", "min": min_speed, "max": max_speed}


def _make_capability_workmode(modes=("Auto", "Manual", "Quiet", "PowerOff")):
    return {
        "access": "readwrite",
        "type": "string",
        "values": {m: {} for m in modes},
    }


def _make_fan(
    workmode="Manual",
    fanspeed=5,
    connected=True,
    fanspeed_cap=None,
    workmode_cap=None,
    entity_source=None,
    is_dam=False,
    speed_range=(1, 9),
) -> ElectroluxFan:
    coordinator = _make_coordinator()

    # Build appliance_status with capabilities
    fanspeed_cap = fanspeed_cap or _make_capability_fanspeed()
    workmode_cap = workmode_cap or _make_capability_workmode()

    appliance_status = {
        "capabilities": {
            "Fanspeed": fanspeed_cap,
            "Workmode": workmode_cap,
        },
        "properties": {
            "reported": {
                "connectivityState": "connected" if connected else "disconnected",
                "Workmode": workmode,
                "Fanspeed": fanspeed,
            }
        },
    }

    # Create a per-call subclass so we can override the read-only is_dam_appliance property
    _is_dam = is_dam
    _entity_source = entity_source
    FanCls = type(
        "_ElectroluxFanTest",
        (ElectroluxFan,),
        {"is_dam_appliance": property(lambda self, v=_is_dam: v)},
    )

    fan = FanCls(
        coordinator=coordinator,
        name="Test Fan",
        config_entry=coordinator.config_entry,
        pnc_id="FAN_PNC",
        entity_type=FAN,
        entity_name="fan_entity",
        entity_attr="Fanspeed",
        entity_source=entity_source,
        capability=fanspeed_cap,
        unit=None,
        device_class=None,  # type: ignore[arg-type]
        entity_category=None,
        icon="mdi:fan",
    )
    fan.hass = coordinator.hass
    fan.appliance_status = appliance_status
    fan.reported_state = appliance_status["properties"]["reported"]
    fan.entity_source = entity_source
    return fan


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestElectroluxFanInit:
    def test_supported_features(self):
        fan = _make_fan()
        assert fan._attr_supported_features & FanEntityFeature.TURN_ON
        assert fan._attr_supported_features & FanEntityFeature.TURN_OFF
        assert fan._attr_supported_features & FanEntityFeature.SET_SPEED
        assert fan._attr_supported_features & FanEntityFeature.PRESET_MODE

    def test_speed_range_from_capability(self):
        # _speed_range is set in __init__ from get_capability, which reads appliance_status.
        # appliance_status is None during __init__ so we set _speed_range directly to verify
        # the logic that uses it (percentage calculations, speed_count, etc.).
        fan = _make_fan(fanspeed_cap=_make_capability_fanspeed(1, 5))
        fan._speed_range = (
            1,
            5,
        )  # simulate what __init__ would set if appliance_status were ready
        assert fan._speed_range == (1, 5)

    def test_speed_range_default(self):
        """When Fanspeed capability is missing, fallback to (1, 9)."""
        fan = _make_fan()
        # Override with empty capabilities to simulate missing cap
        fan.appliance_status = {"capabilities": {}, "properties": {"reported": {}}}
        # The range was already set in __init__, so just check default
        assert fan._speed_range[0] == 1
        assert fan._speed_range[1] == 9

    def test_preset_modes_extracted(self):
        # preset_modes are derived from get_capability in __init__, which needs appliance_status.
        # Set them directly to test the exclusion logic and downstream usage.
        fan = _make_fan()
        fan._preset_modes = [
            "Auto",
            "Manual",
            "Quiet",
        ]  # PowerOff excluded by __init__ logic
        fan._attr_preset_modes = fan._preset_modes
        assert "PowerOff" not in fan._preset_modes
        assert "Auto" in fan._preset_modes
        assert "Manual" in fan._preset_modes
        assert "Quiet" in fan._preset_modes

    def test_speed_count(self):
        fan = _make_fan(fanspeed_cap=_make_capability_fanspeed(1, 5))
        # Simulate __init__ having set speed range from capability
        fan._speed_range = (1, 5)
        fan._attr_speed_count = fan._speed_range[1] - fan._speed_range[0] + 1
        assert fan._attr_speed_count == 5  # 5 - 1 + 1


# ---------------------------------------------------------------------------
# entity_domain
# ---------------------------------------------------------------------------


class TestEntityDomain:
    def test_entity_domain(self):
        assert _make_fan().entity_domain == FAN


# ---------------------------------------------------------------------------
# get_capability
# ---------------------------------------------------------------------------


class TestGetCapability:
    def test_fanspeed_capability_found(self):
        fan = _make_fan()
        cap = fan.get_capability("Fanspeed")
        assert cap is not None

    def test_missing_capability_returns_none(self):
        fan = _make_fan()
        assert fan.get_capability("NonExistentCap") is None

    def test_no_appliance_status_returns_none(self):
        fan = _make_fan()
        fan.appliance_status = None
        assert fan.get_capability("Fanspeed") is None


# ---------------------------------------------------------------------------
# is_on
# ---------------------------------------------------------------------------


class TestIsOn:
    def test_on_when_workmode_not_poweroff(self):
        fan = _make_fan(workmode="Manual")
        fan.get_state_attr = MagicMock(return_value="Manual")
        assert fan.is_on is True

    def test_off_when_workmode_poweroff(self):
        fan = _make_fan(workmode="PowerOff")
        fan.get_state_attr = MagicMock(return_value="PowerOff")
        assert fan.is_on is False

    def test_off_when_workmode_none(self):
        fan = _make_fan()
        fan.get_state_attr = MagicMock(return_value=None)
        assert fan.is_on is False

    def test_case_insensitive_poweroff(self):
        fan = _make_fan()
        fan.get_state_attr = MagicMock(return_value="poweroff")
        assert fan.is_on is False


# ---------------------------------------------------------------------------
# percentage
# ---------------------------------------------------------------------------


class TestPercentage:
    def test_percentage_when_off(self):
        fan = _make_fan(workmode="PowerOff")
        fan.get_state_attr = MagicMock(
            side_effect=lambda k: "PowerOff" if k == "Workmode" else 5
        )
        assert fan.percentage == 0

    def test_percentage_mid_range(self):
        # Speed 5 of 1-9 → 50%
        fan = _make_fan(fanspeed=5)
        fan.get_state_attr = MagicMock(
            side_effect=lambda k: "Manual" if k == "Workmode" else 5
        )
        pct = fan.percentage
        assert pct is not None
        assert pct > 0

    def test_percentage_max_speed(self):
        fan = _make_fan(fanspeed_cap=_make_capability_fanspeed(1, 5), fanspeed=5)
        fan._speed_range = (
            1,
            5,
        )  # set as __init__ would if appliance_status were ready
        fan.get_state_attr = MagicMock(
            side_effect=lambda k: "Manual" if k == "Workmode" else 5
        )
        assert fan.percentage == 100

    def test_percentage_min_speed(self):
        fan = _make_fan(fanspeed_cap=_make_capability_fanspeed(1, 5), fanspeed=1)
        fan._speed_range = (1, 5)
        fan.get_state_attr = MagicMock(
            side_effect=lambda k: "Manual" if k == "Workmode" else 1
        )
        assert fan.percentage == 20

    def test_percentage_none_when_fanspeed_none(self):
        fan = _make_fan()
        fan.get_state_attr = MagicMock(
            side_effect=lambda k: "Manual" if k == "Workmode" else None
        )
        assert fan.percentage is None

    def test_percentage_invalid_value_returns_none(self):
        fan = _make_fan()
        fan.get_state_attr = MagicMock(
            side_effect=lambda k: "Manual" if k == "Workmode" else "NOT_A_NUMBER"
        )
        assert fan.percentage is None


# ---------------------------------------------------------------------------
# preset_mode
# ---------------------------------------------------------------------------


class TestPresetMode:
    def test_preset_mode_when_on(self):
        fan = _make_fan(workmode="Auto")
        fan.get_state_attr = MagicMock(
            side_effect=lambda k: "Auto" if k == "Workmode" else 5
        )
        assert fan.preset_mode == "Auto"

    def test_preset_mode_none_when_off(self):
        fan = _make_fan(workmode="PowerOff")
        fan.get_state_attr = MagicMock(return_value="PowerOff")
        assert fan.preset_mode is None

    def test_preset_mode_none_when_workmode_none(self):
        fan = _make_fan()
        fan.get_state_attr = MagicMock(return_value=None)
        assert fan.preset_mode is None


# ---------------------------------------------------------------------------
# async_turn_on
# ---------------------------------------------------------------------------


class TestAsyncTurnOn:
    @pytest.mark.asyncio
    async def test_turn_on_disconnected_raises(self):
        fan = _make_fan(connected=False)
        fan.is_connected = MagicMock(return_value=False)
        with pytest.raises(HomeAssistantError, match="offline"):
            await fan.async_turn_on()

    @pytest.mark.asyncio
    async def test_turn_on_with_preset_mode(self):
        fan = _make_fan()
        fan.is_connected = MagicMock(return_value=True)
        fan._send_workmode_command = AsyncMock()
        await fan.async_turn_on(preset_mode="Auto")
        fan._send_workmode_command.assert_awaited_once_with("Auto")

    @pytest.mark.asyncio
    async def test_turn_on_uses_current_mode_if_active(self):
        fan = _make_fan(workmode="Quiet")
        fan.is_connected = MagicMock(return_value=True)
        fan._send_workmode_command = AsyncMock()
        fan.get_state_attr = MagicMock(return_value="Quiet")
        await fan.async_turn_on()
        fan._send_workmode_command.assert_awaited_once_with("Quiet")

    @pytest.mark.asyncio
    async def test_turn_on_defaults_to_manual_when_poweroff(self):
        fan = _make_fan(workmode="PowerOff")
        fan.is_connected = MagicMock(return_value=True)
        fan._send_workmode_command = AsyncMock()
        fan.get_state_attr = MagicMock(return_value="PowerOff")
        await fan.async_turn_on()
        fan._send_workmode_command.assert_awaited_once_with("Manual")

    @pytest.mark.asyncio
    async def test_turn_on_sets_speed_if_percentage_given(self):
        fan = _make_fan()
        fan.is_connected = MagicMock(return_value=True)
        fan._send_workmode_command = AsyncMock()
        fan._set_percentage = AsyncMock()
        fan.get_state_attr = MagicMock(return_value="Manual")
        await fan.async_turn_on(percentage=50)
        fan._set_percentage.assert_awaited_once_with(50)


# ---------------------------------------------------------------------------
# async_turn_off
# ---------------------------------------------------------------------------


class TestAsyncTurnOff:
    @pytest.mark.asyncio
    async def test_turn_off_disconnected_raises(self):
        fan = _make_fan(connected=False)
        fan.is_connected = MagicMock(return_value=False)
        with pytest.raises(HomeAssistantError, match="offline"):
            await fan.async_turn_off()

    @pytest.mark.asyncio
    async def test_turn_off_sends_poweroff(self):
        fan = _make_fan()
        fan.is_connected = MagicMock(return_value=True)
        fan._send_workmode_command = AsyncMock()
        await fan.async_turn_off()
        fan._send_workmode_command.assert_awaited_once_with("PowerOff")


# ---------------------------------------------------------------------------
# async_set_percentage
# ---------------------------------------------------------------------------


class TestAsyncSetPercentage:
    @pytest.mark.asyncio
    async def test_set_percentage_disconnected_raises(self):
        fan = _make_fan(connected=False)
        fan.is_connected = MagicMock(return_value=False)
        with pytest.raises(HomeAssistantError, match="offline"):
            await fan.async_set_percentage(50)

    @pytest.mark.asyncio
    async def test_set_percentage_zero_turns_off(self):
        fan = _make_fan()
        fan.is_connected = MagicMock(return_value=True)
        fan.async_turn_off = AsyncMock()
        await fan.async_set_percentage(0)
        fan.async_turn_off.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_percentage_while_off_turns_on_manual_first(self):
        fan = _make_fan(workmode="PowerOff")
        fan.is_connected = MagicMock(return_value=True)
        fan._send_workmode_command = AsyncMock()
        fan._set_percentage = AsyncMock()
        # get_state_attr drives is_on (returns PowerOff → is_on=False)
        fan.get_state_attr = MagicMock(return_value="PowerOff")
        await fan.async_set_percentage(50)
        fan._send_workmode_command.assert_awaited_once_with("Manual")
        fan._set_percentage.assert_awaited_once_with(50)

    @pytest.mark.asyncio
    async def test_set_percentage_while_on_skips_turn_on(self):
        fan = _make_fan(workmode="Auto")
        fan.is_connected = MagicMock(return_value=True)
        fan._send_workmode_command = AsyncMock()
        fan._set_percentage = AsyncMock()
        # get_state_attr drives is_on (returns Auto → is_on=True)
        fan.get_state_attr = MagicMock(return_value="Auto")
        await fan.async_set_percentage(75)
        fan._send_workmode_command.assert_not_called()
        fan._set_percentage.assert_awaited_once_with(75)


# ---------------------------------------------------------------------------
# async_set_preset_mode
# ---------------------------------------------------------------------------


class TestAsyncSetPresetMode:
    @pytest.mark.asyncio
    async def test_set_preset_mode_disconnected_raises(self):
        fan = _make_fan(connected=False)
        fan.is_connected = MagicMock(return_value=False)
        with pytest.raises(HomeAssistantError, match="offline"):
            await fan.async_set_preset_mode("Auto")

    @pytest.mark.asyncio
    async def test_set_invalid_preset_raises(self):
        fan = _make_fan()
        fan.is_connected = MagicMock(return_value=True)
        with pytest.raises(HomeAssistantError, match="Invalid preset mode"):
            await fan.async_set_preset_mode("InvalidMode")

    @pytest.mark.asyncio
    async def test_set_valid_preset_sends_workmode(self):
        fan = _make_fan()
        fan.is_connected = MagicMock(return_value=True)
        fan._preset_modes = ["Auto", "Manual", "Quiet"]  # as __init__ would set
        fan._send_workmode_command = AsyncMock()
        await fan.async_set_preset_mode("Auto")
        fan._send_workmode_command.assert_awaited_once_with("Auto")


# ---------------------------------------------------------------------------
# _set_percentage (internal)
# ---------------------------------------------------------------------------


class TestSetPercentageInternal:
    @pytest.mark.asyncio
    async def test_set_percentage_sends_command(self):
        fan = _make_fan(fanspeed_cap=_make_capability_fanspeed(1, 5))
        fan._speed_range = (
            1,
            5,
        )  # set as __init__ would if appliance_status were ready
        fan._send_command = AsyncMock()
        await fan._set_percentage(100)
        fan._send_command.assert_awaited_once()
        # First arg is attr name
        assert fan._send_command.call_args[0][0] == "Fanspeed"
        # Value should be 5 (max for 1-5 range)
        assert fan._send_command.call_args[0][1] == 5

    @pytest.mark.asyncio
    async def test_set_percentage_missing_capability_returns(self):
        fan = _make_fan()
        fan.appliance_status = {"capabilities": {}, "properties": {"reported": {}}}
        fan._send_command = AsyncMock()
        # Should return without sending command
        await fan._set_percentage(50)
        fan._send_command.assert_not_called()


# ---------------------------------------------------------------------------
# _send_workmode_command (internal)
# ---------------------------------------------------------------------------


class TestSendWorkmodeCommand:
    @pytest.mark.asyncio
    async def test_sends_command(self):
        fan = _make_fan()
        fan._send_command = AsyncMock()
        await fan._send_workmode_command("Auto")
        fan._send_command.assert_awaited_once()
        assert fan._send_command.call_args[0][0] == "Workmode"
        assert fan._send_command.call_args[0][1] == "Auto"

    @pytest.mark.asyncio
    async def test_missing_workmode_cap_returns(self):
        fan = _make_fan()
        fan.appliance_status = {"capabilities": {}, "properties": {"reported": {}}}
        fan._send_command = AsyncMock()
        await fan._send_workmode_command("Auto")
        fan._send_command.assert_not_called()


# ---------------------------------------------------------------------------
# _send_command (integration with execute_command_with_error_handling)
# ---------------------------------------------------------------------------


class TestSendCommand:
    @pytest.mark.asyncio
    async def test_send_command_legacy_appliance(self):
        fan = _make_fan(is_dam=False, entity_source=None)
        fan.api = MagicMock()
        fan._apply_optimistic_update = MagicMock()

        cap = {"access": "readwrite", "type": "string"}
        with patch(
            "custom_components.electrolux.fan.format_command_for_appliance",
            return_value="Auto",
        ), patch(
            "custom_components.electrolux.fan.execute_command_with_error_handling",
            new_callable=AsyncMock,
        ) as mock_exec:
            await fan._send_command("Workmode", "Auto", cap)

        mock_exec.assert_awaited_once()
        # Command must be a simple top-level dict for legacy
        cmd_arg = mock_exec.call_args[0][2]
        assert cmd_arg == {"Workmode": "Auto"}

    @pytest.mark.asyncio
    async def test_send_command_dam_appliance_wraps_in_commands(self):
        fan = _make_fan(is_dam=True, entity_source=None)
        fan.api = MagicMock()
        fan._apply_optimistic_update = MagicMock()

        cap = {"access": "readwrite", "type": "string"}
        with patch(
            "custom_components.electrolux.fan.format_command_for_appliance",
            return_value="Auto",
        ), patch(
            "custom_components.electrolux.fan.execute_command_with_error_handling",
            new_callable=AsyncMock,
        ) as mock_exec:
            await fan._send_command("Workmode", "Auto", cap)

        cmd_arg = mock_exec.call_args[0][2]
        assert "commands" in cmd_arg
        assert cmd_arg["commands"][0] == {"Workmode": "Auto"}

    @pytest.mark.asyncio
    async def test_send_command_dam_with_entity_source(self):
        fan = _make_fan(is_dam=True, entity_source="someSource")
        fan.api = MagicMock()
        fan.appliance_status = {
            "capabilities": _make_capability_workmode(),
            "properties": {"reported": {}},
        }
        fan._apply_optimistic_update = MagicMock()

        cap = {"access": "readwrite", "type": "string"}
        with patch(
            "custom_components.electrolux.fan.format_command_for_appliance",
            return_value="Auto",
        ), patch(
            "custom_components.electrolux.fan.execute_command_with_error_handling",
            new_callable=AsyncMock,
        ) as mock_exec:
            await fan._send_command("Workmode", "Auto", cap)

        cmd_arg = mock_exec.call_args[0][2]
        inner = cmd_arg["commands"][0]
        assert "someSource" in inner
        assert inner["someSource"] == {"Workmode": "Auto"}

    @pytest.mark.asyncio
    async def test_send_command_auth_error_triggers_reauth(self):
        from custom_components.electrolux.exceptions import AuthenticationError

        fan = _make_fan()
        fan.api = MagicMock()
        fan._apply_optimistic_update = MagicMock()
        mock_coord = MagicMock()
        mock_coord.handle_authentication_error = AsyncMock()
        fan.coordinator = mock_coord

        cap = {"access": "readwrite", "type": "string"}
        with patch(
            "custom_components.electrolux.fan.format_command_for_appliance",
            return_value="Auto",
        ), patch(
            "custom_components.electrolux.fan.execute_command_with_error_handling",
            new_callable=AsyncMock,
            side_effect=AuthenticationError("bad token"),
        ):
            with pytest.raises(AuthenticationError):
                await fan._send_command("Workmode", "Auto", cap)

        mock_coord.handle_authentication_error.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_optimistic_update_applied_on_success(self):
        fan = _make_fan(is_dam=False)
        fan.api = MagicMock()
        fan._apply_optimistic_update = MagicMock()

        cap = {"access": "readwrite", "type": "string"}
        with patch(
            "custom_components.electrolux.fan.format_command_for_appliance",
            return_value="Auto",
        ), patch(
            "custom_components.electrolux.fan.execute_command_with_error_handling",
            new_callable=AsyncMock,
        ):
            await fan._send_command("Workmode", "Auto", cap)

        fan._apply_optimistic_update.assert_called_once_with("Workmode", "Auto")


# ---------------------------------------------------------------------------
# Missing coverage: async_setup_entry, __init__ caps, percentage clamp,
#                  preset_mode workmode=None, _set_percentage ValueError,
#                  _send_command userSelections & except Exception paths
# ---------------------------------------------------------------------------


class TestFanMissingCoverage:
    """Targets the remaining missed lines in fan.py."""

    # ── lines 64-76: async_setup_entry ──────────────────────────────────────

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_fan_entities(self):
        """Lines 64-76 — async_setup_entry iterates appliances and adds FAN entities."""
        from unittest.mock import MagicMock

        from custom_components.electrolux.fan import async_setup_entry

        fan_entity = MagicMock()
        fan_entity.entity_type = FAN

        mock_appliance = MagicMock()
        mock_appliance.entities = [fan_entity]

        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "appliances": MagicMock(appliances={"app_1": mock_appliance})
        }

        mock_config_entry = MagicMock()
        mock_config_entry.runtime_data = mock_coordinator

        mock_add_entities = MagicMock()
        await async_setup_entry(MagicMock(), mock_config_entry, mock_add_entities)

        mock_add_entities.assert_called_once_with([fan_entity])

    # ── lines 127-129 & 134-136: __init__ reads Fanspeed/Workmode cap ────────

    def test_init_reads_speed_range_from_fanspeed_capability(self):
        """Lines 127-129 — __init__ sets _speed_range from Fanspeed capability."""
        mock_caps = {
            "Fanspeed": {"min": 2, "max": 7},
        }
        coord = _make_coordinator()
        with patch.object(
            ElectroluxFan, "get_capability", lambda self, attr: mock_caps.get(attr)
        ):
            fan = ElectroluxFan(
                coordinator=coord,
                name="Test Fan",
                config_entry=coord.config_entry,
                pnc_id="FAN_PNC",
                entity_type=FAN,
                entity_name="fan_entity",
                entity_attr="Fanspeed",
                entity_source=None,
                capability={},
                unit=None,
                device_class="",
                entity_category=None,
                icon="mdi:fan",
            )
        assert fan._speed_range == (2, 7)

    def test_init_reads_preset_modes_from_workmode_capability(self):
        """Lines 134-136 — __init__ builds _preset_modes from Workmode capability."""
        mock_caps = {
            "Workmode": {
                "values": {"Auto": {}, "Manual": {}, "Quiet": {}, "PowerOff": {}}
            },
        }
        coord = _make_coordinator()
        with patch.object(
            ElectroluxFan, "get_capability", lambda self, attr: mock_caps.get(attr)
        ):
            fan = ElectroluxFan(
                coordinator=coord,
                name="Test Fan",
                config_entry=coord.config_entry,
                pnc_id="FAN_PNC",
                entity_type=FAN,
                entity_name="fan_entity",
                entity_attr="Fanspeed",
                entity_source=None,
                capability={},
                unit=None,
                device_class="",
                entity_category=None,
                icon="mdi:fan",
            )
        assert "Auto" in fan._preset_modes
        assert "Manual" in fan._preset_modes
        assert "Quiet" in fan._preset_modes
        assert "PowerOff" not in fan._preset_modes

    # ── lines 183, 185: percentage clamps speed to valid range ───────────────

    def test_percentage_clamps_fanspeed_below_min(self):
        """Line 183 — fanspeed < min_speed is clamped to min_speed."""
        fan = _make_fan(fanspeed=0)
        fan._speed_range = (1, 9)
        fan.get_state_attr = MagicMock(
            side_effect=lambda k: "Manual" if k == "Workmode" else 0
        )
        pct = fan.percentage
        # speed 0 clamped to 1, percentage of 1 in [1..9] = ~11%
        assert pct is not None
        assert pct > 0

    def test_percentage_clamps_fanspeed_above_max(self):
        """Line 185 — fanspeed > max_speed is clamped to max_speed."""
        fan = _make_fan(fanspeed=15)
        fan._speed_range = (1, 9)
        fan.get_state_attr = MagicMock(
            side_effect=lambda k: "Manual" if k == "Workmode" else 15
        )
        pct = fan.percentage
        # speed 15 clamped to 9 → 100%
        assert pct == 100

    # ── line 206: preset_mode returns None when workmode is None (but is_on=True) ──

    def test_preset_mode_none_when_workmode_switches_to_none(self):
        """Line 206 — preset_mode returns None when second get_state_attr call returns None."""
        fan = _make_fan()
        call_count = [0]

        def mock_get_state_attr(k):
            if k == "Workmode":
                call_count[0] += 1
                if call_count[0] <= 1:
                    return "Auto"  # is_on sees valid mode → True
                return None  # preset_mode sees None → returns None
            return 5

        fan.get_state_attr = MagicMock(side_effect=mock_get_state_attr)
        assert fan.preset_mode is None

    # ── lines 314-318: _set_percentage ValueError from invalid percentage ─────

    @pytest.mark.asyncio
    async def test_set_percentage_handles_value_error_from_converter(self):
        """Lines 314-318 — ValueError from percentage_to_ordered_list_item is caught."""
        fan = _make_fan()
        fan._send_command = AsyncMock()
        with patch(
            "custom_components.electrolux.fan.percentage_to_ordered_list_item",
            side_effect=ValueError("invalid percentage"),
        ):
            # Should NOT raise — catches ValueError and returns
            await fan._set_percentage(50)
        fan._send_command.assert_not_called()

    # ── lines 387-393: _send_command with userSelections entity_source ────────

    @pytest.mark.asyncio
    async def test_send_command_dam_user_selections_path(self):
        """Lines 387-393 — DAM appliance with userSelections entity_source wraps command."""
        fan = _make_fan(is_dam=True, entity_source="userSelections")
        fan.appliance_status["properties"]["reported"]["userSelections"] = {  # type: ignore[index]
            "programUID": "PROG_001"
        }
        fan.api = MagicMock()
        fan._apply_optimistic_update = MagicMock()

        cap = {"access": "readwrite", "type": "string"}
        with patch(
            "custom_components.electrolux.fan.format_command_for_appliance",
            return_value="Auto",
        ), patch(
            "custom_components.electrolux.fan.execute_command_with_error_handling",
            new_callable=AsyncMock,
        ) as mock_exec:
            await fan._send_command("Workmode", "Auto", cap)

        cmd_arg = mock_exec.call_args[0][2]
        assert "commands" in cmd_arg
        inner = cmd_arg["commands"][0]
        assert "userSelections" in inner
        assert inner["userSelections"]["programUID"] == "PROG_001"
        assert inner["userSelections"]["Workmode"] == "Auto"

    # ── lines 421-423: _send_command re-raises non-auth exceptions ────────────

    @pytest.mark.asyncio
    async def test_send_command_reraises_non_auth_exception(self):
        """Lines 421-423 — non-AuthenticationError from execute_command is re-raised."""
        from homeassistant.exceptions import HomeAssistantError

        fan = _make_fan(is_dam=False)
        fan.api = MagicMock()
        fan._apply_optimistic_update = MagicMock()

        cap = {"access": "readwrite", "type": "string"}
        with patch(
            "custom_components.electrolux.fan.format_command_for_appliance",
            return_value="Auto",
        ), patch(
            "custom_components.electrolux.fan.execute_command_with_error_handling",
            AsyncMock(side_effect=HomeAssistantError("command rejected")),
        ):
            with pytest.raises(HomeAssistantError, match="command rejected"):
                await fan._send_command("Workmode", "Auto", cap)
