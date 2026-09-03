"""Test button platform for Electrolux."""

from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.electrolux.button import ElectroluxButton
from custom_components.electrolux.const import BUTTON
from custom_components.electrolux.execute_command_states import (
    DRYER_EXECUTE_STATES,
    WASHER_EXECUTE_STATES,
    execute_phase_states_from_capabilities,
    execute_states_from_capabilities,
)


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
        coordinator.api = MagicMock()
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
        button_entity.appliance_status = {"properties": {"reported": {"remoteControl": "ENABLED"}}}
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
        assert button_entity.available is True  # Should be available even with remote control disabled

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
        button_entity.appliance_status = {"properties": {"reported": {"remoteControl": "ENABLED", "testAttr": True}}}

        # Mock the API call
        button_entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await button_entity.async_press()

        # Verify command was sent
        button_entity.api.execute_appliance_command.assert_called_once_with("TEST_PNC", {"testAttr": "PRESS"})

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
            "TEST_PNC", {"userSelections": {"testAttr": "PRESS"}}
        )

    @pytest.mark.asyncio
    async def test_press_api_failure(self, button_entity):
        """Test button press when API call fails."""
        # Set remote control enabled
        button_entity.appliance_status = {"properties": {"reported": {"remoteControl": "ENABLED", "testAttr": True}}}

        # Mock the API call to raise an exception
        button_entity.api.execute_appliance_command = AsyncMock(side_effect=Exception("API failure"))

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
        entity.appliance_status = {"properties": {"reported": {"remoteControl": "ENABLED"}}}

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
        entity.appliance_status = {"properties": {"reported": {"remoteControl": "ENABLED", "testAttr": True}}}

        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.async_press()

        entity.api.execute_appliance_command.assert_called_once_with("TEST_PNC", {"testAttr": "PRESS"})

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
        entity = self._make_entity(mock_coordinator, mock_capability, "someAttr", None, "GO")
        uid = entity.unique_id
        assert "someattr" in uid
        assert "GO" in uid
        assert "root" in uid
        assert "MY_PNC" in uid

    def test_unique_id_fppn_prefix_stripped(self, mock_coordinator, mock_capability):
        """Test fppn_ prefix is stripped from entity_attr in unique_id."""
        entity = self._make_entity(mock_coordinator, mock_capability, "fppn_cleaningCycle", None, "START")
        uid = entity.unique_id
        assert "cleaningcycle" in uid
        assert "fppn_" not in uid

    def test_unique_id_fppn_no_underscore_stripped(self, mock_coordinator, mock_capability):
        """Test fppn prefix without underscore is stripped."""
        entity = self._make_entity(mock_coordinator, mock_capability, "fppnSomething", None, "ON")
        uid = entity.unique_id
        assert "fppn" not in uid
        assert "something" in uid

    def test_unique_id_with_entity_source(self, mock_coordinator, mock_capability):
        """Test unique_id includes entity_source."""
        entity = self._make_entity(mock_coordinator, mock_capability, "action", "oven", "START")
        assert "oven" in entity.unique_id

    def test_unique_id_empty_api_key(self, mock_coordinator, mock_capability):
        """Test unique_id with missing api_key uses 'unknown' hash placeholder."""
        mock_coordinator.config_entry.data = {}
        entity = self._make_entity(mock_coordinator, mock_capability, "action", None, "START")
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

    def test_name_with_catalog_entry_appliance_found(self, mock_coordinator, mock_capability):
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

    def test_name_with_catalog_entry_no_appliance(self, mock_coordinator, mock_capability):
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

    def test_name_last_word_matches_val_to_send_no_suffix(self, mock_coordinator, mock_capability):
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

    def test_available_when_states_key_not_in_dict(self, mock_coordinator, mock_capability):
        """Test available when val_to_send not in available_when_states dict → falls through to super."""
        from custom_components.electrolux.model import ElectroluxDevice

        catalog_entry = ElectroluxDevice(
            capability_info=mock_capability,
            available_when_states={"OTHER_VAL": ["RUNNING"]},
        )
        entity = self._make_button(mock_coordinator, mock_capability, catalog_entry)
        # val_to_send="PRESS" not in dict → allowed_states is None → skip, return super().available
        assert entity.available is True


# Trimmed from a live TD-916900511 (AEG dryer) /info response. Note that
# IDLE accepts ON, not START, which is what DRYER_EXECUTE_STATES claims.
DRYER_TRIGGERS = {
    "applianceState": {
        "access": "read",
        "triggers": [
            {
                "action": {"executeCommand": {"values": {"PAUSE": {}}}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "DELAYED_START",
                    "operator": "eq",
                },
            },
            {
                "action": {"executeCommand": {"values": {"ON": {}}}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "IDLE",
                    "operator": "eq",
                },
            },
            {
                "action": {"executeCommand": {"values": {"RESUME": {}, "STOPRESET": {}}}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "PAUSED",
                    "operator": "eq",
                },
            },
            {
                "action": {"executeCommand": {"values": {"START": {}}}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "READY_TO_START",
                    "operator": "eq",
                },
            },
            {
                "action": {"executeCommand": {"values": {"PAUSE": {}}}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "RUNNING",
                    "operator": "eq",
                },
            },
            {
                "action": {"executeCommand": {"values": {"STOPRESET": {}}}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "END_OF_CYCLE",
                    "operator": "eq",
                },
            },
            # Disabled actions carry no values and must be ignored.
            {
                "action": {"executeCommand": {"disabled": True}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "END_OF_CYCLE",
                    "operator": "eq",
                },
            },
            {
                "action": {"executeCommand": {"disabled": False}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "END_OF_CYCLE",
                    "operator": "ne",
                },
            },
        ],
    }
}


