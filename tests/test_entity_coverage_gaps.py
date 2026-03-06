"""Targeted tests to fill entity.py coverage gaps.

Targets the following uncovered lines identified by coverage report:
- 103-106: async_setup_entry fallback_parts when object_id empty
- 116-119: async_setup_entry inner except (registry.async_get_or_create raises)
- 225: __init__ while loop when entity_attr contains '__'
- 243, 256, 258: __init__ userSelections/cyclePersonalization program_key init
- 285, 294, 298, 305: _handle_coordinator_update program branches
- 326-328, 337-342: _handle_coordinator_update program change cache invalidation
- 365, 369: reported_state.setter elif branches
- 402: _apply_optimistic_update entity_id set / log_message branch
- 528: device_info model fallback + mac raw_suffix path
- 564-566: reported_state.setter None value path + non-dict path
- 601, 606: extract_value unsupported probe throttle path
- 629-643: device_info long/Muju ID non-standard branch
- 668-669: device_info connections added when mac_address found
- 682, 690: name property catalog / model fallback
- 741, 782: is_connected + json_path branches
- 858-859: _is_supported_by_program cyclePersonalization branch
- 882-883: _is_supported_by_program no program caps → True
- 904-907: _is_supported_by_program F entity via C counterpart
- 917-920: _is_supported_by_program C entity via F counterpart
- 930-931: _is_supported_by_program targetDuration always True
- 942-953: _is_supported_by_program entity_cap from temperature counterpart
- 960-988: _is_supported_by_program trigger evaluation
- 997-998, 1005-1013: _is_supported_by_program food probe check
- 1050: _get_program_constraint C constraint for F entity
- 1074-1083: _get_program_constraint F constraint for C entity
- 1094-1095: _get_program_constraint exception handling
- 1112: _evaluate_operand cap_name == 'value' path
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import EntityCategory

from custom_components.electrolux.const import (
    FOOD_PROBE_STATE_NOT_INSERTED,
    NUMBER,
    SENSOR,
)
from custom_components.electrolux.number import ElectroluxNumber
from custom_components.electrolux.sensor import ElectroluxSensor

# ---------------------------------------------------------------------------
# Helpers (mirrors test_entity_core.py helpers)
# ---------------------------------------------------------------------------


def make_coordinator(reported: dict | None = None, pnc_id: str = "TEST_PNC"):
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
    catalog_entry=None,
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
        catalog_entry=catalog_entry,
    )
    entity.hass = coordinator.hass
    return entity


# ===========================================================================
# 1.  async_setup_entry – fallback object_id & inner except
# ===========================================================================


class TestAsyncSetupEntryGaps:
    """Cover the two uncovered paths in async_setup_entry."""

    @pytest.mark.asyncio
    async def test_empty_object_id_triggers_fallback(self):
        """When all brand/name/source/attr are empty, fallback_parts uses pnc_id."""
        from custom_components.electrolux.entity import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = "entity"
        # entity_attr empty so object_id will be empty after slugify
        mock_entity.entity_attr = ""
        mock_entity.entity_source = None
        mock_entity.unique_id = "uid-1"
        mock_entity.entity_domain = "sensor"
        mock_entity.pnc_id = "APPLIANCE-001"

        mock_appliance = MagicMock()
        mock_appliance.entities = [mock_entity]
        mock_appliance.brand = ""  # empty → not joined
        mock_appliance.name = ""  # empty → not joined

        mock_appliances = MagicMock()
        mock_appliances.appliances = {"APPLIANCE-001": mock_appliance}

        coordinator = MagicMock()
        coordinator.data = {"appliances": mock_appliances}

        entry = MagicMock()
        entry.runtime_data = coordinator

        mock_registry = MagicMock()
        add_entities = MagicMock()

        with patch(
            "custom_components.electrolux.entity.er.async_get",
            return_value=mock_registry,
        ):
            await async_setup_entry(MagicMock(), entry, add_entities)

        # Entity still added even when object_id falls back
        add_entities.assert_called_once()
        # Registry was called with some object_id derived from pnc_id
        mock_registry.async_get_or_create.assert_called_once()
        call_kwargs = mock_registry.async_get_or_create.call_args[1]
        assert "suggested_object_id" in call_kwargs
        assert call_kwargs["suggested_object_id"]  # not empty

    @pytest.mark.asyncio
    async def test_empty_object_id_with_attr_fallback(self):
        """When brand/name are empty but attr is set, fallback includes pnc_id + attr."""
        from custom_components.electrolux.entity import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = "entity"
        mock_entity.entity_attr = "targetTemp"
        mock_entity.entity_source = None
        mock_entity.unique_id = "uid-2"
        mock_entity.entity_domain = "number"
        mock_entity.pnc_id = "APPLIANCE-002"

        mock_appliance = MagicMock()
        mock_appliance.entities = [mock_entity]
        # brand/name both non-ASCII so slugify produces empty string
        mock_appliance.brand = "日本語"  # slugifies to empty
        mock_appliance.name = "テスト"  # slugifies to empty

        mock_appliances = MagicMock()
        mock_appliances.appliances = {"APPLIANCE-002": mock_appliance}

        coordinator = MagicMock()
        coordinator.data = {"appliances": mock_appliances}
        entry = MagicMock()
        entry.runtime_data = coordinator

        mock_registry = MagicMock()
        add_entities = MagicMock()

        with patch(
            "custom_components.electrolux.entity.er.async_get",
            return_value=mock_registry,
        ):
            await async_setup_entry(MagicMock(), entry, add_entities)

        add_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_inner_registry_exception_swallowed_entity_still_added(self):
        """When registry.async_get_or_create raises, entity still added (inner except)."""
        from custom_components.electrolux.entity import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = "entity"
        mock_entity.entity_attr = "applianceState"
        mock_entity.entity_source = None
        mock_entity.unique_id = "uid-inner-err"
        mock_entity.entity_domain = "sensor"
        mock_entity.pnc_id = "APPLIANCE-003"

        mock_appliance = MagicMock()
        mock_appliance.entities = [mock_entity]
        mock_appliance.brand = "Electrolux"
        mock_appliance.name = "Washer"

        mock_appliances = MagicMock()
        mock_appliances.appliances = {"APPLIANCE-003": mock_appliance}

        coordinator = MagicMock()
        coordinator.data = {"appliances": mock_appliances}
        entry = MagicMock()
        entry.runtime_data = coordinator
        add_entities = MagicMock()

        # er.async_get SUCCEEDS, but async_get_or_create raises
        mock_registry = MagicMock()
        mock_registry.async_get_or_create.side_effect = Exception("DB locked")

        with patch(
            "custom_components.electrolux.entity.er.async_get",
            return_value=mock_registry,
        ):
            await async_setup_entry(MagicMock(), entry, add_entities)

        # Entity MUST still be added despite inner exception
        add_entities.assert_called_once()
        added = add_entities.call_args[0][0]
        assert mock_entity in added


# ===========================================================================
# 2.  ElectroluxEntity.__init__ – entity_attr with '__' + program sources
# ===========================================================================


class TestEntityInitGaps:
    """Cover uncovered __init__ branches."""

    def test_entity_attr_with_double_underscore_translation_key(self):
        """entity_attr containing '__' triggers the while-loop normalisation."""
        entity = make_entity(entity_attr="user__selections__program")
        # The double underscores should be collapsed
        key = entity._attr_translation_key or ""
        assert "__" not in key

    def test_entity_attr_with_multiple_double_underscores(self):
        """Multiple consecutive __ are all collapsed."""
        entity = make_entity(entity_attr="foo____bar")
        key = entity._attr_translation_key or ""
        assert "__" not in key
        assert key == "foo_bar"

    def test_program_key_from_userselections_in_init(self):
        """When reported state has userSelections.programUID, init caches it."""
        coordinator, _ = make_coordinator(
            reported={"userSelections": {"programUID": "Cotton"}}
        )
        entity = ElectroluxNumber(
            coordinator=coordinator,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability={"access": "readwrite"},
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:thermometer",
        )
        assert entity._program_cache_key == "Cotton"

    def test_program_key_from_cyclepersonalization_in_init(self):
        """When reported state has cyclePersonalization.programUID, init caches it."""
        coordinator, _ = make_coordinator(
            reported={"cyclePersonalization": {"programUID": "Delicate"}}
        )
        entity = ElectroluxNumber(
            coordinator=coordinator,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability={"access": "readwrite"},
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:thermometer",
        )
        assert entity._program_cache_key == "Delicate"

    def test_init_with_no_coordinator_data(self):
        """When coordinator.data is None/empty, appliance_status starts as None."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"api_key": "testkey"}
        coordinator.data = None
        coordinator._last_update_times = {}

        entity = ElectroluxNumber(
            coordinator=coordinator,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability={"access": "readwrite"},
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:thermometer",
        )
        assert entity.appliance_status is None
        assert entity._reported_state_cache == {}


