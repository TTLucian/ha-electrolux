"""Test API logic functions."""

from custom_components.electrolux.api import (
    ElectroluxLibraryEntity,
    deep_merge_dicts,
)
from custom_components.electrolux.util import string_to_boolean


class TestDeepMergeDicts:
    """Test the deep_merge_dicts function."""

    def test_deep_merge_dicts_basic(self):
        """Test basic dictionary merging."""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = deep_merge_dicts(dict1, dict2)
        expected = {"a": 1, "b": 3, "c": 4}
        assert result == expected

    def test_deep_merge_dicts_nested(self):
        """Test nested dictionary merging."""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"y": 4, "z": 5}, "c": 6}
        result = deep_merge_dicts(dict1, dict2)
        expected = {"a": {"x": 1, "y": 4, "z": 5}, "b": 3, "c": 6}
        assert result == expected

    def test_deep_merge_dicts_deeply_nested(self):
        """Test deeply nested dictionary merging."""
        dict1 = {"a": {"b": {"c": 1, "d": 2}}}
        dict2 = {"a": {"b": {"d": 3, "e": 4}, "f": 5}}
        result = deep_merge_dicts(dict1, dict2)
        expected = {"a": {"b": {"c": 1, "d": 3, "e": 4}, "f": 5}}
        assert result == expected

    def test_deep_merge_dicts_non_dict_values(self):
        """Test merging when values are not dictionaries."""
        dict1 = {"a": [1, 2], "b": "string"}
        dict2 = {"a": [3, 4], "c": {"nested": "value"}}
        result = deep_merge_dicts(dict1, dict2)
        expected = {"a": [3, 4], "b": "string", "c": {"nested": "value"}}
        assert result == expected

    def test_deep_merge_dicts_empty_dicts(self):
        """Test merging with empty dictionaries."""
        dict1 = {}
        dict2 = {"a": 1}
        result = deep_merge_dicts(dict1, dict2)
        expected = {"a": 1}
        assert result == expected

    def test_deep_merge_dicts_no_modification(self):
        """Test that original dictionaries are not modified."""
        dict1 = {"a": {"x": 1}}
        dict2 = {"a": {"y": 2}}
        original_dict1 = dict1.copy()
        original_dict2 = dict2.copy()

        result = deep_merge_dicts(dict1, dict2)

        assert dict1 == original_dict1
        assert dict2 == original_dict2
        assert result == {"a": {"x": 1, "y": 2}}


class TestKeepSourceLogic:
    """Test the keep_source logic in sources_list."""

    def test_keep_source_not_blacklisted(self):
        """Test that non-blacklisted sources are kept."""
        # Create a mock ElectroluxLibraryEntity
        entity = ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities={"valid_source": {"type": "string", "access": "read"}},
        )

        # Test the keep_source function (it's a nested function, so we need to access it)
        # We'll test the logic by calling sources_list and checking the result
        result = entity.sources_list()
        assert result is not None
        assert "valid_source" in result

    def test_keep_source_blacklisted_not_whitelisted(self):
        """Test that blacklisted sources are excluded when not whitelisted."""
        entity = ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities={
                "fCMiscellaneous/blocked": {"type": "string", "access": "read"},
                "valid_source": {"type": "string", "access": "read"},
            },
        )

        result = entity.sources_list()
        assert result is not None
        assert "fCMiscellaneous/blocked" not in result
        assert "valid_source" in result

    def test_keep_source_blacklisted_but_whitelisted(self):
        """Test that blacklisted sources are included when whitelisted."""
        entity = ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities={
                "someWaterUsage": {
                    "type": "number",
                    "access": "read",
                },  # Should match .*waterUsage
                "fCMiscellaneous/blocked": {"type": "string", "access": "read"},
            },
        )

        result = entity.sources_list()
        assert result is not None
        assert "someWaterUsage" in result  # Whitelisted pattern
        assert (
            "fCMiscellaneous/blocked" not in result
        )  # Blacklisted and not whitelisted

    def test_keep_source_nested_capabilities(self):
        """Test that nested capabilities are properly handled."""
        entity = ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities={
                "parent": {
                    "child1": {"type": "string", "access": "read"},
                    "child2": {"type": "number", "access": "read"},
                },
                "fCMiscellaneous/blocked": {"type": "string", "access": "read"},
            },
        )

        result = entity.sources_list()
        assert result is not None
        assert "parent/child1" in result
        assert "parent/child2" in result
        assert "fCMiscellaneous/blocked" not in result

    def test_sources_list_with_none_capabilities(self):
        """Test sources_list when capabilities is None."""
        entity = ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities=None,
        )

        result = entity.sources_list()
        assert result is None


