"""Tests for ElectroluxEntity core functionality.

Covers:
- async_setup_entry (entity platform): fPPN filtering, registry registration
- icon property: catalog, value map, capability values, default
- entity_registry_enabled_default: catalog override, DWYW hiding
- device_info: MAC extraction, DAM prefix, standard/long id formats
- extract_value: offline, constant, applianceInfo source, nested paths
- is_remote_control_enabled: all control states
- _evaluate_trigger_condition / _evaluate_operand: trigger logic
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import EntityCategory

from custom_components.electrolux.const import NUMBER, SENSOR
from custom_components.electrolux.number import ElectroluxNumber
from custom_components.electrolux.sensor import ElectroluxSensor

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def make_coordinator(reported: dict | None = None, pnc_id: str = "TEST_PNC"):
    """Build a minimal mock coordinator."""
    coordinator = MagicMock()
    coordinator.hass = MagicMock()
    coordinator.hass.loop = MagicMock()
    coordinator.hass.loop.time.return_value = 1_000_000.0
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.data = {"api_key": "test_api_key_1234567890abcdef"}
    coordinator._last_update_times = {}

    mock_appliances = MagicMock()
    mock_appliance = MagicMock()
    mock_appliance.state = {
        "properties": {"reported": reported or {}},
        "connectionState": "connected",
        "connectivityState": "connected",
    }
    mock_appliances.get_appliance.return_value = mock_appliance
    coordinator.data = {"appliances": mock_appliances}

    return coordinator, mock_appliance


def make_entity(
    entity_attr: str = "targetTemperatureC",
    entity_source: str | None = None,
    reported: dict | None = None,
    capability: dict | None = None,
    pnc_id: str = "TEST_APPLIANCE_123",
    use_sensor: bool = False,
) -> ElectroluxNumber | ElectroluxSensor:
    coordinator, _ = make_coordinator(reported=reported, pnc_id=pnc_id)
    cap = capability or {"access": "readwrite", "type": "number", "min": 0, "max": 100}
    cls = ElectroluxSensor if use_sensor else ElectroluxNumber
    entity_type = SENSOR if use_sensor else NUMBER
    entity = cls(
        coordinator=coordinator,
        name="Test Entity",
        config_entry=coordinator.config_entry,
        pnc_id=pnc_id,
        entity_type=entity_type,
        entity_name="test_entity",
        entity_attr=entity_attr,
        entity_source=entity_source,
        capability=cap,
        unit=None,
        device_class=None,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:thermometer",
    )
    entity.hass = coordinator.hass
    return entity


# ===========================================================================
# 1.  async_setup_entry  (entity.py lines 39-127)
# ===========================================================================


class TestEntityAsyncSetupEntry:
    """Test the entity-platform async_setup_entry in entity.py."""

    @pytest.mark.asyncio
    async def test_normal_entities_added(self):
        """Non-fPPN entities are added to HA."""
        from custom_components.electrolux.entity import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = "entity"
        mock_entity.entity_attr = "applianceState"
        mock_entity.unique_id = "uid-1"
        mock_entity.entity_domain = "sensor"
        mock_entity.entity_source = None
        mock_entity.pnc_id = "APPLIANCE_001"

        mock_appliance = MagicMock()
        mock_appliance.entities = [mock_entity]
        mock_appliance.brand = "Electrolux"
        mock_appliance.name = "Washer"

        mock_appliances = MagicMock()
        mock_appliances.appliances = {"APPLIANCE_001": mock_appliance}

        coordinator = MagicMock()
        coordinator.data = {"appliances": mock_appliances}

        entry = MagicMock()
        entry.runtime_data = coordinator

        hass = MagicMock()
        add_entities = MagicMock()

        with patch(
            "custom_components.electrolux.entity.er.async_get", return_value=MagicMock()
        ):
            await async_setup_entry(hass, entry, add_entities)

        add_entities.assert_called_once()
        added = add_entities.call_args[0][0]
        assert mock_entity in added

    @pytest.mark.asyncio
    async def test_fppn_entity_filtered_when_base_exists(self):
        """fPPN entity is skipped when a matching non-prefixed entity exists."""
        from custom_components.electrolux.entity import async_setup_entry

        base_entity = MagicMock()
        base_entity.entity_type = "entity"
        base_entity.entity_attr = "targetTemperatureC"
        base_entity.unique_id = "uid-base"
        base_entity.entity_domain = "number"
        base_entity.entity_source = None
        base_entity.pnc_id = "APPLIANCE_001"

        fppn_entity = MagicMock()
        fppn_entity.entity_type = "entity"
        fppn_entity.entity_attr = "fPPN_targetTemperatureC"
        fppn_entity.unique_id = "uid-fppn"
        fppn_entity.entity_domain = "number"
        fppn_entity.entity_source = None
        fppn_entity.pnc_id = "APPLIANCE_001"

        mock_appliance = MagicMock()
        mock_appliance.entities = [base_entity, fppn_entity]
        mock_appliance.brand = "Electrolux"
        mock_appliance.name = "Oven"

        mock_appliances = MagicMock()
        mock_appliances.appliances = {"APPLIANCE_001": mock_appliance}

        coordinator = MagicMock()
        coordinator.data = {"appliances": mock_appliances}

        entry = MagicMock()
        entry.runtime_data = coordinator

        add_entities = MagicMock()

        with patch(
            "custom_components.electrolux.entity.er.async_get", return_value=MagicMock()
        ):
            await async_setup_entry(MagicMock(), entry, add_entities)

        added = add_entities.call_args[0][0]
        # fPPN entity must NOT be added, base entity must be added
        assert base_entity in added
        assert fppn_entity not in added

    @pytest.mark.asyncio
    async def test_fppn_entity_kept_when_no_base(self):
        """fPPN entity is kept when no matching base entity exists."""
        from custom_components.electrolux.entity import async_setup_entry

        fppn_entity = MagicMock()
        fppn_entity.entity_type = "entity"
        fppn_entity.entity_attr = "fPPN_foodProbeTemperatureC"
        fppn_entity.unique_id = "uid-fppn"
        fppn_entity.entity_domain = "number"
        fppn_entity.entity_source = None
        fppn_entity.pnc_id = "APPLIANCE_001"

        mock_appliance = MagicMock()
        mock_appliance.entities = [fppn_entity]
        mock_appliance.brand = "Electrolux"
        mock_appliance.name = "Oven"

        mock_appliances = MagicMock()
        mock_appliances.appliances = {"APPLIANCE_001": mock_appliance}

        coordinator = MagicMock()
        coordinator.data = {"appliances": mock_appliances}

        entry = MagicMock()
        entry.runtime_data = coordinator

        add_entities = MagicMock()

        with patch(
            "custom_components.electrolux.entity.er.async_get", return_value=MagicMock()
        ):
            await async_setup_entry(MagicMock(), entry, add_entities)

        added = add_entities.call_args[0][0]
        assert fppn_entity in added

    @pytest.mark.asyncio
    async def test_no_appliances_no_entities_added(self):
        """When coordinator data has no appliances key, add_entities is not called."""
        from custom_components.electrolux.entity import async_setup_entry

        coordinator = MagicMock()
        coordinator.data = {}  # no "appliances"

        entry = MagicMock()
        entry.runtime_data = coordinator

        add_entities = MagicMock()
        await async_setup_entry(MagicMock(), entry, add_entities)

        add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_registry_exception_is_swallowed(self):
        """Registry errors don't abort entity addition."""
        from custom_components.electrolux.entity import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = "entity"
        mock_entity.entity_attr = "applianceState"
        mock_entity.unique_id = "uid-1"
        mock_entity.entity_domain = "sensor"
        mock_entity.entity_source = None
        mock_entity.pnc_id = "APPLIANCE_001"

        mock_appliance = MagicMock()
        mock_appliance.entities = [mock_entity]
        mock_appliance.brand = "Electrolux"
        mock_appliance.name = "Washer"

        mock_appliances = MagicMock()
        mock_appliances.appliances = {"APPLIANCE_001": mock_appliance}

        coordinator = MagicMock()
        coordinator.data = {"appliances": mock_appliances}

        entry = MagicMock()
        entry.runtime_data = coordinator

        add_entities = MagicMock()

        with patch(
            "custom_components.electrolux.entity.er.async_get",
            side_effect=Exception("Registry unavailable"),
        ):
            await async_setup_entry(MagicMock(), entry, add_entities)

        # Entities still added despite registry failure
        add_entities.assert_called_once()