class TestExecuteStatesFromCapabilities:
    """Test deriving executeCommand rules from an appliance's own triggers."""

    def test_derives_state_machine_from_triggers(self):
        """Every trigger becomes a command with the states that accept it."""
        assert execute_states_from_capabilities(DRYER_TRIGGERS) == {
            "PAUSE": ["DELAYED_START", "RUNNING"],
            "ON": ["IDLE"],
            "RESUME": ["PAUSED"],
            "STOPRESET": ["PAUSED", "END_OF_CYCLE"],
            "START": ["READY_TO_START"],
        }

    def test_start_is_not_valid_in_idle_on_this_dryer(self):
        """Regression: DRYER_EXECUTE_STATES allows START in IDLE, this model does not."""
        derived = execute_states_from_capabilities(DRYER_TRIGGERS)
        assert derived is not None
        assert "IDLE" not in derived["START"]
        assert "IDLE" in DRYER_EXECUTE_STATES["START"]

    @pytest.mark.parametrize(
        "capabilities",
        [
            None,
            {},
            {"applianceState": {"access": "read"}},
            {"applianceState": {"triggers": []}},
            "not a dict",
        ],
        ids=["none", "empty", "no-triggers-key", "empty-triggers", "wrong-type"],
    )
    def test_returns_none_without_usable_triggers(self, capabilities):
        """Nothing to derive means the caller falls back to the catalog table."""
        assert execute_states_from_capabilities(capabilities) is None

    @pytest.mark.parametrize(
        "trigger",
        [
            {"action": {"executeCommand": {"values": {"START": {}}}}},
            {
                "action": {"executeCommand": {"values": {"START": {}}}},
                "condition": {
                    "operand_1": {"operand_1": "value"},
                    "operand_2": "RUNNING",
                    "operator": "eq",
                },
            },
            {
                "action": {"executeCommand": {"values": {"START": {}}}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "RUNNING",
                    "operator": "ne",
                },
            },
            {
                "action": {"endOfCycleSound": {"access": "read"}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "RUNNING",
                    "operator": "eq",
                },
            },
            {
                "action": {"executeCommand": {"values": {"START": {}}}},
                "condition": "RUNNING",
            },
            {
                "action": {"executeCommand": {"values": {"START": {}}}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": {"operand_1": "value"},
                    "operator": "eq",
                },
            },
            {
                "action": "START",
                "condition": {
                    "operand_1": "value",
                    "operand_2": "RUNNING",
                    "operator": "eq",
                },
            },
            {
                "action": {"executeCommand": "START"},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "RUNNING",
                    "operator": "eq",
                },
            },
            {
                "action": {"executeCommand": {"values": ["START"]}},
                "condition": {
                    "operand_1": "value",
                    "operand_2": "RUNNING",
                    "operator": "eq",
                },
            },
            "not a dict",
        ],
        ids=[
            "no-condition",
            "compound-operand",
            "ne-operator",
            "other-action",
            "condition-not-a-dict",
            "state-not-a-string",
            "action-not-a-dict",
            "command-not-a-dict",
            "values-not-a-dict",
            "wrong-type",
        ],
    )
    def test_skips_triggers_it_cannot_read(self, trigger):
        """Only simple equality conditions on executeCommand values are used."""
        caps = {"applianceState": {"triggers": [trigger]}}
        assert execute_states_from_capabilities(caps) is None


# Mirrors the real SO-944035035_01 structure (samples/SO-944035035_01.json):
# the structured oven publishes TWO independent applianceState machines and the
# reported values diverge (root OFF while the cavity is READY_TO_START).
SO_ROOT_APPLIANCE_STATE = {
    "values": {"ALARM": {}, "OFF": {}, "RUNNING": {}},
    "triggers": [],
}
SO_UPPER_OVEN_APPLIANCE_STATE = {
    "values": {
        "ALARM": {},
        "DELAYED_START": {},
        "END_OF_CYCLE": {},
        "IDLE": {},
        "OFF": {},
        "PAUSED": {},
        "READY_TO_START": {},
        "RUNNING": {},
    },
    "triggers": [
        {
            "condition": {"operand_1": "value", "operand_2": "RUNNING", "operator": "eq"},
            "action": {"executeCommand": {"values": {"STOPRESET": {}}}},
        },
        {
            "condition": {"operand_1": "value", "operand_2": "PAUSED", "operator": "eq"},
            "action": {"executeCommand": {"values": {"RESUME": {}, "STOPRESET": {}}}},
        },
        {
            "condition": {"operand_1": "value", "operand_2": "READY_TO_START", "operator": "eq"},
            "action": {"executeCommand": {"values": {"START": {}}}},
        },
    ],
}
SO_CAPABILITIES = {
    "applianceState": SO_ROOT_APPLIANCE_STATE,
    "upperOven/applianceState": SO_UPPER_OVEN_APPLIANCE_STATE,
}