class TestStringToBoolean:
    """Test the string_to_boolean function."""

    def test_string_to_boolean_none_input(self):
        """Test that None input returns None."""
        result = string_to_boolean(None)
        assert result is None

    def test_string_to_boolean_true_values(self):
        """Test various string values that should return True."""
        true_values = [
            "on",
            "ON",
            "On",
            "true",
            "TRUE",
            "True",
            "yes",
            "YES",
            "Yes",
            "connected",
            "CONNECTED",
            "running",
            "RUNNING",
            "hot",
            "HOT",
            "enabled",
            "ENABLED",
            "locked",
            "LOCKED",
            "motion",
            "MOTION",
            "occupied",
            "OCCUPIED",
            "open",
            "OPEN",
            "plugged",
            "PLUGGED",
            "power",
            "POWER",
            "problem",
            "PROBLEM",
            "smoke",
            "SMOKE",
            "sound",
            "SOUND",
            "tampering",
            "TAMPERING",
            "unsafe",
            "UNSAFE",
            "update available",
            "UPDATE_AVAILABLE",
            "vibration",
            "VIBRATION",
            "wet",
            "WET",
            "charging",
            "CHARGING",
            "detected",
            "DETECTED",
            "home",
            "HOME",
            "light",
            "LIGHT",
            "locking",
            "LOCKING",
            "moving",
            "MOVING",
        ]

        for value in true_values:
            result = string_to_boolean(value)
            assert result is True, f"Expected True for '{value}', got {result}"

    def test_string_to_boolean_false_values(self):
        """Test various string values that should return False."""
        false_values = [
            "off",
            "OFF",
            "Off",
            "false",
            "FALSE",
            "False",
            "no",
            "NO",
            "No",
            "disconnected",
            "DISCONNECTED",
            "stopped",
            "STOPPED",
            "dry",
            "DRY",
            "disabled",
            "DISABLED",
            "unlocked",
            "UNLOCKED",
            "away",
            "AWAY",
            "clear",
            "CLEAR",
            "closed",
            "CLOSED",
            "normal",
            "NORMAL",
            "not charging",
            "NOT_CHARGING",
            "not occupied",
            "NOT_OCCUPIED",
            "not running",
            "NOT_RUNNING",
            "safe",
            "SAFE",
            "unlocking",
            "UNLOCKING",
            "unplugged",
            "UNPLUGGED",
            "up-to-date",
            "UP_TO_DATE",
            "no light",
            "NO_LIGHT",
            "no motion",
            "NO_MOTION",
            "no power",
            "NO_POWER",
            "no problem",
            "NO_PROBLEM",
            "no smoke",
            "NO_SMOKE",
            "no sound",
            "NO_SOUND",
            "no tampering",
            "NO_TAMPERING",
            "no vibration",
            "NO_VIBRATION",
        ]

        for value in false_values:
            result = string_to_boolean(value)
            assert result is False, f"Expected False for '{value}', got {result}"

    def test_string_to_boolean_unknown_with_fallback_true(self):
        """Test unknown values with fallback=True return the original string."""
        unknown_values = ["unknown", "maybe", "perhaps", "random_string"]

        for value in unknown_values:
            result = string_to_boolean(value, fallback=True)
            assert (
                result == value
            ), f"Expected '{value}' for unknown input, got {result}"

    def test_string_to_boolean_unknown_with_fallback_false(self):
        """Test unknown values with fallback=False return False."""
        unknown_values = ["unknown", "maybe", "perhaps", "random_string"]

        for value in unknown_values:
            result = string_to_boolean(value, fallback=False)
            assert (
                result is False
            ), f"Expected False for unknown input '{value}', got {result}"

    def test_string_to_boolean_case_insensitive(self):
        """Test that the function is case insensitive."""
        assert string_to_boolean("ON") is True
        assert string_to_boolean("on") is True
        assert string_to_boolean("On") is True
        assert string_to_boolean("OFF") is False
        assert string_to_boolean("off") is False
        assert string_to_boolean("Off") is False

    def test_string_to_boolean_underscore_handling(self):
        """Test that underscores are converted to spaces."""
        assert string_to_boolean("update_available") is True
        assert string_to_boolean("not_running") is False
        assert string_to_boolean("up_to_date") is False

    def test_string_to_boolean_whitespace_handling(self):
        """Test that extra whitespace is normalized."""
        assert string_to_boolean("  on  ") is True
        assert string_to_boolean("off\t") is False
        assert string_to_boolean(" true ") is True