# ===========================================================================
# 2.  icon property  (entity.py lines 460-484)
# ===========================================================================


class TestEntityIcon:
    """Test icon property for various scenarios."""

    def test_icon_from_catalog_entry_entity_icon(self):
        """Static icon from catalog entry takes priority."""
        entity = make_entity()
        catalog = MagicMock()
        catalog.entity_icon = "mdi:stove"
        catalog.entity_icons_value_map = None
        entity._catalog_entry = catalog
        # Patch extract_value so we skip runtime lookups
        entity.extract_value = MagicMock(return_value=None)

        assert entity.icon == "mdi:stove"

    def test_icon_from_catalog_value_map(self):
        """Value-map icon from catalog_entry used when entity_icon is absent."""
        entity = make_entity()
        # Use a spec that has entity_icons_value_map but NOT entity_icon
        # so that hasattr(catalog, 'entity_icon') is False
        catalog = MagicMock(spec=["entity_icons_value_map"])
        catalog.entity_icons_value_map = {"cool": "mdi:snowflake", "heat": "mdi:fire"}
        entity._catalog_entry = catalog
        entity.extract_value = MagicMock(return_value="cool")

        assert entity.icon == "mdi:snowflake"

    def test_icon_from_capability_values(self):
        """Icon from capability 'values' dict when no catalog entry."""
        entity = make_entity(
            capability={
                "access": "readwrite",
                "type": "string",
                "values": {"eco": {"icon": "mdi:leaf"}, "normal": {}},
            }
        )
        entity._catalog_entry = None
        entity.extract_value = MagicMock(return_value="eco")

        assert entity.icon == "mdi:leaf"

    def test_icon_fallback_to_default(self):
        """Falls back to _icon when no other icon applies."""
        entity = make_entity()
        entity._catalog_entry = None
        entity._icon = "mdi:thermometer"
        entity.extract_value = MagicMock(return_value=None)

        assert entity.icon == "mdi:thermometer"


