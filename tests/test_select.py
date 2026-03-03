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
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
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
        entity.hass = mock_coordinator.hass  # Set hass for the entity
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
        assert select_entity.current_option == ""

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
        entity.hass = mock_coordinator.hass  # Set hass for the entity
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
        """Test selecting option when remote control is disabled - command is sent optimistically to API."""
        select_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "DISABLED"}}
        }

        # With optimistic sending, command should be sent to API (API will validate)
        # Mock the API to simulate successful call (API would reject if truly disabled)
        select_entity.api.execute_appliance_command = AsyncMock(return_value=None)
        await select_entity.async_select_option("Option 1")

        # Verify command was sent to API (not blocked client-side)
        select_entity.api.execute_appliance_command.assert_called_once()

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
        entity.hass = mock_coordinator.hass  # Set hass for the entity
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

            # Verify command structure for Legacy appliance with userSelections source
            call_args = entity.api.execute_appliance_command.call_args
            pnc_id, command = call_args[0]
            assert pnc_id == "TEST_PNC"
            # Legacy appliances with entity_source also wrap the command in the source container
            assert command == {"userSelections": {"testAttr": "OPTION1"}}

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
        entity.hass = mock_coordinator.hass  # Set hass for the entity
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

            # Verify command structure for Legacy appliance with appliance source
            call_args = entity.api.execute_appliance_command.call_args
            pnc_id, command = call_args[0]
            assert pnc_id == "TEST_PNC"
            # Legacy appliances with entity_source also wrap the command in the source container
            assert command == {"oven": {"testAttr": "OPTION1"}}

    def test_available_property_remote_control_disabled(self, select_entity):
        """Test availability when remote control is disabled (but connected)."""
        select_entity.is_connected = MagicMock(return_value=True)
        select_entity.is_remote_control_enabled = MagicMock(return_value=False)
        assert (
            select_entity.available
        )  # Should be available even with remote control disabled

    def test_available_property_remote_control_enabled(self, select_entity):
        """Test availability when remote control is enabled."""
        select_entity.is_connected = MagicMock(return_value=True)
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
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        assert entity.options_list == {}
        assert entity.options == []


class TestSelectAvailableProperty:
    """Test the available property for select entities."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {
            "access": "readwrite",
            "type": "string",
            "values": {"OPT1": {"label": "Opt 1"}},
        }

    def test_available_super_returns_false(self, mock_coordinator, mock_capability):
        """Test available returns False when super().available is False (no appliance_status)."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = None  # triggers super().available = False
        assert entity.available is False


class TestSelectFormatLabel:
    """Test format_label with temperature units."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        return coordinator

    def test_format_label_celsius(self, mock_coordinator):
        """Test format_label appends °C for Celsius unit."""
        from homeassistant.const import UnitOfTemperature

        capability = {"access": "readwrite", "type": "number", "values": {}}
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Temp",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="targetTemp",
            entity_attr="targetTemp",
            entity_source=None,
            unit=UnitOfTemperature.CELSIUS,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        entity.hass = mock_coordinator.hass
        assert entity.format_label(30) == "30 °C"

    def test_format_label_fahrenheit(self, mock_coordinator):
        """Test format_label appends °F for Fahrenheit unit."""
        from homeassistant.const import UnitOfTemperature

        capability = {"access": "readwrite", "type": "number", "values": {}}
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Temp",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="targetTemp",
            entity_attr="targetTemp",
            entity_source=None,
            unit=UnitOfTemperature.FAHRENHEIT,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        entity.hass = mock_coordinator.hass
        assert entity.format_label(80) == "80 °F"

    def test_format_label_none_returns_none(self, mock_coordinator):
        """Test format_label with None returns None."""
        capability = {"access": "readwrite", "type": "string", "values": {}}
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Test",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test",
            entity_attr="test",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        assert entity.format_label(None) is None


class TestSelectCurrentOption:
    """Test current_option with program support and value_mapping."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {
            "access": "readwrite",
            "type": "string",
            "values": {
                "OPTION1": {"label": "Option 1"},
                "OPTION2": {"label": "Option 2"},
            },
        }

    def test_current_option_non_config_not_supported_returns_empty(
        self, mock_coordinator, mock_capability
    ):
        """Test current_option returns empty string when non-CONFIG entity is not supported by program."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.DIAGNOSTIC,  # non-CONFIG
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {"properties": {"reported": {"testAttr": "OPTION1"}}}
        entity._reported_state_cache = {"testAttr": "OPTION1"}
        entity._is_supported_by_program = MagicMock(return_value=False)
        assert entity.current_option == ""

    def test_current_option_with_catalog_value_mapping(
        self, mock_coordinator, mock_capability
    ):
        """Test current_option applies value_mapping from catalog_entry."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            value_mapping={"RAW_VAL": "OPTION1"},
        )
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        entity.hass = mock_coordinator.hass
        # Reported state returns "RAW_VAL" which maps to "OPTION1" via value_mapping
        entity.appliance_status = {"properties": {"reported": {"testAttr": "RAW_VAL"}}}
        entity._reported_state_cache = {"testAttr": "RAW_VAL"}
        # current_option should map "RAW_VAL" → "OPTION1" → find label "Option 1"
        assert entity.current_option == "Option 1"


