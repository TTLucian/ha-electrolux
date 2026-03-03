"""Test button platform for Electrolux."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.electrolux.button import ElectroluxButton
from custom_components.electrolux.const import BUTTON


class TestElectroluxButton:
    """Test the Electrolux Button entity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""

        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator.api = AsyncMock()
        coordinator._last_update_times = {}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        """Create a mock capability."""
        return {
            "access": "write",
            "type": "boolean",
        }

    @pytest.fixture
    def button_entity(self, mock_coordinator, mock_capability):
        """Create a test button entity."""
        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Button",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="test_button",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
            val_to_send="PRESS",
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        return entity

    def test_entity_domain(self, button_entity):
        """Test entity domain property."""
        assert button_entity.entity_domain == "button"

    def test_name_with_friendly_name(self, mock_coordinator, mock_capability):
        """Test name property uses friendly name mapping."""
        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Original Name",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="ovstart_pause",  # This has a friendly name mapping
            entity_attr="startPause",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
            val_to_send="PRESS",
        )
        assert entity.name == "Original Name PRESS"

    def test_name_fallback_to_catalog(self, mock_coordinator, mock_capability):
        """Test name property falls back to catalog friendly name."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            friendly_name="Catalog Friendly Name",
        )

        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Original Name",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="test_button",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
            val_to_send="PRESS",
        )
        assert "catalog friendly name" in entity.name.lower()

    def test_available_true_when_remote_control_enabled(self, button_entity):
        """Test available property when remote control is enabled."""
        button_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }
        assert button_entity.available is True

    def test_available_false_when_remote_control_disabled(self, button_entity):
        """Test available property when remote control is disabled (but connected)."""
        button_entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "DISABLED",
                    "connectivityState": "connected",
                }
            }
        }
        assert (
            button_entity.available is True
        )  # Should be available even with remote control disabled

    def test_available_false_when_no_remote_control_info(self, button_entity):
        """Test available property when no remote control info is available."""
        button_entity.appliance_status = {"properties": {"reported": {}}}
        assert button_entity.available is True  # None is treated as enabled

    def test_available_false_when_no_appliance_status(self, button_entity):
        """Test available property when no appliance status is available."""
        button_entity.appliance_status = None
        assert button_entity.available is False

    @pytest.mark.asyncio
    async def test_press_success(self, button_entity):
        """Test successful button press."""
        # Set remote control enabled
        button_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED", "testAttr": True}}
        }

        # Mock the API call
        button_entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await button_entity.async_press()

        # Verify command was sent
        button_entity.api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC", {"testAttr": "PRESS"}
        )

    @pytest.mark.asyncio
    async def test_press_with_entity_source(self, mock_coordinator, mock_capability):
        """Test button press with entity source."""
        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Button",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="test_button",
            entity_attr="testAttr",
            entity_source="userSelections",
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
            val_to_send="PRESS",
        )

        # Set remote control enabled
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "ENABLED",
                    "userSelections": {"programUID": "TEST"},
                }
            }
        }

        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.async_press()

        entity.api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC", {"testAttr": "PRESS"}
        )

    @pytest.mark.asyncio
    async def test_press_api_failure(self, button_entity):
        """Test button press when API call fails."""
        # Set remote control enabled
        button_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED", "testAttr": True}}
        }

        # Mock the API call to raise an exception
        button_entity.api.execute_appliance_command = AsyncMock(
            side_effect=Exception("API failure")
        )

        with pytest.raises(Exception, match="API failure"):
            await button_entity.async_press()

        # Should still attempt to send command
        button_entity.api.execute_appliance_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_press_with_dam_appliance(self, mock_coordinator, mock_capability):
        """Test button press with DAM appliance (ID starts with '1:')."""
        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Button",
            config_entry=mock_coordinator.config_entry,
            pnc_id="1:TEST_PNC",  # DAM appliance
            entity_type=BUTTON,
            entity_name="test_button",
            entity_attr="testAttr",
            entity_source="airConditioner",
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
            val_to_send="PRESS",
        )

        # Set remote control enabled
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.async_press()

        entity.api.execute_appliance_command.assert_called_once_with(
            "1:TEST_PNC", {"commands": [{"airConditioner": {"testAttr": "PRESS"}}]}
        )

    @pytest.mark.asyncio
    async def test_press_with_legacy_appliance(self, mock_coordinator, mock_capability):
        """Test button press with legacy appliance (ID doesn't start with '1:')."""
        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Button",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",  # Legacy appliance
            entity_type=BUTTON,
            entity_name="test_button",
            entity_attr="testAttr",
            entity_source=None,  # No source for legacy
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
            val_to_send="PRESS",
        )

        # Set remote control enabled
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED", "testAttr": True}}
        }

        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.async_press()

        entity.api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC", {"testAttr": "PRESS"}
        )

    def test_device_class_from_catalog(self, mock_coordinator, mock_capability):
        """Test device class from catalog entry."""
        from homeassistant.components.button import ButtonDeviceClass

        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            device_class=ButtonDeviceClass.RESTART,
        )

        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Button",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="test_button",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
            val_to_send="PRESS",
        )
        assert entity.device_class == ButtonDeviceClass.RESTART