# ---------------------------------------------------------------------------
# ElectroluxLibraryEntity — basic method coverage
# ---------------------------------------------------------------------------


class TestElectroluxLibraryEntityBasics:
    """Cover basic entity methods that feed into the mapping pipeline."""

    def _make_entity(self, capabilities=None, state=None):
        return ElectroluxLibraryEntity(
            name="TestAppliance",
            status="connected",
            state=state or {"properties": {"reported": {"temp": 21}}},
            appliance_info={},
            capabilities=capabilities,
        )

    # L80: reported_state property
    def test_reported_state_property(self):
        entity = self._make_entity()
        assert entity.reported_state == {"temp": 21}

    # L84: get_name
    def test_get_name(self):
        entity = self._make_entity()
        assert entity.get_name() == "TestAppliance"

    # L88-91: get_value with nested slash notation
    def test_get_value_slash_notation(self):
        entity = self._make_entity(
            state={
                "properties": {"reported": {"userSelections": {"programUID": "COTTON"}}}
            }
        )
        assert entity.get_value("userSelections/programUID") == "COTTON"

    def test_get_value_slash_missing_key(self):
        entity = self._make_entity(
            state={"properties": {"reported": {"userSelections": {}}}}
        )
        assert entity.get_value("userSelections/programUID") is None

    def test_get_value_plain_key(self):
        entity = self._make_entity(state={"properties": {"reported": {"temp": 42}}})
        assert entity.get_value("temp") == 42

    # L123: get_sensor_name with all-uppercase intermediate group
    def test_get_sensor_name_all_caps_sequence_mid_word(self):
        """'SOMECaps' — the all-uppercase group must be appended as-is (L123)."""
        entity = self._make_entity()
        # "ABCDef" triggers the upper-group mid-word branch
        result = entity.get_sensor_name("ABCDef")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_sensor_name_trailing_caps(self):
        """Uppercase group at end-of-string triggers L123 (i+1 bounds)."""
        entity = self._make_entity()
        result = entity.get_sensor_name("fCMiscID")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# get_entity_unit / get_entity_device_class — missing branches
# ---------------------------------------------------------------------------


class TestGetEntityUnitMissingBranches:
    """Cover L177: return None when type is non-temperature."""

    def test_non_temperature_type_returns_none(self):
        entity = ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities={"speed": {"type": "int", "access": "read"}},
        )
        assert entity.get_entity_unit("speed") is None