class TestSourceScopedStateGating:
    """Source-scoped buttons must be gated by their own state machine only."""

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

    def _make_button(self, coordinator, entity_source, val_to_send, capabilities, reported):
        """Build an executeCommand button with a given source and reported payload."""
        from custom_components.electrolux.model import ElectroluxDevice

        appliance = MagicMock()
        appliance.data.capabilities = capabilities
        appliances = MagicMock()
        appliances.get_appliance.return_value = appliance
        coordinator.data = {"appliances": appliances}

        entity = ElectroluxButton(
            coordinator=coordinator,
            capability={"access": "write", "type": "boolean"},
            name="Oven",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="execute_command",
            entity_attr="executeCommand",
            entity_source=entity_source,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=ElectroluxDevice(
                capability_info={"access": "write"},
                available_when_states={"START": ["OFF"], "STOPRESET": ["RUNNING"]},
            ),
            val_to_send=val_to_send,
        )
        reported = {"connectivityState": "connected", **reported}
        entity.appliance_status = {"properties": {"reported": reported}}
        entity._reported_state_cache = reported
        return entity

    def test_scoped_rules_use_scoped_state_flat_layout(self, mock_coordinator):
        """STOPRESET follows upperOven/applianceState, not the root machine."""
        # Root says OFF (START-able), cavity says RUNNING (STOPRESET-able).
        entity = self._make_button(
            mock_coordinator,
            "upperOven",
            "STOPRESET",
            SO_CAPABILITIES,
            {"applianceState": "OFF", "upperOven/applianceState": "RUNNING"},
        )
        assert entity.available is True

    def test_scoped_rules_use_scoped_state_nested_layout(self, mock_coordinator):
        """The nested upperOven -> applianceState layout is also resolved."""
        entity = self._make_button(
            mock_coordinator,
            "upperOven",
            "STOPRESET",
            SO_CAPABILITIES,
            {"applianceState": "OFF", "upperOven": {"applianceState": "RUNNING"}},
        )
        assert entity.available is True

    def test_scoped_button_blocked_by_its_own_machine(self, mock_coordinator):
        """Cavity is OFF: STOPRESET is invalid there, even though root allows it."""
        entity = self._make_button(
            mock_coordinator,
            "upperOven",
            "STOPRESET",
            SO_CAPABILITIES,
            {"applianceState": "OFF", "upperOven/applianceState": "OFF"},
        )
        assert entity.available is False

    def test_root_state_change_does_not_flip_scoped_button(self, mock_coordinator):
        """Only the cavity's own state may gate the cavity's buttons."""
        for root_state in ("OFF", "RUNNING", "ALARM"):
            entity = self._make_button(
                mock_coordinator,
                "upperOven",
                "START",
                SO_CAPABILITIES,
                {"applianceState": root_state, "upperOven/applianceState": "READY_TO_START"},
            )
            assert entity.available is True, root_state

    def test_scoped_button_without_scoped_capability_falls_back_to_table(self, mock_coordinator):
        """No upperOven/applianceState capability: the catalog table applies.

        The table is evaluated against the scoped state, never the root machine.
        """
        caps = {"applianceState": SO_ROOT_APPLIANCE_STATE}
        entity = self._make_button(
            mock_coordinator,
            "upperOven",
            "START",
            caps,
            {"applianceState": "RUNNING", "upperOven/applianceState": "OFF"},
        )
        # Root RUNNING would have blocked START via the root machine; the
        # scoped state OFF matches the table's START rule instead.
        assert entity.available is True

    def test_scoped_derivation_ignores_root_appliance_state_capability(self):
        """With entity_source set, the root machine must not be derived."""
        assert execute_states_from_capabilities(SO_CAPABILITIES, entity_source="upperOven") == {
            "STOPRESET": ["RUNNING", "PAUSED"],
            "RESUME": ["PAUSED"],
            "START": ["READY_TO_START"],
        }

    def test_scoped_derivation_returns_none_without_scoped_capability(self):
        """Missing scoped capability: caller falls back to the catalog table."""
        caps = {"applianceState": {"triggers": DRYER_TRIGGERS["applianceState"]["triggers"]}}
        assert execute_states_from_capabilities(caps, entity_source="upperOven") is None

    def test_missing_current_state_fails_open(self, mock_coordinator):
        """A partial payload must not hide every rule-covered button."""
        entity = self._make_button(
            mock_coordinator,
            None,
            "START",
            DRYER_TRIGGERS,
            {},  # no applianceState reported at all
        )
        assert entity.available is True

    def test_cache_invalidates_when_capabilities_object_changes(self, mock_coordinator):
        """A new capabilities payload must refresh the rules, even if the old
        object is garbage-collected and its id() gets recycled."""
        entity = self._make_button(
            mock_coordinator,
            None,
            "START",
            DRYER_TRIGGERS,
            {"applianceState": "READY_TO_START"},
        )
        assert entity.available is True

        # Replace capabilities with a payload publishing no triggers: the rules
        # must refresh to the catalog table, where START is only valid in OFF.
        appliance = MagicMock()
        appliance.data.capabilities = {
            "applianceState": {
                "values": {"READY_TO_START": {}, "OFF": {}},
                "triggers": [],
            }
        }
        appliances = MagicMock()
        appliances.get_appliance.return_value = appliance
        mock_coordinator.data = {"appliances": appliances}

        # The appliance moved to OFF: fresh rules (catalog table) allow START
        # there, while the stale dryer-derived rules (START only in
        # READY_TO_START) would keep the button disabled.
        reported = {"applianceState": "OFF", "connectivityState": "connected"}
        entity.appliance_status = {"properties": {"reported": reported}}
        entity._reported_state_cache = reported

        assert entity._execute_states == {"START": ["OFF"], "STOPRESET": ["RUNNING"]}
        assert entity.available is True


