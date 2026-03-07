"""Test switch platform for Electrolux."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.const import SWITCH
from custom_components.electrolux.switch import ElectroluxSwitch


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
        """Test is_on handles None values."""
        switch_entity.appliance_status = {"properties": {"reported": {}}}
        switch_entity.reported_state = {}
        switch_entity.extract_value = MagicMock(return_value=None)
        assert switch_entity.is_on is False

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
    async def test_switch_with_user_selections_source(
        self, mock_coordinator, mock_capability
    ):
        """Test switch command with userSelections entity source."""
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
            # Legacy appliances with userSelections source include programUID
            assert command == {
                "userSelections": {"programUID": "TEST_PROGRAM", "testAttr": "ON"}
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

        with patch(
            "custom_components.electrolux.switch.execute_command_with_error_handling",
            side_effect=AuthenticationError("token expired"),
        ), patch(
            "custom_components.electrolux.switch.format_command_for_appliance",
            return_value="ON",
        ), patch.object(
            switch_entity, "coordinator", mock_coord
        ):
            with pytest.raises(AuthenticationError):
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
        with patch(
            "custom_components.electrolux.switch.execute_command_with_error_handling",
            side_effect=generic_err,
        ), patch(
            "custom_components.electrolux.switch.format_command_for_appliance",
            return_value="OFF",
        ):
            with pytest.raises(HomeAssistantError, match="remote control disabled"):
                await entity.switch(True)