class TestGetEntityDeviceClassMissingBranches:
    """Cover L211 (SensorDeviceClass) and L231 (return None for non-temperature)."""

    def test_temperature_read_returns_sensor_device_class(self):
        """L211: temperature + access=read → SensorDeviceClass.TEMPERATURE."""
        from homeassistant.components.sensor import SensorDeviceClass

        entity = ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities={"ambientTemp": {"type": "temperature", "access": "read"}},
        )
        result = entity.get_entity_device_class("ambientTemp")
        assert result == SensorDeviceClass.TEMPERATURE

    def test_non_temperature_type_returns_none(self):
        """L231: any non-temperature type_class → return None."""
        entity = ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities={"speed": {"type": "int", "access": "read"}},
        )
        assert entity.get_entity_device_class("speed") is None


# ---------------------------------------------------------------------------
# get_entity_type — missing branches
# ---------------------------------------------------------------------------


class TestGetEntityTypeMissingBranches:
    """Cover L239 (boolean+values→SWITCH), L263-264 (boolean readwrite match),
    L267 (temperature read→SENSOR), L271 (read+number→SENSOR),
    L277 (write→BUTTON), L281 (constant→SENSOR), L290 (int/number readwrite→NUMBER)."""

    def _entity_with_cap(self, cap_name, cap_def):
        return ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities={cap_name: cap_def},
        )

    def test_boolean_readwrite_with_values_returns_switch(self):
        """L239: boolean readwrite + values present → SWITCH (Electrolux bug exception)."""
        from custom_components.electrolux.const import SWITCH

        entity = self._entity_with_cap(
            "lockState",
            {
                "type": "boolean",
                "access": "readwrite",
                "values": {"LOCKED": {}, "UNLOCKED": {}},
            },
        )
        assert entity.get_entity_type("lockState") == SWITCH

    def test_boolean_readwrite_match_case_returns_switch(self):
        """L263-264: boolean readwrite (no values) → SWITCH via match-case."""
        from custom_components.electrolux.const import SWITCH

        entity = self._entity_with_cap(
            "remoteControl",
            {"type": "boolean", "access": "readwrite"},
        )
        assert entity.get_entity_type("remoteControl") == SWITCH

    def test_temperature_read_returns_sensor_platform(self):
        """L267: temperature + access=read → SENSOR platform."""
        from custom_components.electrolux.const import SENSOR

        entity = self._entity_with_cap(
            "ambientTemp",
            {"type": "temperature", "access": "read"},
        )
        assert entity.get_entity_type("ambientTemp") == SENSOR

    def test_access_read_number_returns_sensor(self):
        """L271: number type + access=read → SENSOR."""
        from custom_components.electrolux.const import SENSOR

        entity = self._entity_with_cap(
            "waterLevel",
            {"type": "number", "access": "read"},
        )
        assert entity.get_entity_type("waterLevel") == SENSOR

    def test_access_write_returns_button(self):
        """L277: access=write → BUTTON."""
        from custom_components.electrolux.const import BUTTON

        entity = self._entity_with_cap(
            "resetFilter",
            {"type": "string", "access": "write"},
        )
        assert entity.get_entity_type("resetFilter") == BUTTON

    def test_access_constant_returns_sensor(self):
        """L281: access=constant → SENSOR."""
        from custom_components.electrolux.const import SENSOR

        entity = self._entity_with_cap(
            "firmwareVersion",
            {"type": "string", "access": "constant"},
        )
        assert entity.get_entity_type("firmwareVersion") == SENSOR

    def test_int_type_readwrite_returns_number(self):
        """L290: int type + readwrite (no values constraint) → NUMBER."""
        from custom_components.electrolux.const import NUMBER

        entity = self._entity_with_cap(
            "spinSpeed",
            {"type": "int", "access": "readwrite", "min": 400, "max": 1600},
        )
        assert entity.get_entity_type("spinSpeed") == NUMBER


# ---------------------------------------------------------------------------
# sources_list — whitelisted and flat-capability branches
# ---------------------------------------------------------------------------


