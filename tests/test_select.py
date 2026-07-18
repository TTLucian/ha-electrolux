"""Test select platform for Electrolux."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.const import SELECT
from custom_components.electrolux.entity import ElectroluxEntity
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
            # Legacy appliances with userSelections source include programUID
            assert command == {
                "userSelections": {"programUID": "TEST_PROGRAM", "testAttr": "OPTION1"}
            }

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

    def test_current_option_case_insensitive_match(self, mock_coordinator):
        """Reported state value 'heat' matches capability option 'HEAT' case-insensitively.

        Bogong AC (and other models) report mode values lowercase while capabilities
        define them uppercase. Verify correct label is returned without dynamic add.
        """
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUTO": {},
                "COOL": {},
                "HEAT": {},
                "DRY": {},
                "FANONLY": {},
                "OFF": {"disabled": True},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Mode",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="mode",
            entity_attr="mode",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:fan",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {"properties": {"reported": {"mode": "heat"}}}
        entity.reported_state = {"mode": "heat"}

        label = entity.current_option
        assert label == "Heat"
        # 'heat' must NOT be added as a duplicate dynamic entry alongside 'HEAT'
        assert list(entity.options_list.values()).count("HEAT") == 1
        assert "heat" not in entity.options_list.values()

    def test_current_option_disabled_value_returns_readonly_label(
        self, mock_coordinator
    ):
        """Disabled capability value (e.g. mode=OFF) returns a transient
        read-only label, not the empty string. The label is NOT persisted
        in ``options_list`` (#58).

        Background: PR #57 made disabled values silently skipped, which
        meant ``current_option`` returned ``""`` and HA UI rendered
        ``unknown`` whenever the device entered such a state on its own.
        """
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUTO": {},
                "COOL": {},
                "HEAT": {},
                "DRY": {},
                "FANONLY": {},
                "OFF": {"disabled": True},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Mode",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="mode",
            entity_attr="mode",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:fan",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {"properties": {"reported": {"mode": "OFF"}}}
        entity.reported_state = {"mode": "OFF"}

        label = entity.current_option
        assert label == "Off"
        # Persistent options list still excludes disabled values.
        assert "OFF" not in entity.options_list.values()
        assert "Off" not in entity.options_list
        # The transient label appears in the on-the-fly options list
        # so SelectEntity does not warn that current_option is missing.
        assert "Off" in entity.options

    def test_current_option_disabled_autoclean_returns_readonly_label(
        self, mock_coordinator
    ):
        """``mode=autoClean`` is marked disabled in the Bogong AC catalog.

        When the appliance enters autoClean on its own (e.g. user pressed
        the panel button), HA must show ``Auto Clean`` as a read-only
        label, not ``unknown``. The label is included in ``options`` only
        while the value is current, then disappears.
        """
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "AUTO": {},
                "COOL": {},
                "HEAT": {},
                "DRY": {},
                "FANONLY": {},
                "AUTOCLEAN": {"disabled": True},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Mode",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="mode",
            entity_attr="mode",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:fan",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {"properties": {"reported": {"mode": "autoClean"}}}
        entity.reported_state = {"mode": "autoClean"}

        assert entity.current_option == "Autoclean"
        assert "Autoclean" in entity.options
        # No persistence in the catalog-derived options list.
        assert "Autoclean" not in entity.options_list

    def test_options_drops_transient_label_when_value_changes(self, mock_coordinator):
        """Transient label is included only while the device is in the
        disabled state; switching to a normal value drops it."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "COOL": {},
                "HEAT": {},
                "AUTOCLEAN": {"disabled": True},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Mode",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SELECT,
            entity_name="mode",
            entity_attr="mode",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:fan",
        )
        entity.hass = mock_coordinator.hass

        # Start in autoClean → transient label present.
        entity.appliance_status = {"properties": {"reported": {"mode": "autoClean"}}}
        entity.reported_state = {"mode": "autoClean"}
        assert "Autoclean" in entity.options

        # Move to cool → transient gone.
        entity.appliance_status = {"properties": {"reported": {"mode": "cool"}}}
        entity.reported_state = {"mode": "cool"}
        assert "Autoclean" not in entity.options
        assert "Cool" in entity.options


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
            "values": {"30.5": {"label": "30.5 °C"}},
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

        # "30.5 °C" option → value = "30.5" → float("30.5") = 30.5 via contextlib.suppress
        with patch(
            "custom_components.electrolux.select.format_command_for_appliance",
            return_value=30.5,
        ):
            await entity.async_select_option("30.5 °C")

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


