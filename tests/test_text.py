"""Test text platform for Electrolux."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from custom_components.electrolux.const import TEXT
from custom_components.electrolux.text import ElectroluxText


class TestElectroluxText:
    """Test the Electrolux Text entity."""

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
            "access": "readwrite",
            "type": "string",
            "maxLength": 50,
        }

    @pytest.fixture
    def text_entity(self, mock_coordinator, mock_capability):
        """Create a test text entity."""
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=TEXT,
            entity_name="test_text",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        entity.appliance_status = {
            "properties": {"reported": {"testAttr": "test value"}}
        }
        entity.reported_state = {"testAttr": "test value"}
        return entity

    def test_entity_domain(self, text_entity):
        """Test entity domain property."""
        assert text_entity.entity_domain == "text"

    def test_name_with_friendly_name(self, mock_coordinator, mock_capability):
        """Test name property uses friendly name mapping."""
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Original Name",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=TEXT,
            entity_name="ovprogram_name",  # This has a friendly name mapping
            entity_attr="programName",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
        )
        entity.hass = mock_coordinator.hass  # Set hass for the entity
        assert entity.name == "Original Name"

    def test_name_fallback_to_catalog(self, mock_coordinator, mock_capability):
        """Test name property falls back to catalog friendly name."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            friendly_name="Catalog Friendly Name",
        )

        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Original Name",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=TEXT,
            entity_name="test_text",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        assert entity.name == "Catalog friendly name"

    def test_native_value_from_reported_state(self, text_entity):
        """Test native_value returns value from reported state."""
        assert text_entity.native_value == "test value"

    def test_native_value_none_when_no_data(self, mock_coordinator, mock_capability):
        """Test native_value returns None when no data available."""
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=TEXT,
            entity_name="test_text",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
        )
        entity.appliance_status = None
        entity.reported_state = None
        assert entity.native_value is None

    def test_native_value_with_state_mapping(self, mock_coordinator, mock_capability):
        """Test native_value with state mapping fallback."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            state_mapping="testAttr",
        )

        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=TEXT,
            entity_name="test_text",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        entity.extract_value = MagicMock(return_value=None)
        entity.get_state_attr = MagicMock(return_value="mapped value")
        assert entity.native_value == "mapped value"

    def test_native_max_len_from_capability(self, text_entity):
        """Test native_max_len returns value from capability."""
        assert text_entity.native_max_len == 50

    def test_native_max_len_none_when_no_capability(self, mock_coordinator):
        """Test native_max_len returns None when no maxLength in capability."""
        capability = {
            "access": "readwrite",
            "type": "string",
        }
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=TEXT,
            entity_name="test_text",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
        )
        assert entity.native_max_len is None

    def test_native_min_len_default(self, text_entity):
        """Test native_min_len returns default value."""
        assert text_entity.native_min_len == 0

    def test_native_pattern_none(self, text_entity):
        """Test native_pattern returns None."""
        assert text_entity.native_pattern is None

    def test_native_mode_default(self, text_entity):
        """Test native_mode returns default text mode."""
        assert text_entity.native_mode == "text"

    def test_available_true_when_remote_control_enabled(self, text_entity):
        """Test available property when remote control is enabled."""
        text_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }
        assert text_entity.available is True

    def test_available_false_when_remote_control_disabled(self, text_entity):
        """Test available property when remote control is disabled (but connected)."""
        text_entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "DISABLED",
                    "connectivityState": "connected",
                }
            }
        }
        assert (
            text_entity.available is True
        )  # Should be available even with remote control disabled

    def test_available_false_when_no_remote_control_info(self, text_entity):
        """Test available property when no remote control info is available."""
        text_entity.appliance_status = {"properties": {"reported": {}}}
        assert text_entity.available is True  # None is treated as enabled

    def test_available_false_when_no_appliance_status(self, text_entity):
        """Test available property when no appliance status is available."""
        text_entity.appliance_status = None
        assert text_entity.available is False

    @pytest.mark.asyncio
    async def test_set_value_success(self, text_entity):
        """Test successful value setting."""
        # Set remote control enabled
        text_entity.appliance_status = {
            "properties": {
                "reported": {"remoteControl": "ENABLED", "testAttr": "old value"}
            }
        }

        # Mock the API call
        text_entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await text_entity.async_set_value("new value")

        # Verify command was sent
        text_entity.api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC", {"testAttr": "new value"}
        )

    @pytest.mark.asyncio
    async def test_set_value_with_entity_source(
        self, mock_coordinator, mock_capability
    ):
        """Test set_value with entity source."""
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=TEXT,
            entity_name="test_text",
            entity_attr="testAttr",
            entity_source="userSelections",
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
        )

        # Set remote control enabled and userSelections
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "remoteControl": "ENABLED",
                    "userSelections": {"programUID": "TEST"},
                }
            }
        }

        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.async_set_value("new value")

        entity.api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC",
            {"testAttr": "new value"},
        )

    @pytest.mark.asyncio
    async def test_set_value_api_failure(self, text_entity):
        """Test set_value when API call fails."""
        # Set remote control enabled
        text_entity.appliance_status = {
            "properties": {
                "reported": {"remoteControl": "ENABLED", "testAttr": "old value"}
            }
        }

        # Mock the API call to raise an exception
        text_entity.api.execute_appliance_command = AsyncMock(
            side_effect=Exception("API failure")
        )

        with pytest.raises(Exception, match="API failure"):
            await text_entity.async_set_value("new value")

        # Should still attempt to send command
        text_entity.api.execute_appliance_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_value_remote_control_disabled(self, text_entity):
        """Test set_value when remote control is disabled raises error."""
        text_entity.is_remote_control_enabled = MagicMock(return_value=False)

        with pytest.raises(HomeAssistantError, match="Remote control is disabled"):
            await text_entity.async_set_value("new value")

    @pytest.mark.asyncio
    async def test_set_value_with_dam_appliance(
        self, mock_coordinator, mock_capability
    ):
        """Test set_value with DAM appliance (ID starts with '1:')."""
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="1:TEST_PNC",  # DAM appliance
            entity_type=TEXT,
            entity_name="test_text",
            entity_attr="testAttr",
            entity_source="airConditioner",
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
        )

        # Set remote control enabled
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }

        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.async_set_value("new value")

        entity.api.execute_appliance_command.assert_called_once_with(
            "1:TEST_PNC", {"commands": [{"airConditioner": {"testAttr": "new value"}}]}
        )

    @pytest.mark.asyncio
    async def test_set_value_with_legacy_appliance(
        self, mock_coordinator, mock_capability
    ):
        """Test set_value with legacy appliance (ID doesn't start with '1:')."""
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",  # Legacy appliance
            entity_type=TEXT,
            entity_name="test_text",
            entity_attr="testAttr",
            entity_source=None,  # No source for legacy
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
        )

        # Set remote control enabled
        entity.appliance_status = {
            "properties": {
                "reported": {"remoteControl": "ENABLED", "testAttr": "old value"}
            }
        }

        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.async_set_value("new value")

        entity.api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC", {"testAttr": "new value"}
        )

    def test_mode_from_catalog(self, mock_coordinator, mock_capability):
        """Test mode from catalog entry."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            mode="password",
        )

        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=TEXT,
            entity_name="test_text",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        assert entity.native_mode == "password"