# ===========================================================================
# 3.  entity_registry_enabled_default  (entity.py lines 487-503)
# ===========================================================================


class TestEntityRegistryEnabledDefault:
    """Test entity_registry_enabled_default property (uses ElectroluxSensor which doesn't override it)."""

    def test_catalog_entry_controls_default(self):
        """Catalog entry value overrides any other logic."""
        # Use ElectroluxSensor - ElectroluxNumber always returns True (overrides)
        entity = make_entity(use_sensor=True)
        catalog = MagicMock()
        catalog.entity_registry_enabled_default = False
        entity._catalog_entry = catalog

        assert entity.entity_registry_enabled_default is False

    def test_dwyw_entity_disabled_by_default(self):
        """Entities with 'dwyw' in path are hidden by default."""
        entity = make_entity(
            entity_attr="dwywDataToDryer",
            entity_source="userSelections",
            use_sensor=True,
        )
        entity._catalog_entry = None

        assert entity.entity_registry_enabled_default is False

    def test_normal_entity_enabled_by_default(self):
        """Regular entities default to enabled."""
        entity = make_entity(entity_attr="applianceState", use_sensor=True)
        entity._catalog_entry = None

        assert entity.entity_registry_enabled_default is True


# ===========================================================================
# 4.  device_info  (entity.py lines 517-596)
# ===========================================================================


class TestEntityDeviceInfo:
    """Test device_info property – MAC extraction, model formatting, DAM prefix."""

    def _setup_entity_with_appliance(
        self, pnc_id: str, appliance_type: str = "WM"
    ) -> ElectroluxNumber:
        """Create an entity with a properly configured appliance mock."""
        entity = make_entity(pnc_id=pnc_id)
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        mock_appliance.model = None
        mock_appliance.brand = "Electrolux"
        mock_appliance.name = "Test Machine"
        mock_appliance.appliance_type = appliance_type
        mock_appliance.serial_number = "SN12345"
        return entity

    def test_standard_pnc_mac_extraction(self):
        """MAC is correctly extracted from standard PNC format."""
        pnc_id = "916099949_00:31862190-443E07363DAB"
        entity = self._setup_entity_with_appliance(pnc_id, "WM")
        info = entity.device_info
        connections = info.get("connections", set())
        # Should contain a MAC entry
        assert any("44:3E:07:36:3D:AB" in str(v) for v in connections)

    def test_dam_prefix_stripped(self):
        """DAM '1:' prefix is stripped before processing."""
        pnc_id = "1:950022200_00:34509998-443E074D965A"
        entity = self._setup_entity_with_appliance(pnc_id, "DAM_AC")
        info = entity.device_info
        # Model should not contain "1:" prefix
        model = info.get("model", "")
        assert "1:950022200" not in (model or "")
        assert "950022200" in (model or "")

    def test_model_fallback_to_appliance_type(self):
        """When model is 'Unknown', appliance type is used as fallback."""
        pnc_id = "916099949_00:31862190-443E07363DAB"
        entity = self._setup_entity_with_appliance(pnc_id, "OV")
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        mock_appliance.model = "Unknown"
        info = entity.device_info
        # Should still produce a valid model string
        assert "model" in info
        assert info["model"]

    def test_identifiers_contain_pnc(self):
        """Identifiers tuple includes pnc_id."""
        pnc_id = "916099949_00:31862190-443E07363DAB"
        entity = self._setup_entity_with_appliance(pnc_id)
        info = entity.device_info
        ids = {v for _, v in info.get("identifiers", set())}  # type: ignore[union-attr]
        assert pnc_id in ids

    def test_long_id_no_mac(self):
        """Long numeric IDs (Muju-style) don't extract a MAC."""
        pnc_id = "956006959323006505087076"
        entity = self._setup_entity_with_appliance(pnc_id, "RF")
        info = entity.device_info
        # No connections key expected (or empty) for Muju style
        connections = info.get("connections", set())
        assert len(connections) == 0