class TestRealSampleWM914505603:
    """Derive the washer rules from issue #188's real diagnostics sample.

    The AEG 9000 LR956SY6C (WM-914505603_03) publishes a machine identical to
    WASHER_EXECUTE_STATES plus ON in IDLE, which the catalog table omits — the
    runtime derivation must pick it up. It also ships trigger shapes the
    parser must ignore: compound ``or`` conditions, a ``ne`` operator and
    non-executeCommand actions.

    The applianceState node is embedded verbatim: samples/ is gitignored, so
    the committed test must not depend on the file being present. A companion
    test runs against the full local sample when it exists, keeping the two
    in sync.
    """

    @staticmethod
    def _local_sample_capabilities():
        """Return the full capabilities from the local sample, if present."""
        import json
        from pathlib import Path

        path = Path(__file__).parent.parent / "samples" / "WM-914505603_03.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        appliance = next(iter(data["data"]["appliances_detail"].values()))
        return appliance["capabilities"]

    WM_APPLIANCE_STATE: ClassVar[dict] = {
        "access": "read",
        "triggers": [
            {
                "action": {"executeCommand": {"access": "write", "values": {"PAUSE": {}}}},
                "condition": {"operand_1": "value", "operand_2": "DELAYED_START", "operator": "eq"},
            },
            {
                "action": {"executeCommand": {"access": "write", "values": {"ON": {}}}},
                "condition": {"operand_1": "value", "operand_2": "IDLE", "operator": "eq"},
            },
            {
                "action": {"executeCommand": {"access": "write", "values": {"RESUME": {}, "STOPRESET": {}}}},
                "condition": {"operand_1": "value", "operand_2": "PAUSED", "operator": "eq"},
            },
            {
                "action": {"executeCommand": {"access": "write", "values": {"START": {}}}},
                "condition": {"operand_1": "value", "operand_2": "READY_TO_START", "operator": "eq"},
            },
            {
                "action": {"executeCommand": {"access": "write", "values": {"PAUSE": {}}}},
                "condition": {"operand_1": "value", "operand_2": "RUNNING", "operator": "eq"},
            },
            {
                "action": {"executeCommand": {"access": "write", "values": {"STOPRESET": {}}}},
                "condition": {"operand_1": "value", "operand_2": "END_OF_CYCLE", "operator": "eq"},
            },
            {
                "action": {"executeCommand": {"disabled": True}},
                "condition": {"operand_1": "value", "operand_2": "END_OF_CYCLE", "operator": "eq"},
            },
            {
                "action": {"executeCommand": {"disabled": False}},
                "condition": {"operand_1": "value", "operand_2": "END_OF_CYCLE", "operator": "ne"},
            },
            {
                "action": {
                    "defaultExtraRinse": {"access": "read"},
                    "endOfCycleSound": {"access": "read"},
                    "waterHardness": {"access": "read"},
                    "waterSoftenerMode": {"access": "read"},
                },
                "condition": {
                    "operand_1": {"operand_1": "value", "operand_2": "RUNNING", "operator": "eq"},
                    "operand_2": {"operand_1": "value", "operand_2": "DELAYED_START", "operator": "eq"},
                    "operator": "or",
                },
            },
            {
                "action": {
                    "defaultExtraRinse": {"access": "default"},
                    "endOfCycleSound": {"access": "default"},
                    "waterHardness": {"access": "default"},
                    "waterSoftenerMode": {"access": "default"},
                },
                "condition": {
                    "operand_1": {"operand_1": "value", "operand_2": "READY_TO_START", "operator": "eq"},
                    "operand_2": {"operand_1": "value", "operand_2": "IDLE", "operator": "eq"},
                    "operator": "or",
                },
            },
            {
                "action": {
                    "defaultExtraRinse": {"access": "read"},
                    "endOfCycleSound": {"access": "read"},
                    "waterHardness": {"access": "read"},
                    "waterSoftenerMode": {"access": "read"},
                },
                "condition": {
                    "operand_1": {"operand_1": "value", "operand_2": "PAUSED", "operator": "eq"},
                    "operand_2": {"operand_1": "value", "operand_2": "END_OF_CYCLE", "operator": "eq"},
                    "operator": "or",
                },
            },
        ],
        "type": "string",
        "values": {
            "ALARM": {},
            "DELAYED_START": {},
            "END_OF_CYCLE": {},
            "IDLE": {},
            "OFF": {},
            "PAUSED": {},
            "READY_TO_START": {},
            "RUNNING": {},
        },
    }

    def _derived(self):
        return execute_states_from_capabilities({"applianceState": self.WM_APPLIANCE_STATE})

    def test_derives_the_published_state_machine(self):
        assert self._derived() == {
            "PAUSE": ["DELAYED_START", "RUNNING"],
            "ON": ["IDLE"],
            "RESUME": ["PAUSED"],
            "STOPRESET": ["PAUSED", "END_OF_CYCLE"],
            "START": ["READY_TO_START"],
        }

    def test_on_gated_to_idle_although_catalog_table_has_no_on_entry(self):
        """The catalog leaves ON unrestricted; the appliance does not."""
        derived = self._derived()
        assert derived is not None
        assert "ON" in derived
        assert "ON" not in WASHER_EXECUTE_STATES

    def test_sample_ships_trigger_shapes_the_parser_must_skip(self):
        """The real sample really does contain or/ne/disabled triggers."""
        triggers = self.WM_APPLIANCE_STATE["triggers"]
        assert any(isinstance(t["condition"].get("operand_1"), dict) for t in triggers)
        assert any(t["condition"].get("operator") == "or" for t in triggers)
        assert any(t["condition"].get("operator") == "ne" for t in triggers)
        assert any(
            isinstance(t.get("action"), dict)
            and "executeCommand" in t["action"]
            and "values" not in t["action"]["executeCommand"]
            for t in triggers
        )

    def test_local_sample_matches_embedded_copy(self):
        """Keep the embedded node in sync with the local diagnostics sample."""
        caps = self._local_sample_capabilities()
        if caps is None:
            pytest.skip("samples/WM-914505603_03.json not present (gitignored)")
        assert caps["applianceState"]["triggers"] == self.WM_APPLIANCE_STATE["triggers"]
        assert execute_states_from_capabilities(caps) == self._derived()