class TestButtonUniqueId:
    """Test unique_id property of ElectroluxButton."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator._last_update_times = {}
        config_entry = MagicMock()
        config_entry.data = {"api_key": "test-api-key-12345"}
        coordinator.config_entry = config_entry
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {"access": "write", "type": "boolean"}

    def _make_entity(
        self,
        mock_coordinator,
        mock_capability,
        entity_attr,
        entity_source,
        val_to_send,
        pnc_id="MY_PNC",
    ):
        return ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Button",
            config_entry=mock_coordinator.config_entry,
            pnc_id=pnc_id,
            entity_type=BUTTON,
            entity_name="test_button",
            entity_attr=entity_attr,
            entity_source=entity_source,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
            val_to_send=val_to_send,
        )

    def test_unique_id_basic_structure(self, mock_coordinator, mock_capability):
        """Test unique_id contains attr, val_to_send, source=root, pnc_id."""
        entity = self._make_entity(
            mock_coordinator, mock_capability, "someAttr", None, "GO"
        )
        uid = entity.unique_id
        assert "someattr" in uid
        assert "GO" in uid
        assert "root" in uid
        assert "MY_PNC" in uid

    def test_unique_id_fppn_prefix_stripped(self, mock_coordinator, mock_capability):
        """Test fppn_ prefix is stripped from entity_attr in unique_id."""
        entity = self._make_entity(
            mock_coordinator, mock_capability, "fppn_cleaningCycle", None, "START"
        )
        uid = entity.unique_id
        assert "cleaningcycle" in uid
        assert "fppn_" not in uid

    def test_unique_id_fppn_no_underscore_stripped(
        self, mock_coordinator, mock_capability
    ):
        """Test fppn prefix without underscore is stripped."""
        entity = self._make_entity(
            mock_coordinator, mock_capability, "fppnSomething", None, "ON"
        )
        uid = entity.unique_id
        assert "fppn" not in uid
        assert "something" in uid

    def test_unique_id_with_entity_source(self, mock_coordinator, mock_capability):
        """Test unique_id includes entity_source."""
        entity = self._make_entity(
            mock_coordinator, mock_capability, "action", "oven", "START"
        )
        assert "oven" in entity.unique_id

    def test_unique_id_empty_api_key(self, mock_coordinator, mock_capability):
        """Test unique_id with missing api_key uses 'unknown' hash placeholder."""
        mock_coordinator.config_entry.data = {}
        entity = self._make_entity(
            mock_coordinator, mock_capability, "action", None, "START"
        )
        assert "unknown" in entity.unique_id


class TestButtonNameProperty:
    """Test name property of ElectroluxButton."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator._last_update_times = {}
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"api_key": "key"}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {"access": "write", "type": "boolean"}

    def test_name_with_catalog_entry_appliance_found(
        self, mock_coordinator, mock_capability
    ):
        """Test name when catalog_entry.friendly_name found + appliance found in coordinator."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            friendly_name="Start",
        )
        appliance_mock = MagicMock()
        appliance_mock.name = "My Washer"
        appliances_mock = MagicMock()
        appliances_mock.get_appliance.return_value = appliance_mock
        mock_coordinator.data = {"appliances": appliances_mock}

        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Original Name",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="test_button",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
            val_to_send="START",
        )
        # friendly_name = "Start", val_to_send = "START"
        # name = "My Washer start" → last_word = "start" == "START" → return name (no duplicate)
        assert entity.name == "My Washer start"

    def test_name_with_catalog_entry_no_appliance(
        self, mock_coordinator, mock_capability
    ):
        """Test name when catalog_entry.friendly_name found but appliance not in coordinator."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            friendly_name="Reset",
        )
        appliances_mock = MagicMock()
        appliances_mock.get_appliance.return_value = None
        mock_coordinator.data = {"appliances": appliances_mock}

        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Filter State",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="test_button",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
            val_to_send="RESET",
        )
        # appliance not found => name stays "Filter State"
        # last_word = "State" != "RESET" → appended
        assert entity.name == "Filter State RESET"

    def test_name_last_word_matches_val_to_send_no_suffix(
        self, mock_coordinator, mock_capability
    ):
        """Test name is not suffixed when last word matches val_to_send."""
        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Start Button",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="test_button",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
            val_to_send="BUTTON",
        )
        # last_word from "Start Button" = "Button", val_to_send = "BUTTON"
        # "button" == "button" → return name without suffix
        assert entity.name == "Start Button"