# ===========================================================================
# 5.  extract_value  (entity.py lines 614-690)
# ===========================================================================


class TestExtractValue:
    """Test extract_value for all data-access paths."""

    def test_offline_returns_none_for_non_connectivity(self):
        """When disconnected, all non-connectivityState entities return None."""
        entity = make_entity(
            entity_attr="targetTemperatureC",
            reported={"connectivityState": "Disconnected"},
        )
        # Patch is_connected to simulate offline
        entity.is_connected = MagicMock(return_value=False)
        assert entity.extract_value() is None

    def test_connectivity_state_returns_value_when_offline(self):
        """connectivityState entity returns its value even when offline."""
        entity = make_entity(
            entity_attr="connectivityState",
            reported={"connectivityState": "Disconnected"},
        )
        entity.is_connected = MagicMock(return_value=False)
        # connectivityState is the exception – still returns value
        result = entity.extract_value()
        assert result == "Disconnected"

    def test_constant_capability_returns_default(self):
        """Capabilities with access=constant return 'default' field."""
        entity = make_entity(
            entity_attr="someConstant",
            capability={"access": "constant", "default": "fixed_value"},
        )
        entity.is_connected = MagicMock(return_value=True)
        assert entity.extract_value() == "fixed_value"

    def test_constant_capability_falls_back_to_value(self):
        """DAM constants use 'value' field when 'default' is absent."""
        entity = make_entity(
            entity_attr="someConstant",
            capability={"access": "constant", "value": "dam_constant"},
        )
        entity.is_connected = MagicMock(return_value=True)
        assert entity.extract_value() == "dam_constant"

    def test_top_level_reported_state(self):
        """Value is read from reported state at top level."""
        entity = make_entity(
            entity_attr="cyclePhase",
            reported={"cyclePhase": "Rinse"},
        )
        entity.is_connected = MagicMock(return_value=True)
        result = entity.extract_value()
        assert result == "Rinse"

    def test_nested_source_slash_path(self):
        """Value is read from nested source path (e.g. 'userSelections/spinSpeed')."""
        entity = make_entity(
            entity_attr="spinSpeed",
            entity_source="userSelections",
            reported={"userSelections": {"spinSpeed": 1200}},
        )
        entity.is_connected = MagicMock(return_value=True)
        result = entity.extract_value()
        assert result == 1200

    def test_deep_nested_source_multi_slash(self):
        """Value is read from deeply nested source with multiple '/' levels."""
        entity = make_entity(
            entity_attr="humidity",
            entity_source="climateStatus/environment",
            reported={"climateStatus": {"environment": {"humidity": 55}}},
        )
        entity.is_connected = MagicMock(return_value=True)
        result = entity.extract_value()
        assert result == 55

    def test_applianceinfo_source(self):
        """Value is read from applianceInfo sub-dict."""
        entity = make_entity(
            entity_attr="serialNumber",
            entity_source="applianceInfo",
        )
        entity.is_connected = MagicMock(return_value=True)
        entity.appliance_status = {
            "applianceInfo": {"serialNumber": "SN-ABC123"},
            "properties": {"reported": {}},
        }
        entity._reported_state_cache = {}
        result = entity.extract_value()
        assert result == "SN-ABC123"

    def test_returns_none_when_attr_missing(self):
        """Returns None when attr not found in reported state."""
        entity = make_entity(
            entity_attr="nonExistentAttr",
            reported={},
        )
        entity.is_connected = MagicMock(return_value=True)
        assert entity.extract_value() is None