class TestSelectAsyncSelectOptionAdvanced:
    """Test async_select_option advanced paths: program check, offline, DAM paths, auth error."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {
            "access": "readwrite",
            "type": "string",
            "values": {
                "OPTION1": {"label": "Option 1"},
                "OPTION2": {"label": "Option 2"},
            },
        }

    def _make_select(
        self,
        coordinator,
        capability,
        pnc_id="TEST_PNC",
        entity_source=None,
        entity_attr="testAttr",
        entity_category=EntityCategory.CONFIG,
        entity_name="test",
    ):
        entity = ElectroluxSelect(
            coordinator=coordinator,
            capability=capability,
            name="Test Select",
            config_entry=coordinator.config_entry,
            pnc_id=pnc_id,
            entity_type=SELECT,
            entity_name=entity_name,
            entity_attr=entity_attr,
            entity_source=entity_source,
            unit=None,
            device_class="",
            entity_category=entity_category,
            icon="mdi:test",
        )
        entity.hass = coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"connectivityState": "connected"}}
        }
        entity._reported_state_cache = {"connectivityState": "connected"}
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=None)
        return entity

    @pytest.mark.asyncio
    async def test_not_supported_by_program_raises(
        self, mock_coordinator, mock_capability
    ):
        """Test async_select_option raises when non-CONFIG entity is not supported by program."""
        entity = self._make_select(
            mock_coordinator, mock_capability, entity_category=EntityCategory.DIAGNOSTIC
        )
        entity._is_supported_by_program = MagicMock(return_value=False)
        entity._get_current_program_name = MagicMock(return_value="Cotton")

        with pytest.raises(HomeAssistantError):
            await entity.async_select_option("Option 1")

    @pytest.mark.asyncio
    async def test_offline_appliance_raises(self, mock_coordinator, mock_capability):
        """Test async_select_option raises HomeAssistantError when appliance is offline."""
        entity = self._make_select(mock_coordinator, mock_capability)
        entity._reported_state_cache = {"connectivityState": "disconnected"}
        entity.appliance_status = {
            "properties": {"reported": {"connectivityState": "disconnected"}}
        }

        with pytest.raises(HomeAssistantError, match="offline"):
            await entity.async_select_option("Option 1")

    @pytest.mark.asyncio
    async def test_dam_with_entity_source_not_user_selections(
        self, mock_coordinator, mock_capability
    ):
        """Test DAM appliance with non-userSelections entity_source wraps command correctly."""
        entity = self._make_select(
            mock_coordinator,
            mock_capability,
            pnc_id="1:TEST_PNC",
            entity_source="airConditioner",
        )

        with patch(
            "custom_components.electrolux.select.format_command_for_appliance",
            return_value="OPTION1",
        ):
            await entity.async_select_option("Option 1")

        entity.api.execute_appliance_command.assert_called_once_with(  # type: ignore[union-attr]
            "1:TEST_PNC",
            {"commands": [{"airConditioner": {"testAttr": "OPTION1"}}]},
        )

    @pytest.mark.asyncio
    async def test_dam_with_user_selections_and_program_uid(
        self, mock_coordinator, mock_capability
    ):
        """Test DAM appliance with userSelections wraps command with programUID."""
        entity = self._make_select(
            mock_coordinator,
            mock_capability,
            pnc_id="1:TEST_PNC",
            entity_source="userSelections",
        )
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "connectivityState": "connected",
                    "userSelections": {"programUID": "COTTON"},
                }
            }
        }
        entity._reported_state_cache = {
            "connectivityState": "connected",
            "userSelections": {"programUID": "COTTON"},
        }

        with patch(
            "custom_components.electrolux.select.format_command_for_appliance",
            return_value="OPTION1",
        ):
            await entity.async_select_option("Option 1")

        entity.api.execute_appliance_command.assert_called_once_with(  # type: ignore[union-attr]
            "1:TEST_PNC",
            {
                "commands": [
                    {"userSelections": {"programUID": "COTTON", "testAttr": "OPTION1"}}
                ]
            },
        )

    @pytest.mark.asyncio
    async def test_dam_user_selections_missing_program_uid_raises(
        self, mock_coordinator, mock_capability
    ):
        """Test DAM appliance with userSelections but missing programUID raises error."""
        entity = self._make_select(
            mock_coordinator,
            mock_capability,
            pnc_id="1:TEST_PNC",
            entity_source="userSelections",
        )
        entity.appliance_status = {
            "properties": {
                "reported": {"connectivityState": "connected", "userSelections": {}}
            }
        }
        entity._reported_state_cache = {
            "connectivityState": "connected",
            "userSelections": {},
        }

        with patch(
            "custom_components.electrolux.select.format_command_for_appliance",
            return_value="OPTION1",
        ):
            with pytest.raises(
                HomeAssistantError, match="appliance state is incomplete"
            ):
                await entity.async_select_option("Option 1")

    @pytest.mark.asyncio
    async def test_dam_no_source_program_entity_attr(
        self, mock_coordinator, mock_capability
    ):
        """Test DAM appliance with entity_attr='program' builds userSelections command."""
        entity = self._make_select(
            mock_coordinator,
            mock_capability,
            pnc_id="1:TEST_PNC",
            entity_source=None,
            entity_attr="program",
        )
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "connectivityState": "connected",
                    "userSelections": {"programUID": "COTTON"},
                }
            }
        }
        entity._reported_state_cache = {
            "connectivityState": "connected",
            "userSelections": {"programUID": "COTTON"},
        }

        with patch(
            "custom_components.electrolux.select.format_command_for_appliance",
            return_value="OPTION1",
        ):
            await entity.async_select_option("Option 1")

        entity.api.execute_appliance_command.assert_called_once_with(  # type: ignore[union-attr]
            "1:TEST_PNC",
            {
                "commands": [
                    {"userSelections": {"programUID": "COTTON", "program": "OPTION1"}}
                ]
            },
        )

    @pytest.mark.asyncio
    async def test_dam_no_source_no_program_entity_attr(
        self, mock_coordinator, mock_capability
    ):
        """Test DAM appliance with entity_attr != 'program' and no source wraps command simply."""
        entity = self._make_select(
            mock_coordinator,
            mock_capability,
            pnc_id="1:TEST_PNC",
            entity_source=None,
            entity_attr="fanMode",
        )

        with patch(
            "custom_components.electrolux.select.format_command_for_appliance",
            return_value="OPTION1",
        ):
            await entity.async_select_option("Option 1")

        entity.api.execute_appliance_command.assert_called_once_with(  # type: ignore[union-attr]
            "1:TEST_PNC",
            {"commands": [{"fanMode": "OPTION1"}]},
        )

    @pytest.mark.asyncio
    async def test_dam_no_source_program_no_program_uid(
        self, mock_coordinator, mock_capability
    ):
        """Test DAM program entity with no programUID in userSelections falls back to simple command."""
        entity = self._make_select(
            mock_coordinator,
            mock_capability,
            pnc_id="1:TEST_PNC",
            entity_source=None,
            entity_attr="program",
        )
        entity.appliance_status = {
            "properties": {
                "reported": {"connectivityState": "connected", "userSelections": {}}
            }
        }
        entity._reported_state_cache = {
            "connectivityState": "connected",
            "userSelections": {},
        }

        with patch(
            "custom_components.electrolux.select.format_command_for_appliance",
            return_value="OPTION1",
        ):
            await entity.async_select_option("Option 1")

        entity.api.execute_appliance_command.assert_called_once_with(  # type: ignore[union-attr]
            "1:TEST_PNC",
            {"commands": [{"program": "OPTION1"}]},
        )

    @pytest.mark.asyncio
    async def test_auth_error_triggers_reauth(self, mock_coordinator, mock_capability):
        """Test AuthenticationError triggers coordinator.handle_authentication_error."""
        from custom_components.electrolux.util import AuthenticationError

        entity = self._make_select(mock_coordinator, mock_capability)
        mock_coordinator.handle_authentication_error = AsyncMock()
        auth_ex = AuthenticationError("token expired")

        with patch(
            "custom_components.electrolux.select.execute_command_with_error_handling",
            side_effect=auth_ex,
        ):
            with patch(
                "custom_components.electrolux.select.format_command_for_appliance",
                return_value="OPTION1",
            ):
                await entity.async_select_option("Option 1")

        mock_coordinator.handle_authentication_error.assert_called_once_with(auth_ex)

    @pytest.mark.asyncio
    async def test_optimistic_update_applied_on_success(
        self, mock_coordinator, mock_capability
    ):
        """Test _apply_optimistic_update is called after successful command."""
        entity = self._make_select(mock_coordinator, mock_capability)
        entity._apply_optimistic_update = MagicMock()

        with patch(
            "custom_components.electrolux.select.format_command_for_appliance",
            return_value="OPTION2",
        ):
            await entity.async_select_option("Option 2")

        entity._apply_optimistic_update.assert_called_once_with("testAttr", "OPTION2")


class TestSelectOptionsFiltering:
    """Test options property with program constraints."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {
            "access": "readwrite",
            "type": "string",
            "values": {
                "OPTION1": {"label": "Option 1"},
                "OPTION2": {"label": "Option 2"},
                "OPTION3": {"label": "Option 3"},
            },
        }

    def test_options_filtered_by_program_constraint(
        self, mock_coordinator, mock_capability
    ):
        """Test options returns only program-allowed options when constraint is set."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        entity._get_program_constraint = MagicMock(return_value=["OPTION1", "OPTION3"])

        filtered = entity.options
        assert "Option 1" in filtered
        assert "Option 3" in filtered
        assert "Option 2" not in filtered

    def test_options_no_program_constraint_returns_all(
        self, mock_coordinator, mock_capability
    ):
        """Test options returns all options when no program constraint."""
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        entity._get_program_constraint = MagicMock(return_value=None)

        filtered = entity.options
        assert set(filtered) == {"Option 1", "Option 2", "Option 3"}


class TestSelectMissingCoveragePaths:
    """Tests to cover previously uncovered select.py paths."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        return coordinator

    def test_init_entry_without_label_key_calls_format_label(self, mock_coordinator):
        """Test __init__ calls self.format_label when entry exists but has no 'label' key (line 97)."""
        # Entry with non-empty dict but no 'label' key triggers line 97
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "OPTION_A": {
                    "access": "read"
                },  # truthy dict without 'label' -> falls to format_label
                "OPTION_B": {"label": "Named"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Test",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        # OPTION_A has no "label" → format_label("OPTION_A") = "Option A"
        assert "Option A" in entity.options_list
        assert "Named" in entity.options_list

    @pytest.mark.asyncio
    async def test_temperature_unit_converts_option_to_float(self, mock_coordinator):
        """Test async_select_option converts value to float for temperature unit (lines 227-228)."""
        from homeassistant.const import UnitOfTemperature

        capability = {
            "access": "readwrite",
            "type": "number",
            "values": {"30": {"label": "30 °C"}},
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Temp",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="targetTemperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            unit=UnitOfTemperature.CELSIUS,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:thermometer",
        )
        entity.hass = mock_coordinator.hass
        entity._reported_state_cache = {"connectivityState": "connected"}
        entity.appliance_status = {
            "properties": {"reported": {"connectivityState": "connected"}}
        }
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=None)

        # "30 °C" option → value = "30" → float("30") = 30.0 via contextlib.suppress
        with patch(
            "custom_components.electrolux.select.format_command_for_appliance",
            return_value=30.0,
        ):
            await entity.async_select_option("30 °C")

        entity.api.execute_appliance_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_generic_exception_reraised(self, mock_coordinator):
        """Test generic exception from execute_command_with_error_handling is re-raised (lines 319-321)."""
        from homeassistant.exceptions import HomeAssistantError

        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {"OPTION1": {"label": "Option 1"}},
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Test",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        entity._reported_state_cache = {"connectivityState": "connected"}
        entity.appliance_status = {
            "properties": {"reported": {"connectivityState": "connected"}}
        }

        generic_err = HomeAssistantError("remote control disabled")
        with patch(
            "custom_components.electrolux.select.execute_command_with_error_handling",
            side_effect=generic_err,
        ):
            with patch(
                "custom_components.electrolux.select.format_command_for_appliance",
                return_value="OPTION1",
            ):
                with pytest.raises(HomeAssistantError, match="remote control disabled"):
                    await entity.async_select_option("Option 1")

    def test_handle_coordinator_update_calls_super(self, mock_coordinator):
        """Test _handle_coordinator_update calls super()._handle_coordinator_update (line 340)."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {"OPT1": {"label": "Opt 1"}},
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Test",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {"properties": {"reported": {}}}
        entity._reported_state_cache = {}

        # Call _handle_coordinator_update - it calls super()._handle_coordinator_update()
        # which reads from coordinator data. We just need to call it without error.
        entity.async_write_ha_state = MagicMock()
        entity._handle_coordinator_update()
        # If we got here without error, super() was called successfully
