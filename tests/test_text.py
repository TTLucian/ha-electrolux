"""Test text platform for Electrolux."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EntityCategory, Platform

from custom_components.electrolux.text import ElectroluxText

# Real dishwasher capabilities (verbatim excerpt of samples/DW-911473025_00.json).
# Program constraint dicts key their entries *namespaced* —
# "userSelections/glassCareOption" — which is what the #232 programUID gate has
# to match; see tests/test_program_level_key.py.
DW_CAPS = json.loads((Path(__file__).parent / "fixtures" / "dw_user_selections.json").read_text())["capabilities"]


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
        coordinator.api = MagicMock()
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
            entity_type=Platform.TEXT,
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
        entity.appliance_status = {"properties": {"reported": {"testAttr": "test value"}}}
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
            entity_type=Platform.TEXT,
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
        """Test name property no longer uses catalog friendly_name directly."""
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
            entity_type=Platform.TEXT,
            entity_name="test_text",
            entity_attr="testAttr",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=catalog_entry,
        )
        assert entity.name == "Original Name"

    def test_native_value_from_reported_state(self, text_entity):
        """Test native_value returns value from reported state."""
        assert text_entity.native_value == "test value"

    def test_native_value_converts_non_string_to_str(self, text_entity):
        """Test native_value converts non-string values (e.g., int) to str."""
        text_entity.extract_value = MagicMock(return_value=42)
        assert text_entity.native_value == "42"

    def test_native_value_none_when_no_data(self, mock_coordinator, mock_capability):
        """Test native_value returns None when no data available."""
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=Platform.TEXT,
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
            entity_type=Platform.TEXT,
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
            entity_type=Platform.TEXT,
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
        text_entity.appliance_status = {"properties": {"reported": {"remoteControl": "ENABLED"}}}
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
        assert text_entity.available is True  # Should be available even with remote control disabled

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
            "properties": {"reported": {"remoteControl": "ENABLED", "testAttr": "old value"}}
        }

        # Mock the API call
        text_entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await text_entity.async_set_value("new value")

        # Verify command was sent
        text_entity.api.execute_appliance_command.assert_called_once_with("TEST_PNC", {"testAttr": "new value"})

    @pytest.mark.asyncio
    async def test_set_value_with_entity_source(self, mock_coordinator, mock_capability):
        """Test set_value with entity source."""
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=Platform.TEXT,
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
            {"userSelections": {"programUID": "TEST", "testAttr": "new value"}},
        )

    @pytest.mark.asyncio
    async def test_set_value_api_failure(self, text_entity):
        """Test set_value when API call fails."""
        # Set remote control enabled
        text_entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED", "testAttr": "old value"}}
        }

        # Mock the API call to raise an exception
        text_entity.api.execute_appliance_command = AsyncMock(side_effect=Exception("API failure"))

        with pytest.raises(Exception, match="API failure"):
            await text_entity.async_set_value("new value")

        # Should still attempt to send command
        text_entity.api.execute_appliance_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_value_remote_control_disabled(self, text_entity):
        """Test set_value when remote control is disabled - command is sent optimistically to API."""
        text_entity.is_remote_control_enabled = MagicMock(return_value=False)

        # With optimistic sending, command should be sent to API (API will validate)
        # Mock the API to simulate successful call (API would reject if truly disabled)
        text_entity.api.execute_appliance_command = AsyncMock(return_value=None)
        await text_entity.async_set_value("new value")

        # Verify command was sent to API (not blocked client-side)
        text_entity.api.execute_appliance_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_value_with_dam_appliance(self, mock_coordinator, mock_capability):
        """Test set_value with DAM appliance (ID starts with '1:')."""
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="1:TEST_PNC",  # DAM appliance
            entity_type=Platform.TEXT,
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
        entity.appliance_status = {"properties": {"reported": {"remoteControl": "ENABLED"}}}

        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.async_set_value("new value")

        entity.api.execute_appliance_command.assert_called_once_with(
            "1:TEST_PNC", {"commands": [{"airConditioner": {"testAttr": "new value"}}]}
        )

    @pytest.mark.asyncio
    async def test_set_value_with_legacy_appliance(self, mock_coordinator, mock_capability):
        """Test set_value with legacy appliance (ID doesn't start with '1:')."""
        entity = ElectroluxText(
            coordinator=mock_coordinator,
            capability=mock_capability,
            name="Test Text",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",  # Legacy appliance
            entity_type=Platform.TEXT,
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
        entity.appliance_status = {"properties": {"reported": {"remoteControl": "ENABLED", "testAttr": "old value"}}}

        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.async_set_value("new value")

        entity.api.execute_appliance_command.assert_called_once_with("TEST_PNC", {"testAttr": "new value"})

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
            entity_type=Platform.TEXT,
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


class TestTextSetValueAdvancedPaths:
    """Tests for previously uncovered async_set_value paths in ElectroluxText."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator.api = MagicMock()
        coordinator._last_update_times = {}
        return coordinator

    @pytest.fixture
    def mock_capability(self):
        return {"access": "readwrite", "type": "string", "maxLength": 50}

    def _make_text(self, coordinator, capability, pnc_id="TEST_PNC", entity_source=None):
        entity = ElectroluxText(
            coordinator=coordinator,
            capability=capability,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id=pnc_id,
            entity_type=Platform.TEXT,
            entity_name="test",
            entity_attr="testAttr",
            entity_source=entity_source,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
        )
        entity.hass = coordinator.hass
        entity._reported_state_cache = {"connectivityState": "connected"}
        entity.appliance_status = {"properties": {"reported": {"connectivityState": "connected"}}}
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=True)
        return entity

    @pytest.mark.asyncio
    async def test_offline_raises_home_assistant_error(self, mock_coordinator, mock_capability):
        """Test async_set_value raises HomeAssistantError when appliance is offline."""
        from homeassistant.exceptions import HomeAssistantError

        entity = self._make_text(mock_coordinator, mock_capability)
        entity._reported_state_cache = {"connectivityState": "disconnected"}

        with pytest.raises(HomeAssistantError, match="offline"):
            await entity.async_set_value("hello")

    @pytest.mark.asyncio
    async def test_dam_user_selections_wraps_command(self, mock_coordinator, mock_capability):
        """Test DAM appliance with userSelections entity_source builds correct command."""
        entity = self._make_text(
            mock_coordinator,
            mock_capability,
            pnc_id="1:TEST_PNC",
            entity_source="userSelections",
        )
        entity._reported_state_cache = {
            "connectivityState": "connected",
            "userSelections": {"programUID": "MY_PROGRAM"},
        }
        entity.appliance_status = {
            "properties": {
                "reported": {
                    "connectivityState": "connected",
                    "userSelections": {"programUID": "MY_PROGRAM"},
                }
            }
        }

        await entity.async_set_value("hello")

        entity.api.execute_appliance_command.assert_called_once_with(  # type: ignore[union-attr]
            "1:TEST_PNC",
            {
                "commands": [
                    {
                        "userSelections": {
                            "programUID": "MY_PROGRAM",
                            "testAttr": "hello",
                        }
                    }
                ]
            },
        )

    @pytest.mark.asyncio
    async def test_dam_no_entity_source_wraps_command(self, mock_coordinator, mock_capability):
        """Test DAM appliance with no entity_source wraps command in commands list."""
        entity = self._make_text(mock_coordinator, mock_capability, pnc_id="1:TEST_PNC")

        await entity.async_set_value("hello")

        entity.api.execute_appliance_command.assert_called_once_with(  # type: ignore[union-attr]
            "1:TEST_PNC",
            {"commands": [{"testAttr": "hello"}]},
        )

    @pytest.mark.asyncio
    async def test_auth_error_handled_then_reraised(self, mock_coordinator, mock_capability):
        """Test AuthenticationError triggers coordinator.handle_authentication_error then is re-raised."""
        from unittest.mock import patch

        from custom_components.electrolux.util import AuthenticationError

        entity = self._make_text(mock_coordinator, mock_capability)
        mock_coordinator.handle_authentication_error = AsyncMock()
        auth_ex = AuthenticationError("token expired")

        with (
            patch(
                "custom_components.electrolux.text.execute_command_with_error_handling",
                side_effect=auth_ex,
            ),
            pytest.raises(AuthenticationError),
        ):
            await entity.async_set_value("hello")

        mock_coordinator.handle_authentication_error.assert_called_once_with(auth_ex)


# ---------------------------------------------------------------------------
# #232 — programUID gating for userSelections writes
# ---------------------------------------------------------------------------


class TestUserSelectionsProgramUidGate:
    """Only program-scoped keys are bundled with programUID (#232).

    ``caps`` below is a verbatim excerpt of samples/DW-911473025_00.json, where
    the program constraint dicts name their entries "userSelections/<option>";
    autoDoorOpener is listed by no program.  See tests/test_program_level_key.py.
    """

    @staticmethod
    def _coordinator_with(caps):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1_000_000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}
        mock_appliance = MagicMock()
        mock_appliance.data = MagicMock()
        mock_appliance.data.capabilities = caps
        mock_appliances = MagicMock()
        mock_appliances.get_appliance.return_value = mock_appliance
        coordinator.data = {"appliances": mock_appliances}
        return coordinator

    @staticmethod
    def _entity(coordinator, entity_attr, pnc_id="TEST_PNC", entity_source="userSelections"):
        # The api double is kept in a local and returned so the assertions read
        # off a real AsyncMock; going through ``entity.api`` would resolve the
        # declared ElectroluxApiClient type, where execute_appliance_command is a
        # plain method with no mock attributes.
        api = MagicMock()
        api.execute_appliance_command = AsyncMock(return_value=True)
        entity = ElectroluxText(
            coordinator=coordinator,
            capability={"access": "readwrite", "type": "string"},
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id=pnc_id,
            entity_type=Platform.TEXT,
            entity_name="test",
            entity_attr=entity_attr,
            entity_source=entity_source,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=None,
        )
        entity.api = api
        return entity, api

    @pytest.mark.asyncio
    async def test_appliance_level_key_omits_program_uid(self):
        """A key no program lists must not be bundled with programUID (#232)."""
        coordinator = self._coordinator_with(DW_CAPS)
        entity, api = self._entity(coordinator, "autoDoorOpener")
        entity.appliance_status = {"properties": {"reported": {"userSelections": {"programUID": "ECO"}}}}

        await entity.async_set_value("ON")

        api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC",
            {"userSelections": {"autoDoorOpener": "ON"}},
        )

    @pytest.mark.asyncio
    async def test_program_level_key_keeps_program_uid(self):
        """A real program option must keep programUID (#30 must not regress)."""
        coordinator = self._coordinator_with(DW_CAPS)
        entity, api = self._entity(coordinator, "xtraDryOption")
        entity.appliance_status = {"properties": {"reported": {"userSelections": {"programUID": "ECO"}}}}

        await entity.async_set_value("ON")

        api.execute_appliance_command.assert_called_once_with(
            "TEST_PNC",
            {"userSelections": {"programUID": "ECO", "xtraDryOption": "ON"}},
        )

    @pytest.mark.asyncio
    async def test_dam_appliance_level_key_omits_program_uid(self):
        """DAM writes follow the same gate."""
        coordinator = self._coordinator_with(DW_CAPS)
        entity, api = self._entity(coordinator, "autoDoorOpener", pnc_id="1:TEST_PNC")
        entity.reported_state = {"connectivityState": "connected"}
        entity.appliance_status = {"properties": {"reported": {"userSelections": {"programUID": "ECO"}}}}

        await entity.async_set_value("ON")

        api.execute_appliance_command.assert_called_once_with(
            "1:TEST_PNC",
            {"commands": [{"userSelections": {"autoDoorOpener": "ON"}}]},
        )