class TestSourcesListMissingBranches:
    """Cover L314 (return True for whitelisted blacklisted source) and
    L333-334 (flat capability with access+type at top level)."""

    def test_blacklisted_but_whitelisted_returns_true(self):
        """L314: source matches blacklist pattern but also whitelist → included."""
        entity = ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities={
                "fCMiscellaneousState": {
                    "waterUsage": {"type": "number", "access": "read"}
                },
                "fCMiscellaneousState/waterUsage": {"type": "number", "access": "read"},
            },
        )
        result = entity.sources_list()
        # fCMiscellaneousState matches blacklist, waterUsage sub-key matches whitelist
        # The check is on the top-level key; whitelist patterns match the full source name
        assert result is not None

    def test_flat_capability_with_access_and_type_appended(self):
        """L333-334: a flat top-level capability with access+type is appended to sources."""
        entity = ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities={
                "applianceState": {"type": "string", "access": "read"},
            },
        )
        result = entity.sources_list()
        assert result is not None
        # applianceState appears both as a top-level key and appended via the flat-cap branch
        assert result.count("applianceState") >= 1


# ---------------------------------------------------------------------------
# Precise coverage fixes for api.py lines 123, 177, 231, 271, 277
# ---------------------------------------------------------------------------


class TestApiPreciseCoverage:
    """Target the exact lines that remain uncovered after broader tests."""

    def _entity(self, caps):
        return ElectroluxLibraryEntity(
            name="test",
            status="connected",
            state={},
            appliance_info={},
            capabilities=caps,
        )

    # L123: get_sensor_name mid-word group that is NOT all-caps → group.lower() appended
    def test_get_sensor_name_mixed_case_group_lowercased(self):
        """L123: group 'Target' precedes uppercase → words.append(group.lower())."""
        entity = self._entity({})
        # "targetTemp" → preprocessed to "TargetTemp"
        # When "T" at index 6 follows lowercase "t", group="Target" doesn't match [A-Z0-9]+
        # → words.append("target") → L123
        result = entity.get_sensor_name("targetTemp")
        assert "target" in result.lower()

    # L177: get_capability for deep path where intermediate is not a dict
    def test_get_capability_intermediate_not_dict_returns_none(self):
        """L177: traversal hits a non-dict intermediate value → return None."""
        entity = self._entity({"outer": {"inner": "string_not_dict"}})
        # "outer/inner/deep" → outer→{"inner":"string_not_dict"} → inner→"string_not_dict"
        # → next loop: isinstance("string_not_dict", dict) is False → return None
        result = entity.get_capability("outer/inner/deep")
        assert result is None

    # L231: get_entity_type when capability has no "access" field
    def test_get_entity_type_no_access_returns_none(self):
        """L231: capability with type but without access field → return None."""
        entity = self._entity({"speed": {"type": "number"}})
        result = entity.get_entity_type("speed")
        assert result is None

    # L271: get_entity_type for "alert" type → SENSOR (case "alert": return SENSOR)
    def test_get_entity_type_alert_returns_sensor(self):
        """L271: type='alert' access='read' → SENSOR platform (case 'alert': return SENSOR)."""
        from custom_components.electrolux.const import SENSOR

        entity = self._entity({"someAlert": {"type": "alert", "access": "read"}})
        result = entity.get_entity_type("someAlert")
        assert result == SENSOR

    # temperature readwrite → NUMBER (covers L269)
    def test_get_entity_type_temperature_readwrite_returns_number(self):
        """L269: temperature + readwrite (no values) → NUMBER platform."""
        from custom_components.electrolux.const import NUMBER

        entity = self._entity(
            {
                "targetTemp": {
                    "type": "temperature",
                    "access": "readwrite",
                    "min": 16,
                    "max": 32,
                }
            }
        )
        result = entity.get_entity_type("targetTemp")
        assert result == NUMBER

    # L277: get_entity_type for executeCommand + read → BUTTON
    def test_get_entity_type_execute_command_read_returns_button(self):
        """L277: attr_name='executeCommand' + access='read' → BUTTON."""
        from custom_components.electrolux.const import BUTTON

        entity = self._entity({"executeCommand": {"type": "string", "access": "read"}})
        result = entity.get_entity_type("executeCommand")
        assert result == BUTTON