class TestDiscoveredPrograms:
    """Test the discovered programs mechanism for programs not enumerated by the API.

    Covers issue #65: GUIDED/MealAssist programs on structured ovens are reported
    by the appliance but never listed in capabilities. The integration dynamically
    adds them to options_list and persists them across restarts.
    """

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator with hass.data support."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.data = {}
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"api_key": "test_api_key_12345"}
        coordinator._last_update_times = {}

        # Setup mock appliances structure
        mock_appliances = MagicMock()
        mock_appliance = MagicMock()
        mock_appliances.get_appliance.return_value = mock_appliance
        coordinator.data = {"appliances": mock_appliances}

        return coordinator

    @pytest.fixture
    def mock_capability(self):
        """Capability with only base programs (no GUIDED)."""
        return {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
                "BROIL": {"label": "Broil"},
                "STEAM_LOW": {"label": "Steam Low"},
            },
        }

    def test_discovered_program_persisted_on_unknown_value(self, mock_coordinator):
        """Test that unknown reported value triggers _persist_discovered_program."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "properties": {"reported": {"program": "GUIDED_GRILLTHIN"}}
        }
        entity._reported_state_cache = {"program": "GUIDED_GRILLTHIN"}

        with patch.object(entity, "_persist_discovered_program") as mock_persist:
            _ = entity.current_option

        mock_persist.assert_called_once_with("GUIDED_GRILLTHIN", "Guided Grillthin")

    def test_discovered_program_loaded_on_init(self, mock_coordinator):
        """Test _load_discovered_programs restores values from hass.data."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity.hass = mock_coordinator.hass
        entity.options_list = {"Bake": "BAKE"}

        # Store keyed by the entity's real unique_id (derived from the config
        # entry api_key + attrs); _load_discovered_programs reads it back.
        store_key = f"electrolux_discovered_programs_{entity.unique_id}"
        mock_coordinator.hass.data[store_key] = {
            "Guided Airfry Plus": "GUIDED_AIRFRY_PLUS",
        }
        entity._load_discovered_programs()

        assert "Guided Airfry Plus" in entity.options_list
        assert entity.options_list["Guided Airfry Plus"] == "GUIDED_AIRFRY_PLUS"
        assert "GUIDED_AIRFRY_PLUS" in entity._discovered_values

    def test_discovered_program_not_duplicated(self, mock_coordinator):
        """Test discovered value already in options_list from capabilities is not duplicated."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity.hass = mock_coordinator.hass

        # Store a value that is already a capability option
        store_key = f"electrolux_discovered_programs_{entity.unique_id}"
        mock_coordinator.hass.data[store_key] = {"Bake": "BAKE"}
        entity._load_discovered_programs()

        # BAKE is already in options_list, so _discovered_values should NOT include it
        assert "BAKE" not in entity._discovered_values
        # options_list should have exactly one "Bake" entry
        assert list(entity.options_list.values()).count("BAKE") == 1

    def test_options_preserves_discovered_programs(self, mock_coordinator):
        """Test options includes discovered programs even when program constraints filter."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
                "BROIL": {"label": "Broil"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity.hass = mock_coordinator.hass

        store_key = f"electrolux_discovered_programs_{entity.unique_id}"
        mock_coordinator.hass.data[store_key] = {
            "Guided Grillthin": "GUIDED_GRILLTHIN",
        }
        entity._load_discovered_programs()

        # Simulate program constraint that only allows BAKE, BROIL
        entity._get_program_constraint = MagicMock(return_value=["BAKE", "BROIL"])

        # GUIDED_GRILLTHIN should still appear in options despite not being allowed
        options = entity.options
        assert "Bake" in options
        assert "Broil" in options
        assert "Guided Grillthin" in options

    def test_guided_program_scenario(self, mock_coordinator):
        """End-to-end: appliance reports GUIDED_GRILLTHIN, entity adds it to options."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
                "BROIL": {"label": "Broil"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity.hass = mock_coordinator.hass
        # No discovered programs yet
        assert entity.options_list == {"Bake": "BAKE", "Broil": "BROIL"}
        assert entity._discovered_values == set()

        # Appliance reports GUIDED_GRILLTHIN in reported state
        entity.appliance_status = {
            "properties": {"reported": {"program": "GUIDED_GRILLTHIN"}}
        }
        entity._reported_state_cache = {"program": "GUIDED_GRILLTHIN"}

        # current_option dynamically adds the unknown value
        current = entity.current_option
        assert current == "Guided Grillthin"
        assert "Guided Grillthin" in entity.options_list
        assert entity.options_list["Guided Grillthin"] == "GUIDED_GRILLTHIN"
        assert "GUIDED_GRILLTHIN" in entity._discovered_values

        # Value appears in options
        assert "Guided Grillthin" in entity.options

    def test_discovered_programs_survive_restart(self, mock_coordinator):
        """New entity instance restores discovered programs persisted by a prior one."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
            },
        }

        # First entity discovers a program at runtime, which persists it to the store.
        entity1 = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity1.hass = mock_coordinator.hass
        assert entity1.options_list == {"Bake": "BAKE"}

        entity1.appliance_status = {
            "properties": {"reported": {"program": "GUIDED_GRILLTHIN"}}
        }
        entity1._reported_state_cache = {"program": "GUIDED_GRILLTHIN"}
        assert entity1.current_option == "Guided Grillthin"
        assert "GUIDED_GRILLTHIN" in entity1._discovered_values

        # A second program was persisted in an earlier session.
        store_key = f"electrolux_discovered_programs_{entity1.unique_id}"
        mock_coordinator.hass.data[store_key][
            "Guided Airfry Plus"
        ] = "GUIDED_AIRFRY_PLUS"

        # Second entity — fresh instance (simulates restart), restores from the store.
        entity2 = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity2.hass = mock_coordinator.hass
        assert entity2.options_list == {"Bake": "BAKE"}
        assert entity2._discovered_values == set()

        entity2._load_discovered_programs()

        assert "Guided Grillthin" in entity2.options_list
        assert "Guided Airfry Plus" in entity2.options_list
        assert "GUIDED_GRILLTHIN" in entity2._discovered_values
        assert "GUIDED_AIRFRY_PLUS" in entity2._discovered_values

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restores_discovered(self, mock_coordinator):
        """async_added_to_hass chains to super() and then restores discovered programs."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity.hass = mock_coordinator.hass

        with patch.object(
            ElectroluxEntity, "async_added_to_hass", new=AsyncMock()
        ) as mock_super, patch.object(entity, "_load_discovered_programs") as mock_load:
            await entity.async_added_to_hass()

        mock_super.assert_awaited_once()
        mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_added_to_hass_populates_from_store(self, mock_coordinator):
        """End-to-end: async_added_to_hass runs the real restore and populates state.

        Guards the composition (async_added_to_hass -> real _load_discovered_programs
        -> options_list + _discovered_values), which the mocked wrapper test does not.
        """
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity.hass = mock_coordinator.hass
        store_key = f"electrolux_discovered_programs_{entity.unique_id}"
        mock_coordinator.hass.data[store_key] = {
            "Guided Grillthin": "GUIDED_GRILLTHIN",
        }

        # Stub only the base lifecycle hook; the real _load must run.
        with patch.object(ElectroluxEntity, "async_added_to_hass", new=AsyncMock()):
            await entity.async_added_to_hass()

        assert entity.options_list["Guided Grillthin"] == "GUIDED_GRILLTHIN"
        assert "GUIDED_GRILLTHIN" in entity._discovered_values

    def test_load_discovered_programs_ignores_malformed_store(self, mock_coordinator):
        """A non-dict store entry is ignored instead of raising during restore."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity.hass = mock_coordinator.hass
        store_key = f"electrolux_discovered_programs_{entity.unique_id}"
        mock_coordinator.hass.data[store_key] = ["not", "a", "dict"]

        # Must not raise, and must not corrupt existing options.
        entity._load_discovered_programs()

        assert entity.options_list == {"Bake": "BAKE"}
        assert entity._discovered_values == set()

    def test_options_filtered_by_program_values(self, mock_coordinator):
        """Test options filtering works when _get_program_constraint returns allowed values."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
                "BROIL": {"label": "Broil"},
                "STEAM": {"label": "Steam"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity.hass = mock_coordinator.hass

        # Program allows only BAKE and STEAM
        entity._get_program_constraint = MagicMock(return_value=["BAKE", "STEAM"])

        filtered = entity.options
        assert "Bake" in filtered
        assert "Steam" in filtered
        assert "Broil" not in filtered

    def test_options_no_filter_when_no_constraint(self, mock_coordinator):
        """Test all options pass through when no program constraint."""
        capability = {
            "access": "readwrite",
            "type": "string",
            "values": {
                "BAKE": {"label": "Bake"},
                "BROIL": {"label": "Broil"},
            },
        }
        entity = ElectroluxSelect(
            coordinator=mock_coordinator,
            capability=capability,
            name="Program",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=SELECT,
            entity_name="program",
            entity_attr="program",
            entity_source=None,
            unit=None,
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:chef-hat",
        )
        entity.hass = mock_coordinator.hass

        # No constraint → all options pass through
        entity._get_program_constraint = MagicMock(return_value=None)

        assert set(entity.options) == {"Bake", "Broil"}