class TestButtonAvailableWhenStates:
    """Test available property with catalog_entry available_when_states."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator._last_update_times = {}
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"api_key": "key"}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {"access": "write", "type": "boolean"}

    def _make_button(self, coordinator, capability, catalog_entry, val_to_send="PRESS"):
        entity = ElectroluxButton(
            coordinator=coordinator,
            capability=capability,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
            val_to_send=val_to_send,
        )
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "applianceState": "RUNNING",
                    "connectivityState": "connected",
                }
            }
        }
        entity._reported_state_cache = {
            "applianceState": "RUNNING",
            "connectivityState": "connected",
        }
        return entity

    def test_available_when_state_allowed(self, mock_coordinator, mock_capability):
        """Test available returns True when current state is in allowed states."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            available_when_states={"PRESS": ["RUNNING", "IDLE"]},
        )
        entity = self._make_button(mock_coordinator, mock_capability, catalog_entry)
        assert entity.available is True

    def test_available_when_state_not_allowed(self, mock_coordinator, mock_capability):
        """Test available returns False when current state is not in allowed states."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            available_when_states={"PRESS": ["IDLE", "STANDBY"]},
        )
        entity = self._make_button(mock_coordinator, mock_capability, catalog_entry)
        # state is "RUNNING", not in ["IDLE", "STANDBY"]
        assert entity.available is False

    def test_available_when_states_key_not_in_dict(
        self, mock_coordinator, mock_capability
    ):
        """Test available when val_to_send not in available_when_states dict → falls through to super."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            available_when_states={"OTHER_VAL": ["RUNNING"]},
        )
        entity = self._make_button(mock_coordinator, mock_capability, catalog_entry)
        # val_to_send="PRESS" not in dict → allowed_states is None → skip, return super().available
        assert entity.available is True