class TestButtonAvailabilityPrefersAppliance:
    """Test that button availability follows the appliance over the catalog."""

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

    def _make_button(self, coordinator, appliance_state, val_to_send, capabilities):
        """Build a dryer executeCommand button sitting in a given applianceState."""
        from custom_components.electrolux.model import ElectroluxDevice

        if capabilities is None:
            coordinator.data = None
        else:
            appliance = MagicMock()
            appliance.data.capabilities = capabilities
            appliances = MagicMock()
            appliances.get_appliance.return_value = appliance
            coordinator.data = {"appliances": appliances}

        entity = ElectroluxButton(
            coordinator=coordinator,
            capability={"access": "write", "type": "boolean"},
            name="Dries",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="execute_command",
            entity_attr="executeCommand",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=ElectroluxDevice(
                capability_info={"access": "write"},
                available_when_states=DRYER_EXECUTE_STATES,
            ),
            val_to_send=val_to_send,
        )
        reported = {
            "applianceState": appliance_state,
            "connectivityState": "connected",
        }
        entity.appliance_status = {"properties": {"reported": reported}}
        entity._reported_state_cache = reported
        return entity

    def test_start_hidden_in_idle_when_appliance_says_so(self, mock_coordinator):
        """The bug: the catalog allows START in IDLE, the appliance only accepts ON."""
        caps = DRYER_TRIGGERS
        entity = self._make_button(mock_coordinator, "IDLE", "START", caps)
        assert entity.available is False

    def test_on_offered_in_idle_although_catalog_omits_it(self, mock_coordinator):
        """DRYER_EXECUTE_STATES has no ON entry at all, the appliance does."""
        caps = DRYER_TRIGGERS
        entity = self._make_button(mock_coordinator, "IDLE", "ON", caps)
        assert entity.available is True

    def test_start_offered_in_ready_to_start(self, mock_coordinator):
        """The normal path still works."""
        caps = DRYER_TRIGGERS
        entity = self._make_button(mock_coordinator, "READY_TO_START", "START", caps)
        assert entity.available is True

    def test_falls_back_to_catalog_without_triggers(self, mock_coordinator):
        """An appliance publishing no triggers keeps the catalog behaviour."""
        entity = self._make_button(mock_coordinator, "IDLE", "START", {})
        assert entity.available is True

    def test_survives_coordinator_without_data(self, mock_coordinator):
        """available() is also called before the first refresh and after unload."""
        entity = self._make_button(mock_coordinator, "IDLE", "START", None)
        assert entity.available is True

    def test_survives_coordinator_without_appliances(self, mock_coordinator):
        """Coordinator has data but has not populated appliances yet."""
        entity = self._make_button(mock_coordinator, "IDLE", "START", DRYER_TRIGGERS)
        mock_coordinator.data = {"appliances": None}
        assert entity.available is True

    def test_survives_appliance_removed(self, mock_coordinator):
        """The appliance is gone from the coordinator but its entities still exist."""
        entity = self._make_button(mock_coordinator, "IDLE", "START", DRYER_TRIGGERS)
        mock_coordinator.data["appliances"].get_appliance.return_value = None
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

    def _make_button(self, coordinator, capability, pnc_id="TEST_PNC", entity_source=None):
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
        entity.appliance_status = {"properties": {"reported": {"connectivityState": "disconnected"}}}
        entity._reported_state_cache = {"connectivityState": "disconnected"}

        with pytest.raises(HomeAssistantError, match="offline"):
            await entity.send_command()

    @pytest.mark.asyncio
    async def test_send_command_dam_no_entity_source(self, mock_coordinator, mock_capability):
        """Test DAM appliance with no entity_source wraps command in commands list."""
        entity = self._make_button(mock_coordinator, mock_capability, pnc_id="1:TEST_PNC")
        entity.appliance_status = {"properties": {"reported": {"connectivityState": "connected"}}}
        entity._reported_state_cache = {"connectivityState": "connected"}
        entity.api = MagicMock()
        entity.api.execute_appliance_command = AsyncMock(return_value=True)

        await entity.send_command()

        entity.api.execute_appliance_command.assert_called_once_with(
            "1:TEST_PNC", {"commands": [{"testAttr": "START"}]}
        )

    @pytest.mark.asyncio
    async def test_send_command_dam_user_selections_with_program_uid(self, mock_coordinator, mock_capability):
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
    async def test_send_command_auth_error_triggers_reauth(self, mock_coordinator, mock_capability):
        """Test AuthenticationError triggers coordinator.handle_authentication_error."""
        from unittest.mock import patch

        from custom_components.electrolux.util import AuthenticationError

        entity = self._make_button(mock_coordinator, mock_capability)
        entity.appliance_status = {"properties": {"reported": {"connectivityState": "connected"}}}
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
    async def test_async_press_manual_sync_calls_perform_manual_sync(self, mock_coordinator, mock_capability):
        """Test async_press with entity_attr='manualSync' calls _perform_manual_sync."""
        entity = self._make_manual_sync_button(mock_coordinator, mock_capability)
        mock_coordinator.data = {"appliances": None}

        await entity.async_press()

        mock_coordinator.perform_manual_sync.assert_called_once_with("TEST_PNC", "Unknown Appliance")

    @pytest.mark.asyncio
    async def test_perform_manual_sync_success_fires_events(self, mock_coordinator, mock_capability):
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
        mock_coordinator.perform_manual_sync.assert_called_once_with("TEST_PNC", "My Dryer")

    @pytest.mark.asyncio
    async def test_perform_manual_sync_no_appliance_uses_default_name(self, mock_coordinator, mock_capability):
        """Test _perform_manual_sync uses 'Unknown Appliance' when appliance not found."""
        entity = self._make_manual_sync_button(mock_coordinator, mock_capability)
        appliances_mock = MagicMock()
        appliances_mock.get_appliance.return_value = None
        mock_coordinator.data = {"appliances": appliances_mock}

        await entity._perform_manual_sync()

        mock_coordinator.perform_manual_sync.assert_called_once_with("TEST_PNC", "Unknown Appliance")

    @pytest.mark.asyncio
    async def test_perform_manual_sync_failure_fires_error_and_raises(self, mock_coordinator, mock_capability):
        """Test _perform_manual_sync on coordinator failure fires error event and raises HomeAssistantError."""
        from homeassistant.exceptions import HomeAssistantError

        entity = self._make_manual_sync_button(mock_coordinator, mock_capability)
        mock_coordinator.data = {"appliances": None}
        mock_coordinator.perform_manual_sync = AsyncMock(side_effect=Exception("Connection failed"))

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

    def test_device_class_returns_button_device_class_from_catalog(self, mock_coordinator, mock_capability):
        """Line 100: device_class returns ButtonDeviceClass when catalog has ButtonDeviceClass."""
        from homeassistant.components.button import ButtonDeviceClass

        entity = self._make_button(mock_coordinator, mock_capability)
        mock_catalog = MagicMock()
        mock_catalog.device_class = ButtonDeviceClass.UPDATE
        entity._catalog_entry = mock_catalog
        result = entity.device_class
        assert result == ButtonDeviceClass.UPDATE

    def test_device_class_returns_button_device_class_identify(self, mock_coordinator, mock_capability):
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
        entity = self._make_button(mock_coordinator, mock_capability, icon="mdi:custom-icon")
        result = entity.icon
        assert result == "mdi:custom-icon"

    def test_icon_returns_icon_mapping_when_no_icon_set(self, mock_coordinator, mock_capability):
        """Line 159: icon property returns icon_mapping lookup when _icon is None."""
        from custom_components.electrolux.const import icon_mapping

        # val_to_send must match a key in icon_mapping to return a mapped value
        # Find a valid key from icon_mapping, or use one that returns default
        entity = self._make_button(mock_coordinator, mock_capability, icon="", val_to_send="PRESS")
        result = entity.icon
        # When val_to_send not in icon_mapping, returns "mdi:gesture-tap-button"
        assert result == icon_mapping.get("PRESS", "mdi:gesture-tap-button")

    def test_icon_returns_mapped_icon_for_known_val(self, mock_coordinator, mock_capability):
        """Line 159: icon property returns mapped icon from icon_mapping for known val_to_send."""
        from custom_components.electrolux.const import icon_mapping

        # Use any val_to_send that is actually in icon_mapping
        if icon_mapping:
            val = next(iter(icon_mapping))
            entity = self._make_button(mock_coordinator, mock_capability, icon="", val_to_send=val)
            result = entity.icon
            assert result == icon_mapping[val]
        else:
            # No icon_mapping entries; fallback default
            entity = self._make_button(mock_coordinator, mock_capability, icon="", val_to_send="UNKNOWN")
            result = entity.icon
            assert result == "mdi:gesture-tap-button"

    def test_device_class_fallback_when_no_catalog_entry(self, mock_coordinator, mock_capability):
        """Line 101: device_class returns _device_class when no catalog entry."""
        entity = self._make_button(mock_coordinator, mock_capability)
        entity._catalog_entry = None
        entity._device_class = "custom_class"
        result = entity.device_class
        assert result == "custom_class"

    def test_device_class_fallback_when_catalog_has_non_button_device_class(self, mock_coordinator, mock_capability):
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

        await async_setup_entry(mock_coordinator.hass, mock_entry, async_add_entities_mock)

        async_add_entities_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_appliances(self, mock_coordinator, mock_capability):
        """Lines 34-46: async_setup_entry handles no appliances gracefully."""
        from custom_components.electrolux.button import async_setup_entry

        mock_coordinator.data = {"appliances": None}

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator

        async_add_entities_mock = MagicMock()

        await async_setup_entry(mock_coordinator.hass, mock_entry, async_add_entities_mock)

        async_add_entities_mock.assert_not_called()


