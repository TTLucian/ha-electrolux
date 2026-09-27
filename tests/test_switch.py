"""Test switch platform for Electrolux."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.const import SWITCH
from custom_components.electrolux.switch import ElectroluxSwitch, async_setup_entry

# Real dishwasher capabilities (verbatim excerpt of samples/DW-911473025_00.json).
# Program constraint dicts key their entries *namespaced* —
# "userSelections/glassCareOption" — which is what the #232 programUID gate has
# to match; see tests/test_program_level_key.py.
DW_CAPS = json.loads((Path(__file__).parent / "fixtures" / "dw_user_selections.json").read_text())["capabilities"]


def _set_appliance_capabilities(coordinator, caps=DW_CAPS) -> None:
    """Attach real capabilities to the coordinator's mocked appliance."""
    coordinator.data["appliances"].get_appliance.return_value.data.capabilities = caps


class TestElectroluxSwitch:
    """Test the Electrolux Switch entity."""

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
    def mock_coordinator_with_program_caps(self):
        """Create a mock coordinator with program-level capability data."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        # Simulate appliance capabilities with a program that lists testAttr
        mock_appliance = MagicMock()
        mock_appliance.data = MagicMock()
        mock_appliance.data.capabilities = {
            "program": {
                "values": {
                    "TEST_PROGRAM": {
                        "testAttr": {"disabled": False},
                    }
                }
            }
        }
        coordinator.data = {"appliances": MagicMock()}
        coordinator.data["appliances"].get_appliance.return_value = mock_appliance
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        """Create a mock capability."""
        return {
            "access": "readwrite",
            "type": "boolean",
            "values": {"OFF": {}, "ON": {}},
        }

    @pytest.fixture
    def switch_entity(self, mock_coordinator, mock_capability):
        """Create a test switch entity."""
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.appliance_status = {"properties": {"reported": {"testAttr": True}}}
        entity.reported_state = {"testAttr": True}
        return entity

    def test_entity_domain(self, switch_entity):
        """Test entity domain property."""
        assert switch_entity.entity_domain == "switch"

    def test_is_on_boolean_true(self, switch_entity):
        """Test is_on returns True for boolean True."""
        switch_entity.appliance_status = {
            "properties": {"reported": {"testAttr": True}}
        }
        switch_entity.reported_state = {"testAttr": True}
        assert switch_entity.is_on is True

    def test_is_on_boolean_false(self, switch_entity):
        """Test is_on returns False for boolean False."""
        switch_entity.appliance_status = {
            "properties": {"reported": {"testAttr": False}}
        }
        switch_entity.reported_state = {"testAttr": False}
        assert switch_entity.is_on is False

    def test_is_on_non_boolean_conversion(self, switch_entity):
        """Test is_on converts non-boolean values."""
        switch_entity.appliance_status = {"properties": {"reported": {"testAttr": 1}}}
        switch_entity.reported_state = {"testAttr": 1}
        assert switch_entity.is_on is True

    def test_is_on_string_on(self, switch_entity):
        """Test is_on returns True for string 'ON'."""
        switch_entity.appliance_status = {
            "properties": {"reported": {"testAttr": "ON"}}
        }
        switch_entity.reported_state = {"testAttr": "ON"}
        assert switch_entity.is_on is True

    def test_is_on_string_off(self, switch_entity):
        """Test is_on returns False for string 'OFF'."""
        switch_entity.appliance_status = {
            "properties": {"reported": {"testAttr": "OFF"}}
        }
        switch_entity.reported_state = {"testAttr": "OFF"}
        assert switch_entity.is_on is False

    def test_is_on_string_lowercase(self, switch_entity):
        """Test is_on handles lowercase string values."""
        switch_entity.appliance_status = {
            "properties": {"reported": {"testAttr": "on"}}
        }
        switch_entity.reported_state = {"testAttr": "on"}
        assert switch_entity.is_on is True

        switch_entity.appliance_status = {
            "properties": {"reported": {"testAttr": "off"}}
        }
        switch_entity.reported_state = {"testAttr": "off"}
        assert switch_entity.is_on is False

    def test_is_on_none_value(self, switch_entity):
        """Test is_on returns None when value is unknown (e.g. appliance offline)."""
        switch_entity.appliance_status = {"properties": {"reported": {}}}
        switch_entity.reported_state = {}
        switch_entity.extract_value = MagicMock(return_value=None)
        assert switch_entity.is_on is None

    def test_is_on_with_state_mapping(self, mock_coordinator, mock_capability):
        """Test is_on with state mapping."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            state_mapping="testAttr",
        )

        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        entity.extract_value = MagicMock(return_value=None)
        entity.get_state_attr = MagicMock(return_value=True)
        assert entity.is_on is True

    def test_is_on_offline_returns_none(self, mock_coordinator, mock_capability):
        """A disconnected appliance reports unknown, never a stale on/off (#231)."""
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.reported_state = {"connectivityState": "disconnected", "testAttr": True}
        assert entity.is_on is None

    def test_is_on_offline_with_state_mapping_returns_none(
        self, mock_coordinator, mock_capability
    ):
        """The state_mapping fallback must not revive a stale value while offline.

        ``get_state_attr`` reads raw reported state and has no offline guard of
        its own, so this is the case that kept reporting ``off``/``on`` for the
        mapped dishwasher switches in #231.
        """
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            state_mapping="applianceState",
        )
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        entity.reported_state = {"connectivityState": "disconnected", "applianceState": "OFF"}
        assert entity.is_on is None
        # HA renders is_on=None as "unknown" (SwitchEntity.state returns None)
        assert entity.state is None

    def test_async_setup_entry_keeps_write_only_switches(self, mock_coordinator):
        """Write-only capabilities should stay available as switches even when absent from reported state."""
        entity = MagicMock()
        entity.entity_type = SWITCH
        entity.json_path = "executeCommand"
        entity.entity_attr = "executeCommand"
        entity.capability = {"access": "write", "type": "string"}

        appliance = MagicMock()
        appliance.entities = [entity]
        appliance.reported_state = {}

        appliances = MagicMock()
        appliances.appliances = {"TEST_PNC": appliance}

        coordinator = MagicMock()
        coordinator.data = {"appliances": appliances}

        entry = MagicMock()
        entry.runtime_data = coordinator

        add_entities = MagicMock()

        import asyncio

        asyncio.run(async_setup_entry(MagicMock(), entry, add_entities))

        add_entities.assert_called_once()
        assert add_entities.call_args[0][0][0] is entity

    def test_async_setup_entry_keeps_nested_user_selection_switches(
        self, mock_coordinator
    ):
        """Nested userSelections switches should not be filtered as phantom capabilities."""
        entity = MagicMock()
        entity.entity_type = SWITCH
        entity.json_path = "userSelections/autoDoorOpener"
        entity.entity_attr = "autoDoorOpener"
        entity.capability = {"access": "readwrite", "type": "boolean"}

        appliance = MagicMock()
        appliance.entities = [entity]
        appliance.reported_state = {"userSelections": {"autoDoorOpener": True}}

        appliances = MagicMock()
        appliances.appliances = {"TEST_PNC": appliance}

        coordinator = MagicMock()
        coordinator.data = {"appliances": appliances}

        entry = MagicMock()
        entry.runtime_data = coordinator

        add_entities = MagicMock()

        import asyncio

        asyncio.run(async_setup_entry(MagicMock(), entry, add_entities))

        add_entities.assert_called_once()
        assert add_entities.call_args[0][0][0] is entity

    @pytest.mark.asyncio
    async def test_async_turn_on(self, switch_entity):
        """Test turning switch on."""
        switch_entity.api = AsyncMock()
        switch_entity.is_remote_control_enabled = MagicMock(return_value=True)
        switch_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        with patch(
            "custom_components.electrolux.switch.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = "ON"
            await switch_entity.async_turn_on()

            mock_format.assert_called_once_with(
                switch_entity.capability, "testAttr", True
            )

    @pytest.mark.asyncio
    async def test_async_turn_off(self, switch_entity):
        """Test turning switch off."""
        switch_entity.api = AsyncMock()
        switch_entity.is_remote_control_enabled = MagicMock(return_value=True)
        switch_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        with patch(
            "custom_components.electrolux.switch.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = "OFF"
            await switch_entity.async_turn_off()

            mock_format.assert_called_once_with(
                switch_entity.capability, "testAttr", False
            )

    @pytest.mark.asyncio
    async def test_async_turn_on_remote_control_disabled(self, switch_entity):
        """Test turning on when remote control is disabled - command is sent optimistically to API."""
        switch_entity.is_remote_control_enabled = MagicMock(return_value=False)

        # With optimistic sending, command should be sent to API (API will validate)
        # Mock the API to simulate successful call (API would reject if truly disabled)
        switch_entity.api.execute_appliance_command = AsyncMock(return_value=None)
        await switch_entity.async_turn_on()

        # Verify command was sent to API (not blocked client-side)
        switch_entity.api.execute_appliance_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_command_with_user_selections_source_program_level_key(
        self, mock_coordinator_with_program_caps
    ):
        """Test switch command with userSelections source includes programUID for program-level keys."""
        mock_coordinator = mock_coordinator_with_program_caps
        mock_capability = {
            "access": "readwrite",
            "type": "boolean",
            "values": {"OFF": {}, "ON": {}},
        }
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source="userSelections",
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock()
        entity.is_remote_control_enabled = MagicMock(return_value=True)
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "ENABLED",
                    "userSelections": {"programUID": "TEST_PROGRAM"},
                }
            }
        }

        with patch(
            "custom_components.electrolux.switch.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = "ON"
            await entity.async_turn_on()

            # Verify command structure for Legacy appliance with userSelections source
            call_args = entity.api.execute_appliance_command.call_args
            pnc_id, command = call_args[0]
            assert pnc_id == "TEST_PNC"
            # Program-level key with programUID should be bundled
            assert command == {
                "userSelections": {"programUID": "TEST_PROGRAM", "testAttr": "ON"}
            }

    @pytest.mark.asyncio
    async def test_switch_command_with_user_selections_source_appliance_level_key(
        self, mock_coordinator
    ):
        """Test switch command with userSelections source omits programUID for appliance-level keys.

        Appliance-level keys (not listed by any program's constraint dict) should
        be sent without programUID to avoid silent rejection (fixes #232).
        """
        # Real dishwasher capabilities: its programs list the options
        # (glassCareOption, sanitizeOption, …) but never autoDoorOpener.
        _set_appliance_capabilities(mock_coordinator)
        mock_capability = {
            "access": "readwrite",
            "type": "boolean",
            "values": {"OFF": {}, "ON": {}},
        }
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="autoDoorOpener",
            entity_source="userSelections",
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock()
        entity.is_remote_control_enabled = MagicMock(return_value=True)
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "ENABLED",
                    "userSelections": {"programUID": "ECO"},
                }
            }
        }

        with patch(
            "custom_components.electrolux.switch.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = "ON"
            await entity.async_turn_on()

            call_args = entity.api.execute_appliance_command.call_args
            pnc_id, command = call_args[0]
            assert pnc_id == "TEST_PNC"
            # Appliance-level key: no programUID bundled, sent as simple payload
            assert command == {
                "userSelections": {"autoDoorOpener": "ON"}
            }

    @pytest.mark.asyncio
    async def test_switch_command_with_user_selections_source_real_program_option(
        self, mock_coordinator
    ):
        """Real dishwasher option keeps programUID — no #30 regression (#232).

        The program constraint dicts of a real dishwasher name their entries
        "userSelections/<option>"; a gate that only matched the bare attribute
        would drop programUID here and the write would be rejected silently.
        """
        _set_appliance_capabilities(mock_coordinator)
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            capability={"access": "readwrite", "type": "boolean"},
            name="Glass Care",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="glassCareOption",
            entity_source="userSelections",
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:glass-wine",
        )
        api = MagicMock()
        api.execute_appliance_command = AsyncMock()
        entity.api = api
        entity.is_remote_control_enabled = MagicMock(return_value=True)  # type: ignore[method-assign]
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "ENABLED",
                    "userSelections": {"programUID": "ECO"},
                }
            }
        }

        with patch(
            "custom_components.electrolux.switch.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = "ON"
            await entity.async_turn_on()

            call_args = api.execute_appliance_command.call_args
            _, command = call_args[0]
            # Program option: bundled with the active programUID
            assert command == {
                "userSelections": {"programUID": "ECO", "glassCareOption": "ON"}
            }

    @pytest.mark.asyncio
    async def test_switch_with_appliance_source(
        self, mock_coordinator, mock_capability
    ):
        """Test switch command with appliance-type entity source."""
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source="oven",
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock()
        entity.is_remote_control_enabled = MagicMock(return_value=True)
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        with patch(
            "custom_components.electrolux.switch.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = "ON"
            await entity.async_turn_on()

            # Verify command structure for Legacy appliance with appliance source
            call_args = entity.api.execute_appliance_command.call_args
            pnc_id, command = call_args[0]
            assert pnc_id == "TEST_PNC"
            # Legacy appliances with entity_source also wrap the command in the source container
            assert command == {"oven": {"testAttr": "ON"}}

    @pytest.mark.asyncio
    async def test_switch_with_root_source(self, switch_entity):
        """Test switch command with root entity source (None)."""
        switch_entity.api = MagicMock()
        switch_entity.api.execute_appliance_command = AsyncMock()
        switch_entity.is_remote_control_enabled = MagicMock(return_value=True)
        switch_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        with patch(
            "custom_components.electrolux.switch.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = "ON"
            await switch_entity.async_turn_on()

            # Verify command structure for root source
            call_args = switch_entity.api.execute_appliance_command.call_args
            pnc_id, command = call_args[0]
            assert pnc_id == "TEST_PNC"
            assert command["testAttr"] == "ON"
            assert len(command) == 1  # Only the attribute, no wrapper

    def test_available_property_remote_control_disabled(self, switch_entity):
        """Test availability when remote control is disabled (but connected)."""
        switch_entity.is_connected = MagicMock(return_value=True)
        switch_entity.is_remote_control_enabled = MagicMock(return_value=False)
        assert (
            switch_entity.available
        )  # Should be available even with remote control disabled

    def test_available_property_remote_control_enabled(self, switch_entity):
        """Test availability when remote control is enabled."""
        switch_entity.is_remote_control_enabled = MagicMock(return_value=True)
        assert switch_entity.available

    @pytest.mark.asyncio
    async def test_switch_when_appliance_offline_raises(self, switch_entity):
        """switch() raises HomeAssistantError when appliance is not connected."""
        switch_entity.is_connected = MagicMock(return_value=False)
        switch_entity.reported_state = {"connectivityState": "disconnected"}

        with pytest.raises(HomeAssistantError, match="offline"):
            await switch_entity.switch(True)

    @pytest.mark.asyncio
    async def test_switch_dam_appliance_with_entity_source(
        self, mock_coordinator, mock_capability
    ):
        """DAM appliance switch wraps command in 'commands' list."""
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="1:TEST_PNC",  # DAM appliance
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source="oven",
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:test",
        )
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=None)
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        with patch(
            "custom_components.electrolux.switch.format_command_for_appliance",
            return_value="ON",
        ):
            await entity.switch(True)

        call_args = entity.api.execute_appliance_command.call_args[0]
        assert "commands" in call_args[1]

    @pytest.mark.asyncio
    async def test_switch_dam_appliance_without_entity_source(
        self, mock_coordinator, mock_capability
    ):
        """DAM appliance switch without entity_source uses plain attr command."""
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="1:TEST_PNC",  # DAM appliance
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source=None,
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:test",
        )
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=None)
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        with patch(
            "custom_components.electrolux.switch.format_command_for_appliance",
            return_value="ON",
        ):
            await entity.switch(True)

        call_args = entity.api.execute_appliance_command.call_args[0]
        assert "commands" in call_args[1]

    @pytest.mark.asyncio
    async def test_switch_authentication_error_triggers_reauth(self, switch_entity):
        """AuthenticationError from API triggers coordinator.handle_authentication_error."""
        from custom_components.electrolux.util import AuthenticationError

        switch_entity.api = MagicMock()
        switch_entity.api.execute_appliance_command = AsyncMock(
            side_effect=AuthenticationError("token expired")
        )
        switch_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        mock_coord = MagicMock()
        mock_coord.handle_authentication_error = AsyncMock()

        with (
            patch(
                "custom_components.electrolux.switch.execute_command_with_error_handling",
                side_effect=AuthenticationError("token expired"),
            ),
            patch(
                "custom_components.electrolux.switch.format_command_for_appliance",
                return_value="ON",
            ),
            patch.object(switch_entity, "coordinator", mock_coord),pytest.raises(AuthenticationError)
        ):
            await switch_entity.switch(True)

        mock_coord.handle_authentication_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_dam_user_selections_wraps_command(
        self, mock_coordinator, mock_capability
    ):
        """DAM appliance with userSelections source wraps with programUID."""
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="1:TEST_PNC",  # DAM appliance
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source="userSelections",
            capability=mock_capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:test",
        )
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=None)
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "ENABLED",
                    "userSelections": {"programUID": "COTTON"},
                }
            }
        }

        with patch(
            "custom_components.electrolux.switch.format_command_for_appliance",
            return_value="ON",
        ):
            await entity.switch(True)

        call_args = entity.api.execute_appliance_command.call_args[0]
        assert "commands" in call_args[1]

    @pytest.mark.asyncio
    async def test_switch_generic_exception_reraised(
        self, mock_coordinator, mock_capability
    ):
        """Generic (non-auth) exceptions from execute_command_with_error_handling are re-raised."""
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=None)

        generic_err = HomeAssistantError("remote control disabled")
        with (
            patch(
                "custom_components.electrolux.switch.execute_command_with_error_handling",
                side_effect=generic_err,
            ),
            patch(
                "custom_components.electrolux.switch.format_command_for_appliance",
                return_value="OFF",
            ),pytest.raises(HomeAssistantError, match="remote control disabled")
        ):
            await entity.switch(True)

    # ... (existing tests in TestElectroluxSwitch class) ...

    @pytest.mark.asyncio
    async def test_switch_schedules_state_refresh_after_command(
        self, mock_coordinator, mock_capability
    ):
        """State refresh is scheduled after a successful switch command."""
        entity = ElectroluxSwitch(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Switch",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SWITCH,
            entity_name="test_switch",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=None)
        mock_coordinator._schedule_state_refresh = MagicMock()

        with (
            patch(
                "custom_components.electrolux.switch.execute_command_with_error_handling",
                return_value=None,
            ),
            patch(
                "custom_components.electrolux.switch.format_command_for_appliance",
                return_value="ON",
            ),
        ):
            await entity.switch(True)

        mock_coordinator._schedule_state_refresh.assert_called_once_with("TEST_PNC")