# ===========================================================================
# 3.  _handle_coordinator_update – program branches + cache invalidation
# ===========================================================================


class TestHandleCoordinatorUpdateGaps:
    """Cover cyclePersonalization, userSelections, and cache-invalidation branches."""

    def _make_coordinator_with_state(self, reported: dict):
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"api_key": "testkey123456789012"}
        coordinator._last_update_times = {}

        mock_appliances = MagicMock()
        mock_appliance = MagicMock()
        mock_appliance.state = {"properties": {"reported": reported}}
        mock_appliances.get_appliance.return_value = mock_appliance
        coordinator.data = {"appliances": mock_appliances}
        return coordinator

    def test_program_from_userselections_in_update(self):
        """_handle_coordinator_update reads program from userSelections.programUID."""
        coordinator = self._make_coordinator_with_state(
            {"userSelections": {"programUID": "QuickWash"}}
        )
        entity = ElectroluxNumber(
            coordinator=coordinator,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test",
            entity_attr="spinSpeed",
            entity_source=None,
            capability={"access": "readwrite"},
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:wash",
        )
        entity.pnc_id = "TEST_PNC"
        entity.async_write_ha_state = MagicMock()

        # Set initial program_cache_key to something different
        entity._program_cache_key = "OldProgram"
        entity._is_supported_cache = True
        entity._constraints_cache = {"min": 30}

        entity._handle_coordinator_update()

        # Cache should be cleared after program change
        assert entity._program_cache_key == "QuickWash"
        assert entity._is_supported_cache is None
        assert entity._constraints_cache == {}

    def test_program_from_cyclepersonalization_in_update(self):
        """_handle_coordinator_update reads program from cyclePersonalization.programUID."""
        coordinator = self._make_coordinator_with_state(
            {"cyclePersonalization": {"programUID": "Synthetic"}}
        )
        entity = ElectroluxNumber(
            coordinator=coordinator,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test",
            entity_attr="temperature",
            entity_source=None,
            capability={"access": "readwrite"},
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:thermometer",
        )
        entity.pnc_id = "TEST_PNC"
        entity.async_write_ha_state = MagicMock()
        entity._program_cache_key = "OldProgram"
        entity._is_supported_cache = True
        entity._constraints_cache = {"max": 90}

        entity._handle_coordinator_update()

        assert entity._program_cache_key == "Synthetic"
        assert entity._is_supported_cache is None
        assert entity._constraints_cache == {}

    def test_non_dict_appliance_status_clears_cache(self):
        """When get_appliance returns non-dict state, cache is reset to {}."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.data = {"api_key": "testkey123456789012"}
        coordinator._last_update_times = {}

        mock_appliances = MagicMock()
        mock_appliance = MagicMock()
        # Return non-dict state
        mock_appliance.state = "invalid_state_string"
        mock_appliances.get_appliance.return_value = mock_appliance
        coordinator.data = {"appliances": mock_appliances}

        entity = ElectroluxNumber(
            coordinator=coordinator,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test",
            entity_attr="spinSpeed",
            entity_source=None,
            capability={"access": "readwrite"},
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:wash",
        )
        entity.pnc_id = "TEST_PNC"
        entity._reported_state_cache = {"old": "data"}
        entity.async_write_ha_state = MagicMock()

        entity._handle_coordinator_update()

        assert entity._reported_state_cache == {}

    def test_program_unchanged_does_not_clear_cache(self):
        """When program is the same, caches are NOT cleared."""
        coordinator = self._make_coordinator_with_state({"program": "Cotton"})
        entity = ElectroluxNumber(
            coordinator=coordinator,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability={"access": "readwrite"},
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:thermometer",
        )
        entity.pnc_id = "TEST_PNC"
        entity.async_write_ha_state = MagicMock()
        # Same program already in cache
        entity._program_cache_key = "Cotton"
        entity._is_supported_cache = True
        entity._constraints_cache = {"min": 30}

        entity._handle_coordinator_update()

        # Cache should NOT be cleared (program didn't change)
        assert entity._is_supported_cache is True
        assert entity._constraints_cache == {"min": 30}


# ===========================================================================
# 4.  reported_state.setter – elif branches for broken appliance_status
# ===========================================================================


class TestReportedStateSetterGaps:
    """Cover the elif branches in reported_state.setter."""

    def test_setter_when_properties_missing_from_dict(self):
        """elif branch: appliance_status is dict but missing 'properties' key."""
        entity = make_entity()
        entity.appliance_status = {"connectionState": "connected"}  # no 'properties'

        entity.reported_state = {"temperature": 75}

        assert entity.reported_state == {"temperature": 75}
        props = entity.appliance_status.get("properties")
        assert isinstance(props, dict)
        assert props.get("reported") == {"temperature": 75}

    def test_setter_when_properties_is_not_dict(self):
        """elif branch: appliance_status['properties'] is not a dict."""
        entity = make_entity()
        entity.appliance_status = {"properties": "broken_string_not_dict"}

        entity.reported_state = {"spinSpeed": 1200}

        assert entity.reported_state == {"spinSpeed": 1200}

    def test_setter_when_reported_missing_from_properties(self):
        """elif branch: 'reported' key missing from properties."""
        entity = make_entity()
        entity.appliance_status = {"properties": {"other": "stuff"}}  # no 'reported'

        entity.reported_state = {"humidity": 55}

        assert entity.reported_state == {"humidity": 55}
        assert entity.appliance_status["properties"]["reported"] == {"humidity": 55}

    def test_setter_when_reported_is_not_dict(self):
        """elif branch: 'reported' is not a dict."""
        entity = make_entity()
        entity.appliance_status = {"properties": {"reported": "bad_string"}}

        entity.reported_state = {"mode": "cool"}

        assert entity.reported_state == {"mode": "cool"}

    def test_setter_none_clears_both_stores(self):
        """Setting None clears the reported state and cache."""
        entity = make_entity(reported={"targetTemperatureC": 60})

        entity.reported_state = None

        assert entity.reported_state == {}
        assert entity._reported_state_cache == {}


# ===========================================================================
# 5.  _apply_optimistic_update – entity_id set + log_message paths
# ===========================================================================


class TestApplyOptimisticUpdateGaps:
    """Cover entity_id and log_message branches in _apply_optimistic_update."""

    def test_writes_ha_state_when_entity_id_is_set(self):
        """async_write_ha_state is called when entity has entity_id set."""
        entity = make_entity(reported={"targetTemperatureC": 50})
        entity.entity_id = "number.electrolux_targettemperaturec"
        entity.async_write_ha_state = MagicMock()

        entity._apply_optimistic_update("targetTemperatureC", 60)

        entity.async_write_ha_state.assert_called_once()
        assert entity.reported_state.get("targetTemperatureC") == 60

    def test_no_write_ha_state_when_entity_id_not_set(self):
        """async_write_ha_state is NOT called when entity_id is empty."""
        entity = make_entity(reported={"targetTemperatureC": 50})
        entity.entity_id = ""  # Not yet registered (falsy, same as unset)
        entity.async_write_ha_state = MagicMock()

        entity._apply_optimistic_update("targetTemperatureC", 65)

        entity.async_write_ha_state.assert_not_called()
        assert entity.reported_state.get("targetTemperatureC") == 65

    def test_custom_log_message_branch(self):
        """log_message provided → custom log branch executes."""
        entity = make_entity(reported={"mode": "cool"})
        entity.entity_id = ""  # Not yet registered (falsy)
        entity.async_write_ha_state = MagicMock()

        # Should not raise and should update state
        entity._apply_optimistic_update("mode", "heat", log_message="user changed mode")
        assert entity.reported_state.get("mode") == "heat"

    def test_no_update_when_appliance_status_none(self):
        """Nothing happens when appliance_status is None."""
        entity = make_entity()
        entity.appliance_status = None
        entity.async_write_ha_state = MagicMock()

        entity._apply_optimistic_update("targetTemperatureC", 50)

        entity.async_write_ha_state.assert_not_called()


# ===========================================================================
# 6.  available property – returns False
# ===========================================================================


class TestAvailableProperty:
    """Cover the False branch of available."""

    def test_available_false_when_appliance_status_none(self):
        """Returns False when appliance_status is explicitly None."""
        entity = make_entity()
        entity.appliance_status = None
        assert entity.available is False

    def test_available_true_when_appliance_status_dict(self):
        """Returns True when appliance_status is set."""
        entity = make_entity()
        entity.appliance_status = {"properties": {"reported": {}}}
        assert entity.available is True


# ===========================================================================
# 7.  device_info – various format gaps
# ===========================================================================


class TestDeviceInfoGaps:
    """Cover uncovered device_info branches."""

    def _make_entity_with_pnc(self, pnc_id: str, appliance_type="WM", model=None):
        entity = make_entity(pnc_id=pnc_id)
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        mock_appliance.model = model
        mock_appliance.brand = "Electrolux"
        mock_appliance.name = "Test Appliance"
        mock_appliance.appliance_type = appliance_type
        mock_appliance.serial_number = "SN123"
        return entity

    def test_model_falls_back_to_name_when_type_unknown(self):
        """When model is Unknown and appliance_type is also Unknown, uses name."""
        entity = self._make_entity_with_pnc("916099949_00", "Unknown", model="Unknown")
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        mock_appliance.name = "My Appliance"

        info = entity.device_info
        assert "My Appliance" in str(info)

    def test_model_falls_back_to_str_when_no_name_no_type(self):
        """When model=Unknown, type=Unknown, name is None → device name uses 'Unknown Appliance'."""
        entity = self._make_entity_with_pnc("916099949_00", "Unknown", model="Unknown")
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        mock_appliance.name = None

        info = entity.device_info
        # The fallback sets model='Unknown Appliance' which feeds into info["name"]
        assert "Unknown Appliance" in str(info.get("name", ""))

    def test_mac_suffix_with_no_dash_uses_raw_suffix(self):
        """When pnc_id suffix has no '-', mac_address = raw_suffix directly."""
        # "31862190443E07363DAB" has no dash in the part after ':'
        pnc_id = "916099949_00:31862190443E07363DAB"
        entity = self._make_entity_with_pnc(pnc_id, "WM")
        info = entity.device_info
        # We just assert it doesn't raise and returns valid device info
        assert "identifiers" in info

    def test_mac_raw_not_12_chars_uses_raw_suffix(self):
        """When the hex after '-' is not 12 chars, mac_address = raw_suffix."""
        # Make last part invalid hex (too short)
        pnc_id = "916099949_00:31862190-TOOSHORT"
        entity = self._make_entity_with_pnc(pnc_id, "WM")
        info = entity.device_info
        assert "identifiers" in info

    def test_long_id_non_standard_format(self):
        """Long numeric (Muju-style) IDs follow the non-standard branch."""
        pnc_id = "956006959323006505087076"
        entity = self._make_entity_with_pnc(pnc_id, "RF")
        info = entity.device_info
        # No connections expected (no MAC in plain numeric ID)
        assert info.get("connections", set()) == set()
        # Model contains the long ID
        assert "956006959323006505087076" in str(info.get("model", ""))

    def test_non_standard_id_with_dam_type(self):
        """Long ID with DAM appliance_type strips DAM_ prefix."""
        pnc_id = "956006959323006505087076"
        entity = self._make_entity_with_pnc(pnc_id, "DAM_AC")
        info = entity.device_info
        assert "AC-" in str(info.get("model", ""))
        assert "DAM_" not in str(info.get("model", ""))

    def test_device_info_with_valid_mac_adds_connections(self):
        """Valid MAC in standard PNC adds connections to device_info."""
        pnc_id = "916099949_00:31862190-443E07363DAB"
        entity = self._make_entity_with_pnc(pnc_id, "WM")
        info = entity.device_info
        assert "connections" in info
        connections = info["connections"]
        assert any("44:3E:07:36:3D:AB" in str(v) for v in connections)

    def test_device_info_serial_none(self):
        """serial_number = None → serial_number not in device_info or None."""
        entity = self._make_entity_with_pnc("916099949_00:31862190-443E07363DAB", "WM")
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        mock_appliance.serial_number = None
        info = entity.device_info
        assert info.get("serial_number") is None

    def test_device_info_no_appliance_type(self):
        """appliance_type = None → type_part is empty, no type prefix in model."""
        entity = self._make_entity_with_pnc("916099949_00:31862190-443E07363DAB")
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        mock_appliance.appliance_type = None
        mock_appliance.model = "SomeModel"

        info = entity.device_info
        # Model starts with "Model:" but no type prefix
        model = info.get("model") or ""
        assert model.startswith("Model:")


# ===========================================================================
# 8.  name property – catalog entry friendly_name branch
# ===========================================================================


class TestNameProperty:
    """Cover catalog_entry.friendly_name branch."""

    def test_name_from_catalog_friendly_name(self):
        """name returns capitalized catalog friendly_name when present."""
        catalog = MagicMock()
        catalog.friendly_name = "target temperature"
        catalog.entity_icon = None
        catalog.entity_registry_enabled_default = True
        entity = make_entity(catalog_entry=catalog)
        assert entity.name == "Target temperature"

    def test_name_fallback_when_no_catalog(self):
        """name returns _name when no catalog entry."""
        entity = make_entity()
        entity._catalog_entry = None
        assert entity.name == "Test Entity"


# ===========================================================================
# 9.  is_connected – offline path + json_path
# ===========================================================================


class TestIsConnectedAndJsonPath:
    """Cover disconnected path and json_path with source."""

    def test_is_connected_false_when_disconnected(self):
        """Returns False when connectivityState is not 'connected'."""
        entity = make_entity(reported={"connectivityState": "Disconnected"})
        assert entity.is_connected() is False

    def test_is_connected_true_when_connected(self):
        """Returns True when connectivityState is 'connected'."""
        entity = make_entity(reported={"connectivityState": "connected"})
        assert entity.is_connected() is True

    def test_is_connected_true_when_no_state(self):
        """Returns True when connectivityState not reported (backwards compat)."""
        entity = make_entity(reported={})
        assert entity.is_connected() is True

    def test_json_path_with_source(self):
        """json_path returns 'source/attr' when entity_source is set."""
        entity = make_entity(entity_attr="spinSpeed", entity_source="userSelections")
        assert entity.json_path == "userSelections/spinSpeed"

    def test_json_path_without_source(self):
        """json_path returns just attr when no source."""
        entity = make_entity(entity_attr="applianceState", entity_source=None)
        assert entity.json_path == "applianceState"


# ===========================================================================
# 10. extract_value – foodProbe not-supported throttle path
# ===========================================================================


class TestExtractValueFoodProbe:
    """Cover the targetFoodProbeTemperatureC unsupported path in extract_value."""

    def test_food_probe_unsupported_returns_min(self):
        """When targetFoodProbeTemperatureC is unsupported, returns min value."""
        entity = make_entity(
            entity_attr="targetFoodProbeTemperatureC",
            reported={"foodProbeInsertionState": FOOD_PROBE_STATE_NOT_INSERTED},
            capability={"access": "readwrite", "min": 0, "max": 100},
        )
        entity.is_connected = MagicMock(return_value=True)
        # _is_supported_by_program must return False to reach the probe-min path
        entity._is_supported_by_program = MagicMock(return_value=False)

        result = entity.extract_value()
        assert result == 0  # min value

    def test_food_probe_unsupported_uses_program_constraint_min(self):
        """targetFoodProbeTemperatureC unsupported uses program constraint min if available."""
        entity = make_entity(
            entity_attr="targetFoodProbeTemperatureC",
            reported={
                "program": "Roasting",
                "foodProbeInsertionState": FOOD_PROBE_STATE_NOT_INSERTED,
            },
            capability={"access": "readwrite", "min": 10, "max": 100},
        )
        entity.is_connected = MagicMock(return_value=True)
        entity._is_supported_by_program = MagicMock(return_value=False)

        # Mock program constraint min = 15
        entity._get_program_constraint = MagicMock(return_value=15)

        result = entity.extract_value()
        assert result == 15

    def test_food_probe_unsupported_throttle_log_not_repeated(self):
        """Second call within 1 hour does not re-log."""

        entity = make_entity(
            entity_attr="targetFoodProbeTemperatureC",
            reported={"foodProbeInsertionState": FOOD_PROBE_STATE_NOT_INSERTED},
            capability={"access": "readwrite", "min": 0, "max": 100},
        )
        entity.is_connected = MagicMock(return_value=True)
        entity._is_supported_by_program = MagicMock(return_value=False)

        # First call sets the log timestamp
        entity.extract_value()
        log_key = "probe_not_supported_targetFoodProbeTemperatureC"
        first_ts = getattr(entity, f"_last_log_{log_key}", 0.0)
        assert first_ts > 0

        # Second call within 1 hour should NOT update the timestamp

        second_result = entity.extract_value()
        second_ts = getattr(entity, f"_last_log_{log_key}", 0.0)
        assert second_ts == first_ts  # not updated again within 1 hour
        assert second_result == 0


# ===========================================================================
# 11. _is_supported_by_program – all uncovered branches
# ===========================================================================


def _make_entity_with_capabilities(
    entity_attr: str,
    entity_source: str | None = None,
    reported: dict | None = None,
    appliance_capabilities: dict | None = None,
) -> ElectroluxNumber:
    """Create entity with mock appliance capabilities for program support tests."""
    entity = make_entity(
        entity_attr=entity_attr,
        entity_source=entity_source,
        reported=reported or {},
    )
    # Wire get_appliance.data.capabilities
    mock_data = MagicMock()
    mock_data.capabilities = appliance_capabilities or {}
    entity.coordinator.data["appliances"].get_appliance.return_value.data = mock_data
    return entity


class TestIsSupportedByProgramGaps:
    """Cover uncovered branches in _is_supported_by_program."""

    def test_program_from_cyclepersonalization(self):
        """Program retrieved from cyclePersonalization.programUID."""
        caps = {
            "cyclePersonalization/programUID": {
                "values": {"Synthetic": {"targetTemperatureC": {"min": 30, "max": 60}}}
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureC",
            reported={"cyclePersonalization": {"programUID": "Synthetic"}},
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is True

    def test_no_program_caps_returns_true(self):
        """When program exists but no caps for it, returns True (assume supported)."""
        caps = {
            "program": {
                "values": {
                    # "Cotton" is not here
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton"},
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is True

    def test_F_entity_found_via_C_counterpart(self):
        """F temperature entity is found via its C counterpart in program caps."""
        caps = {
            "program": {
                "values": {"Roasting": {"targetTemperatureC": {"min": 50, "max": 250}}}
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureF",  # F entity
            reported={"program": "Roasting"},
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is True

    def test_C_entity_found_via_F_counterpart(self):
        """C temperature entity is found via its F counterpart in program caps."""
        caps = {
            "program": {
                "values": {"Roasting": {"targetTemperatureF": {"min": 122, "max": 482}}}
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureC",  # C entity
            reported={"program": "Roasting"},
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is True

    def test_food_probe_F_found_via_C_counterpart(self):
        """FoodProbeTemperatureF entity found via C counterpart."""
        caps = {
            "program": {
                "values": {
                    "Roasting": {"targetFoodProbeTemperatureC": {"min": 30, "max": 90}}
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetFoodProbeTemperatureF",
            reported={"program": "Roasting"},
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is True

    def test_targetDuration_always_true_when_not_in_caps(self):
        """targetDuration is always supported regardless of program caps."""
        caps = {
            "program": {
                "values": {
                    "Cotton": {
                        # targetDuration not listed
                        "targetTemperatureC": {"min": 30, "max": 90}
                    }
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetDuration",
            reported={"program": "Cotton"},
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is True

    def test_entity_cap_from_F_counterpart_for_C_entity(self):
        """entity_cap is fetched from F counterpart when C entity's cap is absent."""
        caps = {
            "program": {
                "values": {
                    "Roasting": {
                        "targetTemperatureF": {
                            "min": 122,
                            "max": 482,
                            "disabled": False,
                        }
                    }
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureC",
            reported={"program": "Roasting"},
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is True

    def test_entity_cap_from_C_counterpart_for_F_entity(self):
        """entity_cap is fetched from C counterpart when F entity's cap is absent."""
        caps = {
            "program": {
                "values": {
                    "Roasting": {
                        "targetTemperatureC": {"min": 50, "max": 250, "disabled": False}
                    }
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureF",
            reported={"program": "Roasting"},
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is True

    def test_trigger_disables_entity(self):
        """A trigger that sets disabled=True makes entity unsupported."""
        caps = {
            "program": {
                "values": {"Cotton": {"targetTemperatureC": {"min": 30, "max": 90}}}
            }
        }
        all_caps = {
            **caps,
            "steamMode": {
                "values": {"on": {}, "off": {}},
                "triggers": [
                    {
                        "condition": {
                            "operator": "eq",
                            "operand_1": "on",
                            "operand_2": "on",
                        },
                        "action": {"targetTemperatureC": {"disabled": True}},
                    }
                ],
            },
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton", "steamMode": "on"},
            appliance_capabilities=all_caps,
        )
        # The trigger condition: operand_1="on" == operand_2="on" → True → disabled
        result = entity._is_supported_by_program()
        assert result is False

    def test_trigger_condition_not_met_does_not_disable(self):
        """A trigger that evaluates False does NOT disable the entity."""
        caps = {
            "program": {
                "values": {"Cotton": {"targetTemperatureC": {"min": 30, "max": 90}}}
            }
        }
        all_caps = {
            **caps,
            "steamMode": {
                "triggers": [
                    {
                        "condition": {
                            "operator": "eq",
                            "operand_1": "on",
                            "operand_2": "off",  # condition is FALSE
                        },
                        "action": {"targetTemperatureC": {"disabled": True}},
                    }
                ],
            },
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton", "steamMode": "on"},
            appliance_capabilities=all_caps,
        )
        result = entity._is_supported_by_program()
        assert result is True

    def test_food_probe_not_inserted_returns_false(self):
        """food probe not inserted → _is_supported_by_program returns False."""
        caps = {
            "program": {
                "values": {
                    "Roasting": {"targetFoodProbeTemperatureC": {"min": 30, "max": 90}}
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetFoodProbeTemperatureC",
            reported={
                "program": "Roasting",
                "foodProbeInsertionState": FOOD_PROBE_STATE_NOT_INSERTED,
            },
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is False

    def test_food_probe_F_not_inserted_returns_false(self):
        """targetFoodProbeTemperatureF also respects foodProbeInsertionState."""
        caps = {
            "program": {
                "values": {
                    "Roasting": {"targetFoodProbeTemperatureF": {"min": 86, "max": 194}}
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetFoodProbeTemperatureF",
            reported={
                "program": "Roasting",
                "foodProbeInsertionState": FOOD_PROBE_STATE_NOT_INSERTED,
            },
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is False

    def test_targetDuration_always_true_when_disabled_by_trigger(self):
        """targetDuration special case: always True even if trigger would disable."""
        caps = {"program": {"values": {"Cotton": {"targetDuration": {"min": 30}}}}}
        entity = _make_entity_with_capabilities(
            entity_attr="targetDuration",
            reported={"program": "Cotton"},
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is True

    def test_no_appliance_data_returns_not_disabled(self):
        """When get_appliance has no .data, cannot evaluate triggers → uses disabled flag."""
        entity = make_entity(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton"},
        )
        # Set up program caps via mock
        program_caps = {
            "Cotton": {"targetTemperatureC": {"min": 30, "max": 90, "disabled": False}}
        }
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        # No .data attribute
        del mock_appliance.data

        # Make _get_program_capabilities return program caps
        entity._get_program_capabilities = MagicMock(
            return_value=program_caps["Cotton"]
        )

        result = entity._is_supported_by_program()
        assert result is True  # not disabled

    def test_entity_not_in_program_caps_returns_false(self):
        """Entity not in program caps and not a temperature/duration → False."""
        caps = {
            "program": {
                "values": {
                    "Cotton": {
                        "targetTemperatureC": {"min": 30, "max": 90}
                        # spinSpeed is NOT here
                    }
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="spinSpeed",
            reported={"program": "Cotton"},
            appliance_capabilities=caps,
        )
        result = entity._is_supported_by_program()
        assert result is False


# ===========================================================================
# 12. _get_program_constraint – temperature cross-unit + exception
# ===========================================================================


class TestGetProgramConstraintGaps:
    """Cover temperature counterpart lookup and exception handling."""

    def test_F_entity_gets_constraint_from_C_counterpart(self):
        """F temperature entity falls back to C counterpart for constraints."""
        caps = {
            "program": {
                "values": {
                    "Roasting": {
                        "targetTemperatureC": {"min": 50, "max": 250, "step": 5}
                    }
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureF",
            reported={"program": "Roasting"},
            appliance_capabilities=caps,
        )

        min_val = entity._get_program_constraint("min")
        assert min_val == 50

    def test_C_entity_gets_constraint_from_F_counterpart(self):
        """C temperature entity falls back to F counterpart for constraints."""
        caps = {
            "program": {
                "values": {
                    "Roasting": {
                        "targetTemperatureF": {"min": 122, "max": 482, "step": 9}
                    }
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureC",
            reported={"program": "Roasting"},
            appliance_capabilities=caps,
        )

        max_val = entity._get_program_constraint("max")
        assert max_val == 482

    def test_food_probe_F_constraint_from_C(self):
        """targetFoodProbeTemperatureF falls back to C counterpart."""
        caps = {
            "program": {
                "values": {
                    "Roasting": {"targetFoodProbeTemperatureC": {"min": 30, "max": 90}}
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetFoodProbeTemperatureF",
            reported={"program": "Roasting"},
            appliance_capabilities=caps,
        )
        min_val = entity._get_program_constraint("min")
        assert min_val == 30

    def test_food_probe_C_constraint_from_F(self):
        """targetFoodProbeTemperatureC falls back to F counterpart."""
        caps = {
            "program": {
                "values": {
                    "Roasting": {"targetFoodProbeTemperatureF": {"min": 86, "max": 194}}
                }
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetFoodProbeTemperatureC",
            reported={"program": "Roasting"},
            appliance_capabilities=caps,
        )
        max_val = entity._get_program_constraint("max")
        assert max_val == 194

    def test_returns_none_on_attribute_error(self):
        """AttributeError in capability lookup returns None gracefully."""
        entity = make_entity(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton"},
        )
        # Make _get_program_capabilities raise AttributeError
        entity._get_program_capabilities = MagicMock(side_effect=AttributeError("oops"))

        result = entity._get_program_constraint("min")
        assert result is None

    def test_returns_none_on_key_error(self):
        """KeyError in capability lookup returns None gracefully."""
        entity = make_entity(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton"},
        )
        entity._get_program_capabilities = MagicMock(side_effect=KeyError("missing"))

        result = entity._get_program_constraint("min")
        assert result is None

    def test_constraint_cached_after_first_call(self):
        """Second call uses cache instead of re-computing."""
        caps = {
            "program": {
                "values": {"Cotton": {"targetTemperatureC": {"min": 30, "max": 90}}}
            }
        }
        entity = _make_entity_with_capabilities(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton"},
            appliance_capabilities=caps,
        )

        result1 = entity._get_program_constraint("min")
        # Poison the caps so if re-computed it would differ
        entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value.data.capabilities = {}
        result2 = entity._get_program_constraint("min")
        assert result1 == result2 == 30


# ===========================================================================
# 13. _evaluate_operand – nested condition + cap_name == 'value'
# ===========================================================================


class TestEvaluateOperandGaps:
    """Cover uncovered branches in _evaluate_operand."""

    @pytest.fixture
    def entity(self):
        ent = make_entity(
            entity_attr="targetTemperatureC",
            reported={"mode": "cool", "steamMode": "on"},
        )
        ent._reported_state_cache = {"mode": "cool", "steamMode": "on"}
        return ent

    def test_nested_condition_operand(self, entity):
        """When operand has both operand_1 and operand_2, it's a nested condition."""
        nested_operand = {
            "operator": "eq",
            "operand_1": "cool",
            "operand_2": "cool",
        }
        # Because operand has both operand_1 and operand_2, it's treated as a condition
        result = entity._evaluate_operand(nested_operand, "mode")
        assert result is True

    def test_nested_condition_operand_false(self, entity):
        """Nested condition evaluating to False."""
        nested_operand = {
            "operator": "eq",
            "operand_1": "cool",
            "operand_2": "heat",  # does not match
        }
        result = entity._evaluate_operand(nested_operand, "mode")
        assert result is False

    def test_operand_cap_name_is_value_reads_trigger_cap(self, entity):
        """operand_1='value' reads from trigger_cap_name in reported_state."""
        # "value" is a special keyword meaning "the value of the triggering capability"
        operand = {"operand_1": "value"}
        # trigger_cap_name = "steamMode", which has value "on" in reported_state
        result = entity._evaluate_operand(operand, "steamMode")
        assert result == "on"

    def test_operand_regular_cap_name_reads_from_reported(self, entity):
        """operand_1 = regular cap name reads from reported_state."""
        operand = {"operand_1": "mode"}
        result = entity._evaluate_operand(operand, "someOtherCap")
        assert result == "cool"

    def test_operand_literal_value(self, entity):
        """Operand with just 'value' key returns literal."""
        operand = {"value": "literal_value"}
        result = entity._evaluate_operand(operand, "anyCap")
        assert result == "literal_value"

    def test_or_operator_one_true(self, entity):
        """operator='or' returns True when at least one side is truthy."""
        result = entity._evaluate_trigger_condition(
            {"operator": "or", "operand_1": False, "operand_2": True},
            "cap",
        )
        assert result is True

    def test_unknown_operator_returns_false(self, entity):
        """Unknown operator returns False."""
        result = entity._evaluate_trigger_condition(
            {"operator": "xor", "operand_1": True, "operand_2": False},
            "cap",
        )
        assert result is False


# ===========================================================================
# 14. _get_program_capabilities – no appliance data or no capabilities
# ===========================================================================


class TestGetProgramCapabilitiesGaps:
    """Cover edge cases in _get_program_capabilities."""

    def test_no_get_appliance_data_returns_empty(self):
        """When get_appliance has no .data attribute, returns {}."""
        entity = make_entity(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton"},
        )
        # Remove .data from the appliance mock
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        del mock_appliance.data

        result = entity._get_program_capabilities("Cotton")
        assert result == {}

    def test_no_capabilities_on_appliance_data_returns_empty(self):
        """When appliance.data.capabilities is None/empty, returns {}."""
        entity = make_entity(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton"},
        )
        mock_data = MagicMock()
        mock_data.capabilities = None
        entity.coordinator.data["appliances"].get_appliance.return_value.data = (
            mock_data
        )

        result = entity._get_program_capabilities("Cotton")
        assert result == {}

    def test_userselections_location(self):
        """Program caps found via userSelections/programUID path."""
        mock_data = MagicMock()
        mock_data.capabilities = {
            "userSelections/programUID": {
                "values": {"QuickWash": {"spinSpeed": {"min": 400, "max": 1200}}}
            }
        }
        entity = make_entity(entity_attr="spinSpeed", reported={"program": "QuickWash"})
        entity.coordinator.data["appliances"].get_appliance.return_value.data = (
            mock_data
        )

        result = entity._get_program_capabilities("QuickWash")
        assert "spinSpeed" in result

    def test_cyclepersonalization_location(self):
        """Program caps found via cyclePersonalization/programUID path."""
        mock_data = MagicMock()
        mock_data.capabilities = {
            "cyclePersonalization/programUID": {
                "values": {"Synthetic": {"temperature": {"min": 30, "max": 60}}}
            }
        }
        entity = make_entity(entity_attr="temperature", reported={})
        entity.coordinator.data["appliances"].get_appliance.return_value.data = (
            mock_data
        )

        result = entity._get_program_capabilities("Synthetic")
        assert "temperature" in result


# ===========================================================================
# 15.  is_dam_appliance property
# ===========================================================================


class TestIsDamAppliance:
    def test_dam_appliance(self):
        entity = make_entity(pnc_id="1:950022200_00:34509998-443E074D965A")
        assert entity.is_dam_appliance is True

    def test_non_dam_appliance(self):
        entity = make_entity(pnc_id="916099949_00:31862190-443E07363DAB")
        assert entity.is_dam_appliance is False


# ===========================================================================
# 16. Additional targeted tests for remaining 18 uncovered lines
# ===========================================================================


class TestLine105FallbackWithAttr:
    """Line 105: fallback_parts.append(str(attr)) when object_id empty but attr truthy."""

    @pytest.mark.asyncio
    async def test_empty_object_id_with_truthy_attr_reaches_fallback_append(self):
        """Line 105: When slugify returns '' and attr is truthy, fallback_parts.append fires."""
        from custom_components.electrolux.entity import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = "entity"
        mock_entity.entity_attr = "targetTemperatureC"  # truthy attr
        mock_entity.entity_source = None
        mock_entity.unique_id = "uid-line105"
        mock_entity.entity_domain = "sensor"
        mock_entity.pnc_id = "DEVICE-ABC"

        mock_appliance = MagicMock()
        mock_appliance.entities = [mock_entity]
        mock_appliance.brand = "Electrolux"
        mock_appliance.name = "Washer"

        mock_appliances = MagicMock()
        mock_appliances.appliances = {"DEVICE-ABC": mock_appliance}

        coordinator = MagicMock()
        coordinator.data = {"appliances": mock_appliances}
        entry = MagicMock()
        entry.runtime_data = coordinator

        mock_registry = MagicMock()
        add_entities = MagicMock()

        # First slugify call returns "" (triggers fallback), second returns actual slug
        with patch(
            "custom_components.electrolux.entity.slugify",
            side_effect=["", "device_abc_targettemperaturec"],
        ):
            with patch(
                "custom_components.electrolux.entity.er.async_get",
                return_value=mock_registry,
            ):
                await async_setup_entry(MagicMock(), entry, add_entities)

        add_entities.assert_called_once()
        mock_registry.async_get_or_create.assert_called_once()
        _, call_kwargs = mock_registry.async_get_or_create.call_args
        assert call_kwargs["suggested_object_id"] == "device_abc_targettemperaturec"


class TestEntityDomainAndUniqueId:
    """Lines 243, 256, 258: entity_domain and unique_id fppn branches."""

    def test_entity_domain_returns_sensor(self):
        """Line 243: entity_domain returns 'sensor' for base ElectroluxSensor."""
        entity = make_entity(use_sensor=True)
        assert entity.entity_domain == "sensor"

    def test_unique_id_fppn_underscore_prefix(self):
        """Line 256: unique_id normalises fppn_ prefix."""
        entity = make_entity(entity_attr="fPPN_targetTemperatureC")
        uid = entity.unique_id
        # Should NOT contain fppn_ in the normalized part
        assert "fppn" not in uid.split("-")[1]

    def test_unique_id_fppn_no_underscore_prefix(self):
        """Line 258: unique_id normalises fppn prefix (no underscore)."""
        entity = make_entity(entity_attr="fPPNtargetTemperatureC")
        uid = entity.unique_id
        assert "fppn" not in uid.split("-")[1]

    def test_should_poll_returns_false(self):
        """Line 285: should_poll returns False."""
        entity = make_entity()
        assert entity.should_poll is False


class TestHandleCoordinatorUpdateEarlyExits:
    """Lines 294, 298: _handle_coordinator_update early returns."""

    def test_coordinator_data_none_returns_early(self):
        """Line 294: When coordinator.data is None, _handle_coordinator_update returns."""
        entity = make_entity()
        entity.coordinator.data = None  # type: ignore[assignment]
        entity.async_write_ha_state = MagicMock()

        # Should not raise
        entity._handle_coordinator_update()

        # async_write_ha_state should NOT be called (returned early)
        entity.async_write_ha_state.assert_not_called()

    def test_appliances_none_returns_early(self):
        """Line 298: When coordinator.data has no appliances key, returns early."""
        entity = make_entity()
        entity.coordinator.data = {"appliances": None}
        entity.async_write_ha_state = MagicMock()

        entity._handle_coordinator_update()

        entity.async_write_ha_state.assert_not_called()

    def test_appliances_key_missing_returns_early(self):
        """Line 298: When coordinator.data has no appliances, returns early."""
        entity = make_entity()
        entity.coordinator.data = {}  # no "appliances" key
        entity.async_write_ha_state = MagicMock()

        entity._handle_coordinator_update()

        entity.async_write_ha_state.assert_not_called()


class TestGetStateAttr:
    """Lines 337-342: get_state_attr method."""

    def test_path_with_slash_found_at_top_level(self):
        """Line 338-339: When '/' in path and full path exists in reported_state."""
        entity = make_entity(reported={"userSelections/programUID": "Cotton"})
        result = entity.get_state_attr("userSelections/programUID")
        assert result == "Cotton"

    def test_path_with_slash_found_via_nested(self):
        """Line 340-341: When '/' in path and nested lookup works."""
        entity = make_entity(reported={"userSelections": {"programUID": "Delicate"}})
        result = entity.get_state_attr("userSelections/programUID")
        assert result == "Delicate"

    def test_path_without_slash(self):
        """Line 342: Simple path without '/' reads directly from reported_state."""
        entity = make_entity(reported={"cyclePhase": "Rinse"})
        result = entity.get_state_attr("cyclePhase")
        assert result == "Rinse"

    def test_path_not_found_returns_none(self):
        """Returns None when path not found."""
        entity = make_entity(reported={})
        result = entity.get_state_attr("nonExistent")
        assert result is None


class TestEntityCategoryAndDeviceClass:
    """Lines 601, 606: entity_category and device_class properties."""

    def test_entity_category_returns_value(self):
        """Line 601: entity_category property returns _entity_category."""
        entity = make_entity()
        assert entity.entity_category == EntityCategory.CONFIG

    def test_device_class_returns_value(self):
        """Line 606: device_class property returns _device_class."""
        entity = make_entity()
        assert entity.device_class is None

    def test_device_class_when_set(self):
        """device_class returns set value."""
        from homeassistant.components.sensor import SensorDeviceClass

        coordinator, _ = make_coordinator()
        entity = ElectroluxSensor(
            coordinator=coordinator,
            name="Test",
            config_entry=coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SENSOR,
            entity_name="test",
            entity_attr="temperature",
            entity_source=None,
            capability={"access": "readwrite"},
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            entity_category=None,
            icon="mdi:thermometer",
        )
        assert entity.device_class == SensorDeviceClass.TEMPERATURE


class TestExtractValueDeepNestedBreak:
    """Lines 668-669: extract_value non-dict intermediate breaks path traversal."""

    def test_nested_path_non_dict_intermediate_returns_none(self):
        """Lines 668-669: When intermediate value is not a dict, break and return None."""
        entity = make_entity(
            entity_attr="programUID",
            entity_source="a/b/c",
            reported={"a": "not_a_dict"},  # 'a' is a string, not a dict
        )
        entity.is_connected = MagicMock(return_value=True)
        # Parts will be ["a", "b", "c"]. After "a": category="not_a_dict" (non-dict) → break
        result = entity.extract_value()
        assert result is None

    def test_nested_path_first_part_missing_returns_none(self):
        """When first part of nested source is missing from reported state."""
        entity = make_entity(
            entity_attr="programUID",
            entity_source="missing/deep",
            reported={},
        )
        entity.is_connected = MagicMock(return_value=True)
        result = entity.extract_value()
        assert result is None


class TestUpdateMethod:
    """Line 682: update() method sets appliance_status."""

    def test_update_sets_appliance_status(self):
        """Line 682: update() updates the appliance_status attribute."""
        entity = make_entity()
        new_status = {"properties": {"reported": {"targetTemperatureC": 70}}}

        entity.update(new_status)

        assert entity.appliance_status == new_status


class TestIsRemoteControlEnabledFalsyNonNone:
    """Line 741: return True when remote_control_status is falsy but not None."""

    def test_falsy_non_none_remote_control_returns_true(self):
        """Line 741: remote_control_status = False (falsy non-None) → return True."""
        entity = make_entity()
        entity.appliance_status = {"remoteControl": False}
        assert entity.is_remote_control_enabled() is True

    def test_empty_string_remote_control_returns_true(self):
        """Line 741: remote_control_status = '' (empty string) → return True."""
        entity = make_entity()
        entity.appliance_status = {"remoteControl": ""}
        assert entity.is_remote_control_enabled() is True

    def test_zero_remote_control_returns_true(self):
        """Line 741: remote_control_status = 0 → return True."""
        entity = make_entity()
        entity.appliance_status = {"remoteControl": 0}
        assert entity.is_remote_control_enabled() is True


class TestIsSupportedByProgramAlwaysSupported:
    """Lines 858-859: _is_supported_by_program for always-supported entity attrs."""

    def test_program_attr_always_supported(self):
        """Lines 858-859: entity_attr='program' is always supported."""
        entity = make_entity(entity_attr="program", reported={"program": "Cotton"})
        assert entity._is_supported_by_program() is True

    def test_programUID_attr_always_supported(self):
        """Lines 858-859: entity_attr='programUID' is always supported."""
        entity = make_entity(entity_attr="programUID", reported={"program": "Cotton"})
        assert entity._is_supported_by_program() is True

    def test_userselections_programUID_always_supported(self):
        """Lines 858-859: entity_attr='userSelections/programUID' is always supported."""
        entity = make_entity(
            entity_attr="userSelections/programUID",
            reported={"userSelections": {"programUID": "Cotton"}},
        )
        assert entity._is_supported_by_program() is True


class TestIsSupportedByProgramNoApplianceData:
    """Lines 966-967: _is_supported_by_program when appliance.data is None."""

    def test_no_appliance_data_returns_not_disabled(self):
        """Lines 966-967: When appliance.data is falsy, returns not disabled."""
        entity = make_entity(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton"},
        )
        # Set appliance.data = None so the data check fires
        mock_appliance = entity.coordinator.data[
            "appliances"
        ].get_appliance.return_value
        mock_appliance.data = None

        # Mock _get_program_capabilities so entity IS found in caps
        entity._get_program_capabilities = MagicMock(
            return_value={"targetTemperatureC": {"min": 30, "max": 90}}
        )

        result = entity._is_supported_by_program()
        assert result is True  # not disabled (disabled=False → not False = True)

    def test_no_appliance_capabilities_returns_not_disabled(self):
        """Lines 966-967: When appliance.data.capabilities is None."""
        entity = make_entity(
            entity_attr="targetTemperatureC",
            reported={"program": "Cotton"},
        )
        mock_data = MagicMock()
        mock_data.capabilities = None
        entity.coordinator.data["appliances"].get_appliance.return_value.data = (
            mock_data
        )

        # Mock _get_program_capabilities so entity IS found in caps
        entity._get_program_capabilities = MagicMock(
            return_value={"targetTemperatureC": {"min": 30, "max": 90}}
        )

        result = entity._is_supported_by_program()
        # capabilities is None → not (True and None) = True → return not disabled
        assert result is True


class TestGetProgramConstraintNoProgram:
    """Line 1050: _get_program_constraint returns None when no program_caps."""

    def test_returns_none_when_no_program_caps(self):
        """Line 1050: When _get_program_capabilities returns empty, returns None."""
        entity = make_entity(
            entity_attr="targetTemperatureC",
            reported={"program": "UnknownProgram"},
        )
        # _get_program_capabilities will return {} for unknown program
        mock_data = MagicMock()
        mock_data.capabilities = {
            "program": {"values": {}}  # UnknownProgram not in values
        }
        entity.coordinator.data["appliances"].get_appliance.return_value.data = (
            mock_data
        )

        result = entity._get_program_constraint("min")
        assert result is None

    def test_returns_none_when_no_current_program(self):
        """_get_program_constraint returns None when no program in reported state."""
        entity = make_entity(
            entity_attr="targetTemperatureC",
            reported={},  # no program
        )
        result = entity._get_program_constraint("min")
        assert result is None


class TestEvaluateTriggerConditionOperand2Dict:
    """Line 1112: _evaluate_trigger_condition when operand2 is a dict."""

    @pytest.fixture
    def entity(self):
        ent = make_entity(
            entity_attr="targetTemperatureC",
            reported={"mode": "cool", "steamMode": "on"},
        )
        ent._reported_state_cache = {"mode": "cool", "steamMode": "on"}
        return ent

    def test_operand2_as_dict_is_evaluated(self, entity):
        """Line 1112: operand2 is a dict → calls _evaluate_operand(operand2)."""
        # operand_2 is a dict that resolves to "cool" via the "operand_1" key lookup
        condition = {
            "operator": "eq",
            "operand_1": "cool",
            "operand_2": {"operand_1": "mode"},  # dict → resolved via _evaluate_operand
        }
        result = entity._evaluate_trigger_condition(condition, "mode")
        # operand2 dict resolves: {"operand_1": "mode"} → reported_state["mode"] = "cool"
        # "cool" == "cool" → True
        assert result is True

    def test_operand1_and_operand2_both_dicts(self, entity):
        """Both operands as dicts → both evaluated."""
        condition = {
            "operator": "eq",
            "operand_1": {"operand_1": "mode"},  # → "cool"
            "operand_2": {"operand_1": "steamMode"},  # → "on"
        }
        result = entity._evaluate_trigger_condition(condition, "steamMode")
        # "cool" == "on" → False
        assert result is False