# ===========================================================================
# 6.  is_remote_control_enabled  (entity.py lines 705-741)
# ===========================================================================


class TestIsRemoteControlEnabled:
    """Test is_remote_control_enabled() for all control states."""

    def test_no_appliance_status_returns_false(self):
        """Returns False when appliance_status is None/missing."""
        entity = make_entity()
        entity.appliance_status = None
        assert entity.is_remote_control_enabled() is False

    def test_remote_control_enabled_string(self):
        """REMOTE_CONTROL_ENABLED state returns True."""
        entity = make_entity()
        entity.appliance_status = {"remoteControl": "ENABLED"}
        assert entity.is_remote_control_enabled() is True

    def test_remote_control_disabled_string(self):
        """REMOTE_CONTROL_DISABLED state returns False."""
        entity = make_entity()
        entity.appliance_status = {"remoteControl": "DISABLED"}
        assert entity.is_remote_control_enabled() is False

    def test_remote_control_not_safety_relevant_enabled(self):
        """NOT_SAFETY_RELEVANT_ENABLED state returns True."""
        from custom_components.electrolux.const import (
            REMOTE_CONTROL_NOT_SAFETY_RELEVANT_ENABLED,
        )

        entity = make_entity()
        entity.appliance_status = {
            "remoteControl": REMOTE_CONTROL_NOT_SAFETY_RELEVANT_ENABLED
        }
        assert entity.is_remote_control_enabled() is True

    def test_remote_control_none_returns_true(self):
        """None remote_control (appliance doesn't report it) defaults to True."""
        entity = make_entity()
        entity.appliance_status = {"remoteControl": None}
        assert entity.is_remote_control_enabled() is True

    def test_remote_control_in_reported_nested(self):
        """Reads remoteControl from nested properties.reported path."""
        entity = make_entity()
        entity.appliance_status = {
            "properties": {"reported": {"remoteControl": "ENABLED"}}
        }
        assert entity.is_remote_control_enabled() is True

    def test_remote_control_not_present_returns_true(self):
        """When remoteControl key is absent (but status has other data), assume enabled."""
        entity = make_entity()
        # Non-empty dict without 'remoteControl' key
        entity.appliance_status = {"connectionState": "connected"}
        assert entity.is_remote_control_enabled() is True


# ===========================================================================
# 7.  _evaluate_trigger_condition / _evaluate_operand  (lines 1050-1143)
# ===========================================================================


class TestEvaluateTriggerCondition:
    """Test trigger condition evaluation logic."""

    @pytest.fixture
    def entity(self):
        ent = make_entity(
            entity_attr="targetTemperatureC",
            reported={"mode": "cool", "steamMode": True},
        )
        # Wire reported_state so it returns from the cache
        ent._reported_state_cache = {"mode": "cool", "steamMode": True}
        return ent

    def test_empty_condition_returns_true(self, entity):
        """Empty condition dict means no restriction → True."""
        assert entity._evaluate_trigger_condition({}, "someCapability") is True

    def test_eq_operator_match(self, entity):
        """operator='eq' returns True when operands match."""
        # Simulate: _evaluate_operand for operand_1 reads from reported_state
        result = entity._evaluate_trigger_condition(
            {
                "operator": "eq",
                "operand_1": "cool",  # pre-evaluated literal
                "operand_2": "cool",
            },
            "mode",
        )
        assert result is True

    def test_eq_operator_no_match(self, entity):
        """operator='eq' returns False when operands differ."""
        result = entity._evaluate_trigger_condition(
            {
                "operator": "eq",
                "operand_1": "cool",
                "operand_2": "heat",
            },
            "mode",
        )
        assert result is False

    def test_and_operator_both_true(self, entity):
        """operator='and' returns True when both sides truthy."""
        result = entity._evaluate_trigger_condition(
            {"operator": "and", "operand_1": True, "operand_2": True},
            "cap",
        )
        assert result is True

    def test_and_operator_one_false(self, entity):
        """operator='and' returns False when one side falsy."""
        result = entity._evaluate_trigger_condition(
            {"operator": "and", "operand_1": True, "operand_2": False},
            "cap",
        )
        assert result is False

    def test_or_operator_one_true(self, entity):
        """operator='or' returns True when at least one side truthy."""
        result = entity._evaluate_trigger_condition(
            {"operator": "or", "operand_1": False, "operand_2": True},
            "cap",
        )
        assert result is True

    def test_or_operator_both_false(self, entity):
        """operator='or' returns False when both sides falsy."""
        result = entity._evaluate_trigger_condition(
            {"operator": "or", "operand_1": False, "operand_2": False},
            "cap",
        )
        assert result is False

    def test_unknown_operator_returns_false(self, entity):
        """Unknown operator returns False (safe default)."""
        result = entity._evaluate_trigger_condition(
            {"operator": "xor", "operand_1": True, "operand_2": True},
            "cap",
        )
        assert result is False

    def test_dict_operands_are_evaluated(self, entity):
        """Dict operands trigger _evaluate_operand recursion."""
        # operand_1 is dict that reads from reported_state (mode="cool")
        condition = {
            "operator": "eq",
            "operand_1": {"operand_1": "mode"},
            "operand_2": "cool",
        }
        result = entity._evaluate_trigger_condition(condition, "mode")
        assert result is True

    def test_evaluate_operand_value_key_reads_trigger_cap(self, entity):
        """operand with operand_1='value' reads from reported state for that cap."""
        # cap_name = "mode", reported["mode"] = "cool"
        result = entity._evaluate_operand({"operand_1": "value"}, "mode")
        assert result == "cool"

    def test_evaluate_operand_named_cap(self, entity):
        """operand with named capability reads from reported state."""
        result = entity._evaluate_operand({"operand_1": "steamMode"}, "mode")
        assert result is True

    def test_evaluate_operand_literal_value(self, entity):
        """operand with 'value' key returns its literal."""
        result = entity._evaluate_operand({"value": 42}, "mode")
        assert result == 42

    def test_evaluate_operand_nested_condition(self, entity):
        """operand containing nested condition is recursively evaluated."""
        nested = {
            "operand_1": "cool",
            "operand_2": "cool",
            "operator": "eq",
        }
        result = entity._evaluate_operand(nested, "mode")
        assert result is True