class TestElectroluxSwitchSetup:
    """Test the switch platform dynamic setup and capability filtering."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_filters_phantom_entities(self):
        """Verify supported switches load, and phantoms absent from reported state are pruned."""
        hass = MagicMock()
        entry = MagicMock()
        async_add_entities = MagicMock()

        # Mock runtime data setup
        coordinator = MagicMock()
        entry.runtime_data = coordinator

        # Mock appliances collection
        mock_appliance = MagicMock()
        mock_appliance.reported_state = {
            "userSelections/EWX1493A_preWashPhase": True,  # Supported path
            "looseAttr": False,  # Supported loose attribute
        }

        # Entity definitions
        entity_valid_path = MagicMock()
        entity_valid_path.entity_type = SWITCH
        entity_valid_path.json_path = "userSelections/EWX1493A_preWashPhase"
        entity_valid_path.entity_attr = "EWX1493A_preWashPhase"

        entity_valid_attr = MagicMock()
        entity_valid_attr.entity_type = SWITCH
        entity_valid_attr.json_path = None
        entity_valid_attr.entity_attr = "looseAttr"

        entity_phantom = MagicMock()
        entity_phantom.entity_type = SWITCH
        entity_phantom.json_path = "userSelections/EWX1493A_pod"
        entity_phantom.entity_attr = "EWX1493A_pod"

        mock_appliance.entities = [entity_valid_path, entity_valid_attr, entity_phantom]

        appliances_container = MagicMock()
        appliances_container.appliances = {"appliance_1": mock_appliance}
        coordinator.data = {"appliances": appliances_container}

        # Run setup entry execution loop
        await async_setup_entry(hass, entry, async_add_entities)

        # Confirm only the 2 supported entities get registered
        async_add_entities.assert_called_once()
        added_entities = async_add_entities.call_args[0][0]
        assert len(added_entities) == 2
        assert entity_valid_path in added_entities
        assert entity_valid_attr in added_entities
        assert entity_phantom not in added_entities