# ---------------------------------------------------------------------------
# cyclePhase gating dimension (issue #178)
# ---------------------------------------------------------------------------

# Trimmed verbatim from samples/new/TD-916900511_01.json (AEG TR969PB4C
# heat-pump dryer): the model publishes STOPRESET via a cyclePhase trigger,
# and applianceState never reports ANTICREASE.
TD_CYCLE_PHASE: dict = {
    "access": "read",
    "type": "string",
    "values": {
        "ANTICREASE": {},
        "COOL": {},
        "CYCLE_PHASE_HIDDEN": {"disabled": True},
        "DRY": {},
        "UNAVAILABLE": {},
    },
    "triggers": [
        {
            "action": {"executeCommand": {"access": "write", "values": {"STOPRESET": {}}}},
            "condition": {"operand_1": "value", "operand_2": "ANTICREASE", "operator": "eq"},
        }
    ],
}

# remoteControl on the same dryer publishes executeCommand triggers whose
# actions carry no command values — they must contribute no gating rules.
TD_REMOTE_CONTROL: dict = {
    "access": "read",
    "type": "string",
    "values": {"DISABLED": {}, "ENABLED": {}, "NOT_SAFETY_RELEVANT_ENABLED": {}, "TEMPORARY_LOCKED": {}},
    "triggers": [
        {
            "action": {"executeCommand": {"access": "write", "values": {}}},
            "condition": {"operand_1": "value", "operand_2": "ENABLED", "operator": "eq"},
        }
    ],
}

