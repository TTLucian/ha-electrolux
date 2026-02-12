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
        entity.appliance_status = {"properties": {"reported": {"testAttr": True}}}
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
        """Test turning on when remote control is disabled raises error."""
        switch_entity.is_remote_control_enabled = MagicMock(return_value=False)

        with pytest.raises(HomeAssistantError, match="Remote control is disabled"):
            await switch_entity.async_turn_on()

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
            # Legacy appliances send simple commands, not wrapped in userSelections
            assert command == {"testAttr": "ON"}

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
            # Legacy appliances send simple commands, not wrapped in appliance type
            assert command == {"testAttr": "ON"}

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
        """Test availability when remote control is disabled."""
        switch_entity.is_remote_control_enabled = MagicMock(return_value=False)
        assert not switch_entity.available

    def test_available_property_remote_control_enabled(self, switch_entity):
        """Test availability when remote control is enabled."""
        switch_entity.is_remote_control_enabled = MagicMock(return_value=True)
        assert switch_entity.available