# ===========================================================================
# 8.  _get_current_program_name  (entity.py lines 818-851)
# ===========================================================================


class TestGetCurrentProgramName:
    """Test _get_current_program_name from all possible locations."""

    def test_reads_from_program_key(self):
        """Reads from top-level 'program' key."""
        entity = make_entity(reported={"program": "ECO"})
        entity._reported_state_cache = {"program": "ECO"}
        assert entity._get_current_program_name() == "ECO"

    def test_reads_from_user_selections(self):
        """Reads from userSelections/programUID (dryer-style)."""
        entity = make_entity(reported={"userSelections": {"programUID": "COTTONS"}})
        entity._reported_state_cache = {"userSelections": {"programUID": "COTTONS"}}
        assert entity._get_current_program_name() == "COTTONS"

    def test_reads_from_cycle_personalization(self):
        """Reads from cyclePersonalization/programUID (alternative location)."""
        entity = make_entity(reported={})
        entity._reported_state_cache = {
            "cyclePersonalization": {"programUID": "DELICATE"}
        }
        assert entity._get_current_program_name() == "DELICATE"

    def test_returns_none_when_no_program(self):
        """Returns None when no program is found anywhere."""
        entity = make_entity(reported={})
        entity._reported_state_cache = {}
        assert entity._get_current_program_name() is None


# ===========================================================================
# 9.  _get_program_constraint  temperature cross-lookup  (lines 972-988)
# ===========================================================================


class TestGetProgramConstraintCrossLookup:
    """Test temperature unit cross-lookup in _get_program_constraint."""

    def _make_oven_entity(self, attr: str) -> ElectroluxNumber:
        entity = make_entity(entity_attr=attr)
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "program": {
                "values": {
                    "BAKE": {
                        "targetTemperatureC": {"min": 30, "max": 250, "step": 5}
                        # No 'targetTemperatureF' entry deliberately
                    }
                }
            }
        }
        entity._reported_state_cache = {"program": "BAKE"}
        return entity

    def test_f_entity_uses_c_constraint(self):
        """F temperature entity falls back to C constraint when F is absent."""
        entity = self._make_oven_entity("targetTemperatureF")
        # 'targetTemperatureF' not in caps, but 'targetTemperatureC' is
        result = entity._get_program_constraint("min")
        # Should fall through to C lookup and return 30
        assert result == 30

    def test_c_entity_returns_c_constraint_directly(self):
        """C temperature entity reads its own constraint directly."""
        entity = self._make_oven_entity("targetTemperatureC")
        result = entity._get_program_constraint("max")
        assert result == 250