TD916900511_CAPABILITIES: dict = {
    **DRYER_TRIGGERS,
    "cyclePhase": TD_CYCLE_PHASE,
    "remoteControl": TD_REMOTE_CONTROL,
}


class TestCyclePhaseDimensionGating:
    """executeCommand gating must consider cyclePhase triggers (issue #178).

    The AEG TR969PB4C heat-pump dryer (TD-916900511) publishes STOPRESET via a
    ``cyclePhase`` trigger for ANTICREASE — a value ``applianceState`` never
    reports — so the Stop/Reset button stayed disabled during anti-crease.
    A command is available when ANY dimension that publishes a rule for it
    matches (OR across dimensions).
    """

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

    def _make_button(self, coordinator, val_to_send, capabilities, reported):
        """Build a root-level executeCommand button with the given payloads."""
        from custom_components.electrolux.model import ElectroluxDevice

        appliance = MagicMock()
        appliance.data.capabilities = capabilities
        appliances = MagicMock()
        appliances.get_appliance.return_value = appliance
        coordinator.data = {"appliances": appliances}

        entity = ElectroluxButton(
            coordinator=coordinator,
            capability={"access": "write", "type": "boolean"},
            name="Dryer",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="execute_command",
            entity_attr="executeCommand",
            entity_source=None,
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=ElectroluxDevice(
                capability_info={"access": "write"},
                available_when_states=DRYER_EXECUTE_STATES,
            ),
            val_to_send=val_to_send,
        )
        reported = {"connectivityState": "connected", **reported}
        entity.appliance_status = {"properties": {"reported": reported}}
        entity._reported_state_cache = reported
        return entity

    def test_phase_rules_derived_from_td916900511(self):
        """The dryer's cyclePhase trigger yields STOPRESET: [ANTICREASE]."""
        assert execute_phase_states_from_capabilities({"cyclePhase": TD_CYCLE_PHASE}) == {
            "STOPRESET": ["ANTICREASE"]
        }

    def test_remote_control_triggers_with_no_values_contribute_nothing(self):
        """The third trigger-publishing capability (remoteControl) has empty
        value sets — it must not create rules (tanarchytan's observation)."""
        assert (
            execute_phase_states_from_capabilities({"remoteControl": TD_REMOTE_CONTROL})
            is None
        )
        assert execute_states_from_capabilities({"remoteControl": TD_REMOTE_CONTROL}) is None

    def test_stopreset_available_during_anticrease(self, mock_coordinator):
        """THE issue #178 scenario: applianceState=RUNNING has no STOPRESET
        rule, but cyclePhase=ANTICREASE does — the button must be available."""
        entity = self._make_button(
            mock_coordinator,
            "STOPRESET",
            TD916900511_CAPABILITIES,
            {"applianceState": "RUNNING", "cyclePhase": "ANTICREASE"},
        )
        assert entity.available is True

    def test_stopreset_unavailable_when_both_dimensions_fail(self, mock_coordinator):
        """applianceState=IDLE (no STOPRESET) and cyclePhase=DRY (no STOPRESET)."""
        entity = self._make_button(
            mock_coordinator,
            "STOPRESET",
            TD916900511_CAPABILITIES,
            {"applianceState": "IDLE", "cyclePhase": "DRY"},
        )
        assert entity.available is False

    def test_stopreset_available_via_state_dimension(self, mock_coordinator):
        """applianceState=PAUSED allows STOPRESET on its own; the phase
        dimension must not be able to take that away."""
        entity = self._make_button(
            mock_coordinator,
            "STOPRESET",
            TD916900511_CAPABILITIES,
            {"applianceState": "PAUSED", "cyclePhase": "DRY"},
        )
        assert entity.available is True

    def test_missing_cycle_phase_fails_open(self, mock_coordinator):
        """A partial payload without cyclePhase must not hide rule-covered
        buttons: the unknown dimension counts as unrestricted."""
        entity = self._make_button(
            mock_coordinator,
            "STOPRESET",
            TD916900511_CAPABILITIES,
            {"applianceState": "IDLE"},
        )
        assert entity.available is True

    def test_model_without_phase_triggers_is_unchanged(self, mock_coordinator):
        """No cyclePhase capability → no phase rules → old behavior only.

        ANTICREASE in reported cyclePhase must NOT enable STOPRESET on a model
        that publishes no cyclePhase triggers.
        """
        entity = self._make_button(
            mock_coordinator,
            "STOPRESET",
            DRYER_TRIGGERS,
            {"applianceState": "IDLE", "cyclePhase": "ANTICREASE"},
        )
        assert entity.available is False

    def test_command_without_phase_rule_gated_by_state_only(self, mock_coordinator):
        """PAUSE has no cyclePhase rule; only the applianceState dimension
        gates it (RUNNING allows PAUSE, IDLE does not)."""
        running = self._make_button(
            mock_coordinator,
            "PAUSE",
            TD916900511_CAPABILITIES,
            {"applianceState": "RUNNING", "cyclePhase": "ANTICREASE"},
        )
        idle = self._make_button(
            mock_coordinator,
            "PAUSE",
            TD916900511_CAPABILITIES,
            {"applianceState": "IDLE", "cyclePhase": "ANTICREASE"},
        )
        assert running.available is True
        assert idle.available is False

    def test_scoped_phase_rules_use_scoped_cycle_phase(self, mock_coordinator):
        """A source-scoped button reads {source}/cyclePhase, mirroring the
        applianceState scoping."""
        from custom_components.electrolux.model import ElectroluxDevice

        appliance = MagicMock()
        appliance.data.capabilities = {
            "upperOven/cyclePhase": {
                "triggers": [
                    {
                        "action": {"executeCommand": {"values": {"STOPRESET": {}}}},
                        "condition": {
                            "operand_1": "value",
                            "operand_2": "ANTICREASE",
                            "operator": "eq",
                        },
                    }
                ]
            }
        }
        appliances = MagicMock()
        appliances.get_appliance.return_value = appliance
        mock_coordinator.data = {"appliances": appliances}

        entity = ElectroluxButton(
            coordinator=mock_coordinator,
            capability={"access": "write", "type": "boolean"},
            name="Oven",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=BUTTON,
            entity_name="execute_command",
            entity_attr="executeCommand",
            entity_source="upperOven",
            unit="",
            device_class="",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
            catalog_entry=ElectroluxDevice(
                capability_info={"access": "write"},
                available_when_states={"STOPRESET": ["RUNNING"]},
            ),
            val_to_send="STOPRESET",
        )
        reported = {
            "connectivityState": "connected",
            "applianceState": "OFF",
            "upperOven/applianceState": "OFF",
            "upperOven/cyclePhase": "ANTICREASE",
        }
        entity.appliance_status = {"properties": {"reported": reported}}
        entity._reported_state_cache = reported
        # Root and cavity applianceState machines both forbid STOPRESET; only
        # the cavity's cyclePhase dimension allows it.
        assert entity.available is True

    @staticmethod
    def _local_sample():
        """Return the local TD-916900511 sample, if present."""
        import json
        from pathlib import Path

        path = Path(__file__).parent.parent / "samples" / "new" / "TD-916900511_01.json"
        if not path.exists():
            return None
        # Scrubbed capabilities-only dump (as offered in issue #178).
        return json.loads(path.read_text())["capabilities"]

    def test_local_sample_ships_the_embedded_cycle_phase_triggers(self):
        """Keep the embedded node in sync with the local sample."""
        caps = self._local_sample()
        if caps is None:
            pytest.skip("samples/new/TD-916900511_01.json not present")
        assert caps["cyclePhase"]["triggers"] == TD_CYCLE_PHASE["triggers"]
        assert caps["cyclePhase"]["values"] == TD_CYCLE_PHASE["values"]

    def test_local_sample_end_to_end_anticrease(self, mock_coordinator):
        """Full end-to-end against the real diagnostics sample."""
        caps = self._local_sample()
        if caps is None:
            pytest.skip("samples/new/TD-916900511_01.json not present")

        # Derived rules from the full real capability set.
        assert execute_states_from_capabilities(caps) == {
            "PAUSE": ["DELAYED_START", "RUNNING"],
            "ON": ["IDLE"],
            "RESUME": ["PAUSED"],
            "STOPRESET": ["PAUSED", "END_OF_CYCLE"],
            "START": ["READY_TO_START"],
        }
        assert execute_phase_states_from_capabilities(caps) == {"STOPRESET": ["ANTICREASE"]}

        entity = self._make_button(
            mock_coordinator,
            "STOPRESET",
            caps,
            {"applianceState": "RUNNING", "cyclePhase": "ANTICREASE"},
        )
        assert entity.available is True