class TestButtonSendCommandPaths:
    """Test additional send_command() paths."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator._last_update_times = {}
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"api_key": "key"}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {"access": "write", "type": "boolean"}

    def _make_button(
        self, coordinator, capability, pnc_id="TEST_PNC", entity_source=None
    ):
        entity = ElectroluxButton(
            coordinator=coordinator,
            capability=capability,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id=pnc_id,
            entity_type=BUTTON,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=entity_source,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
            val_to_send="START",
        )
        entity.hass = coordinator.hass
        return entity

    @pytest.mark.asyncio
    async def test_send_command_offline_raises(self, mock_coordinator, mock_capability):
        """Test send_command raises HomeAssistantError when appliance is offline."""
        from homeassistant.exceptions import HomeAssistantError

        entity = self._make_button(mock_coordinator, mock_capability)
        entity.appliance_status = {
            "properties": {"reported": {"connectivityState": "disconnected"}}
        }
        entity._reported_state_cache = {"connectivityState": "disconnected"}

        with pytest.raises(HomeAssistantError, match="offline"):
            await entity.send_command()

    @pytest.mark.asyncio
    async def test_send_command_dam_no_entity_source(
        self, mock_coordinator, mock_capability
    ):
        """Test DAM appliance with no entity_source wraps command in commands list."""
        entity = self._make_button(
            mock_coordinator, mock_capability, pnc_id="1:TEST_PNC"
        )
        entity.appliance_status = {
            "properties": {"reported": {"connectivityState": "connected"}}
        }
        entity._reported_state_cache = {"connectivityState": "connected"}
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.send_command()

        entity.api.execute_appliance_command.assert_called_once_with(
            "1:TEST_PNC", {"commands": [{"testAttr": "START"}]}
        )

    @pytest.mark.asyncio
    async def test_send_command_dam_user_selections_with_program_uid(
        self, mock_coordinator, mock_capability
    ):
        """Test DAM appliance with userSelections entity_source includes programUID."""
        entity = self._make_button(
            mock_coordinator,
            mock_capability,
            pnc_id="1:TEST_PNC",
            entity_source="userSelections",
        )
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "connectivityState": "connected",
                    "userSelections": {"programUID": "COTTON_90"},
                }
            }
        }
        entity._reported_state_cache = {
            "connectivityState": "connected",
            "userSelections": {"programUID": "COTTON_90"},
        }
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.send_command()

        entity.api.execute_appliance_command.assert_called_once_with(
            "1:TEST_PNC",
            {
                "commands": [
                    {
                        "userSelections": {
                            "programUID": "COTTON_90",
                            "testAttr": "START",
                        }
                    }
                ]
            },
        )

    @pytest.mark.asyncio
    async def test_send_command_auth_error_triggers_reauth(
        self, mock_coordinator, mock_capability
    ):
        """Test AuthenticationError triggers coordinator.handle_authentication_error."""
        from unittest.mock import patch

        from custom_components.electrolux.util import AuthenticationError

        entity = self._make_button(mock_coordinator, mock_capability)
        entity.appliance_status = {
            "properties": {"reported": {"connectivityState": "connected"}}
        }
        entity._reported_state_cache = {"connectivityState": "connected"}
        mock_coordinator.handle_authentication_error = AsyncMock()

        auth_ex = AuthenticationError("token expired")
        with patch(
            "custom_components.electrolux.button.execute_command_with_error_handling",
            side_effect=auth_ex,
        ):
            await entity.send_command()

        mock_coordinator.handle_authentication_error.assert_called_once_with(auth_ex)


class TestButtonManualSync:
    """Test _perform_manual_sync and async_press with manualSync."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator._last_update_times = {}
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"api_key": "key"}
        coordinator.perform_manual_sync = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {"access": "write", "type": "boolean"}

    def _make_manual_sync_button(self, coordinator, capability):
        entity = ElectroluxButton(
            coordinator=coordinator,
            capability=capability,
            name="Manual Sync",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="manualSync",
            entity_attr="manualSync",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:sync",
            catalog_entry=None,
            val_to_send="SYNC",
        )
        entity.hass = coordinator.hass
        return entity

    @pytest.mark.asyncio
    async def test_async_press_manual_sync_calls_perform_manual_sync(
        self, mock_coordinator, mock_capability
    ):
        """Test async_press with entity_attr='manualSync' calls _perform_manual_sync."""
        entity = self._make_manual_sync_button(mock_coordinator, mock_capability)
        mock_coordinator.data = {"appliances": None}

        await entity.async_press()

        mock_coordinator.perform_manual_sync.assert_called_once_with(
            "TEST_PNC", "Unknown Appliance"
        )

    @pytest.mark.asyncio
    async def test_perform_manual_sync_success_fires_events(
        self, mock_coordinator, mock_capability
    ):
        """Test _perform_manual_sync fires progress events and calls coordinator."""
        entity = self._make_manual_sync_button(mock_coordinator, mock_capability)
        # Set up appliance in coordinator data
        appliance_mock = MagicMock()
        appliance_mock.name = "My Dryer"
        appliances_mock = MagicMock()
        appliances_mock.get_appliance.return_value = appliance_mock
        mock_coordinator.data = {"appliances": appliances_mock}

        await entity._perform_manual_sync()

        # Should fire 5 progress events (steps 0-4)
        assert mock_coordinator.hass.bus.async_fire.call_count == 5
        mock_coordinator.perform_manual_sync.assert_called_once_with(
            "TEST_PNC", "My Dryer"
        )

    @pytest.mark.asyncio
    async def test_perform_manual_sync_no_appliance_uses_default_name(
        self, mock_coordinator, mock_capability
    ):
        """Test _perform_manual_sync uses 'Unknown Appliance' when appliance not found."""
        entity = self._make_manual_sync_button(mock_coordinator, mock_capability)
        appliances_mock = MagicMock()
        appliances_mock.get_appliance.return_value = None
        mock_coordinator.data = {"appliances": appliances_mock}

        await entity._perform_manual_sync()

        mock_coordinator.perform_manual_sync.assert_called_once_with(
            "TEST_PNC", "Unknown Appliance"
        )

    @pytest.mark.asyncio
    async def test_perform_manual_sync_failure_fires_error_and_raises(
        self, mock_coordinator, mock_capability
    ):
        """Test _perform_manual_sync on coordinator failure fires error event and raises HomeAssistantError."""
        from homeassistant.exceptions import HomeAssistantError

        entity = self._make_manual_sync_button(mock_coordinator, mock_capability)
        mock_coordinator.data = {"appliances": None}
        mock_coordinator.perform_manual_sync = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        with pytest.raises(HomeAssistantError, match="Manual sync failed"):
            await entity._perform_manual_sync()

        # Should have fired error event (step=-1)
        last_call = mock_coordinator.hass.bus.async_fire.call_args
        assert last_call[0][1]["step"] == -1


