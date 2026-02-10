"""Test select platform for Electrolux."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.const import SELECT
from custom_components.electrolux.select import ElectroluxSelect


class TestElectroluxSelect:
    """Test the Electrolux Select entity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.config_entry = MagicMock()
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        """Create a mock capability with options."""
        return {
            "access": "readwrite",
            "type": "string",
            "values": {
                "OPTION1": {"label": "Option 1"},
                "OPTION2": {"label": "Option 2"},
                "DISABLED_OPTION": {"disabled": True},
            },
        }

    @pytest.fixture
    def select_entity(self, mock_coordinator, mock_capability):
        """Create a test select entity."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Select",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.appliance_status = {"properties": {"reported": {"testAttr": "OPTION1"}}}
        entity.reported_state = {"testAttr": "OPTION1"}
        return entity

    def test_entity_domain(self, select_entity):
        """Test entity domain property."""
        assert select_entity.entity_domain == "select"

    def test_options_list_creation(self, select_entity):
        """Test that options list is created correctly from capability values."""
        expected_options = {"Option 1": "OPTION1", "Option 2": "OPTION2"}
        assert select_entity.options_list == expected_options

    def test_options_list_excludes_disabled(self, select_entity):
        """Test that disabled options are excluded from options list."""
        assert "DISABLED_OPTION" not in select_entity.options_list.values()

    def test_options_property(self, select_entity):
        """Test options property returns the keys of options_list."""
        assert set(select_entity.options) == {"Option 1", "Option 2"}

    def test_current_option_basic(self, select_entity):
        """Test current_option returns the formatted label."""
        assert select_entity.current_option == "Option 1"

    def test_current_option_none_value(self, select_entity):
        """Test current_option handles None values."""
        select_entity.extract_value = MagicMock(return_value=None)
        assert select_entity.current_option is None

    def test_current_option_unknown_value(self, select_entity):
        """Test current_option handles unknown values."""
        select_entity.appliance_status = {
            "properties": {"reported": {"testAttr": "UNKNOWN"}}
        }
        select_entity.reported_state = {"testAttr": "UNKNOWN"}
        assert select_entity.current_option == "Unknown"

    def test_format_label_basic(self, select_entity):
        """Test basic label formatting."""
        assert select_entity.format_label("test_value") == "Test Value"

    def test_format_label_with_label_in_capability(self, mock_coordinator):
        """Test label formatting uses capability label if available."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "OPTION1": {"label": "Custom Label"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Test Select",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        # The options_list should use the custom label
        assert entity.options_list["Custom Label"] == "OPTION1"

    def test_format_label_disabled_option(self, select_entity):
        """Test that disabled options are formatted normally."""
        assert select_entity.format_label("DISABLED_OPTION") == "Disabled Option"

    @pytest.mark.asyncio
    async def test_async_select_option(self, select_entity):
        """Test selecting an option."""
        select_entity.api = MagicMock()
        select_entity.api.execute_appliance_command = AsyncMock()
        select_entity.is_remote_control_enabled = MagicMock(return_value=True)
        select_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        with patch(
            "custom_components.electrolux.select.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = "OPTION2"
            await select_entity.async_select_option("Option 2")

            mock_format.assert_called_once_with(
                select_entity.capability, "testAttr", "OPTION2"
            )

    @pytest.mark.asyncio
    async def test_async_select_option_invalid_option(self, select_entity):
        """Test selecting an invalid option raises error."""
        with pytest.raises(HomeAssistantError, match="Invalid option"):
            await select_entity.async_select_option("Invalid Option")

    @pytest.mark.asyncio
    async def test_async_select_option_remote_control_disabled(self, select_entity):
        """Test selecting option when remote control is disabled raises error."""
        select_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "DISABLED"}}
        }

        with pytest.raises(HomeAssistantError, match="Remote control disabled"):
            await select_entity.async_select_option("Option 1")

    @pytest.mark.asyncio
    async def test_select_with_user_selections_source(
        self, mock_coordinator, mock_capability
    ):
        """Test select command with userSelections entity source."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Select",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="testAttr",
            entity_source="userSelections",
            unit=None,
            device_class="",
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
            "custom_components.electrolux.select.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = "OPTION1"
            await entity.async_select_option("Option 1")

            # Verify command structure for userSelections
            call_args = entity.api.execute_appliance_command.call_args
            pnc_id, command = call_args[0]
            assert pnc_id == "TEST_PNC"
            assert "userSelections" in command
            assert command["userSelections"]["programUID"] == "TEST_PROGRAM"
            assert command["userSelections"]["testAttr"] == "OPTION1"

    @pytest.mark.asyncio
    async def test_select_with_appliance_source(
        self, mock_coordinator, mock_capability
    ):
        """Test select command with appliance-type entity source."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Select",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="testAttr",
            entity_source="oven",
            unit=None,
            device_class="",
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
            "custom_components.electrolux.select.format_command_for_appliance"
        ) as mock_format:
            mock_format.return_value = "OPTION1"
            await entity.async_select_option("Option 1")

            # Verify command structure for appliance source
            call_args = entity.api.execute_appliance_command.call_args
            pnc_id, command = call_args[0]
            assert pnc_id == "TEST_PNC"
            assert "oven" in command
            assert command["oven"]["testAttr"] == "OPTION1"

    def test_available_property_remote_control_disabled(self, select_entity):
        """Test availability when remote control is disabled."""
        select_entity.is_remote_control_enabled = MagicMock(return_value=False)
        assert not select_entity.available

    def test_available_property_remote_control_enabled(self, select_entity):
        """Test availability when remote control is enabled."""
        select_entity.is_remote_control_enabled = MagicMock(return_value=True)
        assert select_entity.available

    def test_select_without_options(self, mock_coordinator):
        """Test select entity with no options in capability."""
        capability = {"access": "readwrite", "type": "string"}
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Test Select",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test_select",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        assert entity.options_list == {}
        assert entity.options == []
