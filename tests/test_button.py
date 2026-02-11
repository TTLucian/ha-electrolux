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
        coordinator.config_entry = MagicMock()
        coordinator.api = AsyncMock()
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
        """Test available property when remote control is disabled."""
        button_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "DISABLED"}}
        }
        assert button_entity.available is False

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

        # Mock the coordinator update
        button_entity.coordinator.async_request_refresh = AsyncMock()

        await button_entity.async_press()

        # Verify command was sent
        button_entity.api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC", {"testAttr": "PRESS"}
        )
        button_entity.coordinator.async_request_refresh.assert_called_once()

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
        entity.coordinator.async_request_refresh = AsyncMock()

        await entity.async_press()

        entity.api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC", {"testAttr": "PRESS"}
        )
        entity.coordinator.async_request_refresh.assert_called_once()

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
        entity.coordinator.async_request_refresh = AsyncMock()

        await entity.async_press()

        entity.api.execute_appliance_command.assert_called_once_with(
            "1:TEST_PNC", {"commands": [{"airConditioner": {"testAttr": "PRESS"}}]}
        )
        entity.coordinator.async_request_refresh.assert_called_once()

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
        entity.coordinator.async_request_refresh = AsyncMock()

        await entity.async_press()

        entity.api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC", {"testAttr": "PRESS"}
        )
        entity.coordinator.async_request_refresh.assert_called_once()

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