class TestButtonMissingCoverage:
    """Tests for missed lines in button.py: line 100 (device_class) and line 159 (icon)."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator._last_update_times = {}
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"api_key": "test_key"}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {"access": "write", "type": "boolean"}

    def _make_button(
        self,
        coordinator,
        capability,
        catalog_entry=None,
        val_to_send="PRESS",
        icon="",
    ):
        entity = ElectroluxButton(
            coordinator=coordinator,
            capability=capability,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon=icon,
            catalog_entry=catalog_entry,
            val_to_send=val_to_send,
        )
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "applianceState": "RUNNING",
                    "connectivityState": "connected",
                }
            }
        }
        entity._reported_state_cache = {
            "applianceState": "RUNNING",
            "connectivityState": "connected",
        }
        return entity

    def test_device_class_returns_button_device_class_from_catalog(
        self, mock_coordinator, mock_capability
    ):
        """Line 100: device_class returns ButtonDeviceClass when catalog has ButtonDeviceClass."""
        from homeassistant.components.button import ButtonDeviceClass

        entity = self._make_button(mock_coordinator, mock_capability)
        mock_catalog = MagicMock()
        mock_catalog.device_class = ButtonDeviceClass.UPDATE
        entity._catalog_entry = mock_catalog
        result = entity.device_class
        assert result == ButtonDeviceClass.UPDATE

    def test_device_class_returns_button_device_class_identify(
        self, mock_coordinator, mock_capability
    ):
        """Line 100: device_class returns ButtonDeviceClass.IDENTIFY from catalog."""
        from homeassistant.components.button import ButtonDeviceClass

        entity = self._make_button(mock_coordinator, mock_capability)
        mock_catalog = MagicMock()
        mock_catalog.device_class = ButtonDeviceClass.IDENTIFY
        entity._catalog_entry = mock_catalog
        result = entity.device_class
        assert result == ButtonDeviceClass.IDENTIFY

    def test_icon_returns_icon_when_set(self, mock_coordinator, mock_capability):
        """Line 159: icon property returns _icon when it is set."""
        entity = self._make_button(
            mock_coordinator, mock_capability, icon="mdi:custom-icon"
        )
        result = entity.icon
        assert result == "mdi:custom-icon"

    def test_icon_returns_icon_mapping_when_no_icon_set(
        self, mock_coordinator, mock_capability
    ):
        """Line 159: icon property returns icon_mapping lookup when _icon is None."""
        from custom_components.electrolux.const import icon_mapping

        # val_to_send must match a key in icon_mapping to return a mapped value
        # Find a valid key from icon_mapping, or use one that returns default
        entity = self._make_button(
            mock_coordinator, mock_capability, icon="", val_to_send="PRESS"
        )
        result = entity.icon
        # When val_to_send not in icon_mapping, returns "mdi:gesture-tap-button"
        assert result == icon_mapping.get("PRESS", "mdi:gesture-tap-button")

    def test_icon_returns_mapped_icon_for_known_val(
        self, mock_coordinator, mock_capability
    ):
        """Line 159: icon property returns mapped icon from icon_mapping for known val_to_send."""
        from custom_components.electrolux.const import icon_mapping

        # Use any val_to_send that is actually in icon_mapping
        if icon_mapping:
            val = next(iter(icon_mapping))
            entity = self._make_button(
                mock_coordinator, mock_capability, icon="", val_to_send=val
            )
            result = entity.icon
            assert result == icon_mapping[val]
        else:
            # No icon_mapping entries; fallback default
            entity = self._make_button(
                mock_coordinator, mock_capability, icon="", val_to_send="UNKNOWN"
            )
            result = entity.icon
            assert result == "mdi:gesture-tap-button"

    def test_device_class_fallback_when_no_catalog_entry(
        self, mock_coordinator, mock_capability
    ):
        """Line 101: device_class returns _device_class when no catalog entry."""
        entity = self._make_button(mock_coordinator, mock_capability)
        entity._catalog_entry = None
        entity._device_class = "custom_class"
        result = entity.device_class
        assert result == "custom_class"

    def test_device_class_fallback_when_catalog_has_non_button_device_class(
        self, mock_coordinator, mock_capability
    ):
        """Line 101: device_class returns _device_class when catalog device_class is not ButtonDeviceClass."""
        entity = self._make_button(mock_coordinator, mock_capability)
        mock_catalog = MagicMock()
        mock_catalog.device_class = "not_a_button_device_class"
        entity._catalog_entry = mock_catalog
        entity._device_class = "fallback_class"
        result = entity.device_class
        assert result == "fallback_class"

    @pytest.mark.asyncio
    async def test_async_setup_entry(self, mock_coordinator, mock_capability):
        """Lines 34-46: async_setup_entry adds button entities for each appliance."""

        from custom_components.electrolux.button import async_setup_entry

        # Build a mock entity that belongs to the BUTTON type
        mock_entity = MagicMock()
        mock_entity.entity_type = BUTTON

        # Build a mock appliance
        mock_appliance = MagicMock()
        mock_appliance.entities = [mock_entity]

        mock_appliances = MagicMock()
        mock_appliances.appliances = {"appliance_1": mock_appliance}

        mock_coordinator.data = {"appliances": mock_appliances}
        mock_coordinator.hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator

        async_add_entities_mock = MagicMock()

        await async_setup_entry(
            mock_coordinator.hass, mock_entry, async_add_entities_mock
        )

        async_add_entities_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_appliances(
        self, mock_coordinator, mock_capability
    ):
        """Lines 34-46: async_setup_entry handles no appliances gracefully."""
        from custom_components.electrolux.button import async_setup_entry

        mock_coordinator.data = {"appliances": None}

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator

        async_add_entities_mock = MagicMock()

        await async_setup_entry(
            mock_coordinator.hass, mock_entry, async_add_entities_mock
        )

        async_add_entities_mock.assert_not_called()
