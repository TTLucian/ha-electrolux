"""Tests for the Electrolux sensor platform."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.util import dt as dt_util

from custom_components.electrolux.const import SENSOR
from custom_components.electrolux.sensor import ElectroluxSensor


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {"appliances": MagicMock()}
    coordinator.hass = MagicMock()
    coordinator.config_entry = MagicMock()
    coordinator._consecutive_auth_failures = 0
    coordinator._auth_failure_threshold = 3
    coordinator._last_time_to_end = {}
    coordinator._deferred_tasks = set()
    coordinator._deferred_tasks_by_appliance = {}
    return coordinator


@pytest.fixture
def basic_sensor_entity(mock_coordinator) -> ElectroluxSensor:
    """Create a basic sensor entity for testing."""
    capability = {"access": "read", "type": "number"}
    entity = ElectroluxSensor(
        coordinator=mock_coordinator,
        name="Test Sensor",
        config_entry=mock_coordinator.config_entry,
        pnc_id="TEST_PNC",
        entity_type=SENSOR,
        entity_name="testAttribute",
        entity_attr="testAttribute",
        entity_source=None,
        capability=capability,
        unit=None,
        device_class=None,
        entity_category=None,
        icon="mdi:test",
    )
    entity.hass = mock_coordinator.hass
    entity.appliance_status = {
        "applianceId": "test_appliance",
        "properties": {
            "reported": {"testAttribute": 25.0},
            "desired": {},
            "metadata": {},
        },
    }
    entity.reported_state = {"testAttribute": 25.0}
    return entity


class TestElectroluxSensor:

    def test_entity_domain(self, basic_sensor_entity: ElectroluxSensor):
        """Test sensor entity domain."""
        assert basic_sensor_entity.entity_domain == SENSOR

    def test_name_with_friendly_name(self, basic_sensor_entity: ElectroluxSensor):
        """Test sensor name uses friendly name when available."""
        basic_sensor_entity.entity_name = "connectivityState"
        assert basic_sensor_entity.name == "Connectivity State"

    def test_name_fallback_to_catalog(self, mock_coordinator):
        """Test sensor name falls back to catalog entry."""
        catalog = MagicMock()
        catalog.friendly_name = "Custom Sensor"
        capability = {"access": "read", "type": "number"}
        entity = ElectroluxSensor(
            coordinator=mock_coordinator,
            name="Test Sensor",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SENSOR,
            entity_name="testAttribute",
            entity_attr="testAttribute",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:test",
            catalog_entry=catalog,
        )
        entity.hass = mock_coordinator.hass
        assert entity.name == "Custom sensor"

    def test_name_fallback_to_internal(self, basic_sensor_entity: ElectroluxSensor):
        """Test sensor name falls back to internal name."""
        basic_sensor_entity.entity_name = "unknownSensor"
        assert basic_sensor_entity.name == "Test Sensor"

    def test_native_value_basic(self, basic_sensor_entity: ElectroluxSensor):
        """Test basic native value extraction."""
        assert basic_sensor_entity.native_value == 25.0

    def test_native_value_none_when_no_data(
        self, basic_sensor_entity: ElectroluxSensor
    ):
        """Test native value returns None when no data available."""
        basic_sensor_entity.reported_state = {}
        assert basic_sensor_entity.native_value is None

    def test_native_value_with_default(self, basic_sensor_entity: ElectroluxSensor):
        """Test native value uses default when no data available."""
        basic_sensor_entity.reported_state = {}
        basic_sensor_entity.capability = {
            "access": "read",
            "type": "number",
            "default": 100.0,
        }
        assert basic_sensor_entity.native_value == 100.0

    def test_suggested_display_precision_temperature(
        self, basic_sensor_entity: ElectroluxSensor
    ):
        """Test display precision for temperature sensors."""
        basic_sensor_entity.unit = UnitOfTemperature.CELSIUS
        assert basic_sensor_entity.suggested_display_precision == 2

    def test_suggested_display_precision_time(
        self, basic_sensor_entity: ElectroluxSensor
    ):
        """Test display precision for time sensors."""
        basic_sensor_entity.unit = UnitOfTime.SECONDS
        assert basic_sensor_entity.suggested_display_precision == 0

    def test_suggested_display_precision_none(
        self, basic_sensor_entity: ElectroluxSensor
    ):
        """Test display precision returns None for unknown units."""
        basic_sensor_entity.unit = "unknown"
        assert basic_sensor_entity.suggested_display_precision is None


class TestTimeToEndSensor:

    @pytest.fixture
    def time_to_end_entity(self, mock_coordinator) -> ElectroluxSensor:
        """Create a timeToEnd sensor entity."""
        capability = {"access": "read", "type": "number"}
        entity = ElectroluxSensor(
            coordinator=mock_coordinator,
            name="Time to End",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SENSOR,
            entity_name="timeToEnd",
            entity_attr="timeToEnd",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=None,
            icon="mdi:timer",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "applianceId": "test_appliance",
            "properties": {
                "reported": {"timeToEnd": 3600, "applianceState": "RUNNING"},
                "desired": {},
                "metadata": {},
            },
        }
        entity.reported_state = {"timeToEnd": 3600, "applianceState": "RUNNING"}
        return entity

    def test_time_to_end_shows_countdown_when_running(
        self, time_to_end_entity: ElectroluxSensor
    ):
        """Test timeToEnd shows countdown timestamp when appliance is running."""
        result = time_to_end_entity.native_value
        assert isinstance(result, datetime)
        # Should be approximately now + 3600 seconds (allow 2 second tolerance)
        now = dt_util.now()
        expected = now + timedelta(seconds=3600)
        assert abs((result - expected).total_seconds()) < 2

    def test_time_to_end_shows_countdown_when_paused(
        self, time_to_end_entity: ElectroluxSensor
    ):
        """Test timeToEnd shows countdown when appliance is paused."""
        time_to_end_entity.reported_state["applianceState"] = "PAUSED"
        result = time_to_end_entity.native_value
        assert isinstance(result, datetime)
        now = dt_util.now()
        expected = now + timedelta(seconds=3600)
        assert abs((result - expected).total_seconds()) < 2

    def test_time_to_end_shows_countdown_when_delayed_start(
        self, time_to_end_entity: ElectroluxSensor
    ):
        """Test timeToEnd shows countdown when appliance has delayed start."""
        time_to_end_entity.reported_state["applianceState"] = "DELAYED_START"
        result = time_to_end_entity.native_value
        assert isinstance(result, datetime)

    def test_time_to_end_shows_countdown_when_ready_to_start(
        self, time_to_end_entity: ElectroluxSensor
    ):
        """Test timeToEnd shows countdown when appliance is ready to start."""
        time_to_end_entity.reported_state["applianceState"] = "READY_TO_START"
        result = time_to_end_entity.native_value
        assert isinstance(result, datetime)

    def test_time_to_end_shows_countdown_when_end_of_cycle(
        self, time_to_end_entity: ElectroluxSensor
    ):
        """Test timeToEnd shows countdown when appliance is at end of cycle."""
        time_to_end_entity.reported_state["applianceState"] = "END_OF_CYCLE"
        result = time_to_end_entity.native_value
        assert isinstance(result, datetime)

    def test_time_to_end_none_when_stopped(self, time_to_end_entity: ElectroluxSensor):
        """Test timeToEnd returns None when appliance is stopped."""
        time_to_end_entity.reported_state["applianceState"] = "STOPPED"
        assert time_to_end_entity.native_value is None

    def test_time_to_end_none_when_idle(self, time_to_end_entity: ElectroluxSensor):
        """Test timeToEnd returns None when appliance is idle."""
        time_to_end_entity.reported_state["applianceState"] = "IDLE"
        assert time_to_end_entity.native_value is None

    def test_time_to_end_none_when_off(self, time_to_end_entity: ElectroluxSensor):
        """Test timeToEnd returns None when appliance is off."""
        time_to_end_entity.reported_state["applianceState"] = "POWEROFF"
        assert time_to_end_entity.native_value is None

    def test_time_to_end_none_when_value_is_negative_one(
        self, time_to_end_entity: ElectroluxSensor
    ):
        """Test timeToEnd returns None when value is -1 (not set)."""
        time_to_end_entity.reported_state["timeToEnd"] = -1
        assert time_to_end_entity.native_value is None

    def test_time_to_end_none_when_value_is_zero(
        self, time_to_end_entity: ElectroluxSensor
    ):
        """Test timeToEnd returns None when value is 0."""
        time_to_end_entity.reported_state["timeToEnd"] = 0
        assert time_to_end_entity.native_value is None

    def test_time_to_end_none_when_value_is_none(
        self, time_to_end_entity: ElectroluxSensor
    ):
        """Test timeToEnd returns None when value is None."""
        time_to_end_entity.reported_state["timeToEnd"] = None
        assert time_to_end_entity.native_value is None


class TestRunningTimeSensor:

    @pytest.fixture
    def running_time_entity(self, mock_coordinator) -> ElectroluxSensor:
        """Create a runningTime sensor entity."""
        capability = {"access": "read", "type": "number"}
        entity = ElectroluxSensor(
            coordinator=mock_coordinator,
            name="Running Time",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SENSOR,
            entity_name="runningTime",
            entity_attr="runningTime",
            entity_source=None,
            capability=capability,
            unit=UnitOfTime.SECONDS,
            device_class=SensorDeviceClass.DURATION,
            entity_category=None,
            icon="mdi:timer",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "applianceId": "test_appliance",
            "properties": {
                "reported": {"runningTime": 1800, "applianceState": "RUNNING"},
                "desired": {},
                "metadata": {},
            },
        }
        entity.reported_state = {"runningTime": 1800, "applianceState": "RUNNING"}
        return entity

    def test_running_time_shows_elapsed_when_running(
        self, running_time_entity: ElectroluxSensor
    ):
        """Test runningTime shows elapsed seconds when appliance is running."""
        result = running_time_entity.native_value
        assert result == 1800

    def test_running_time_shows_elapsed_when_paused(
        self, running_time_entity: ElectroluxSensor
    ):
        """Test runningTime shows elapsed seconds when appliance is paused."""
        running_time_entity.reported_state["applianceState"] = "PAUSED"
        result = running_time_entity.native_value
        assert result == 1800

    def test_running_time_none_when_stopped(
        self, running_time_entity: ElectroluxSensor
    ):
        """Test runningTime returns None when appliance is stopped."""
        running_time_entity.reported_state["applianceState"] = "STOPPED"
        assert running_time_entity.native_value is None

    def test_running_time_none_when_idle(self, running_time_entity: ElectroluxSensor):
        """Test runningTime returns None when appliance is idle."""
        running_time_entity.reported_state["applianceState"] = "IDLE"
        assert running_time_entity.native_value is None

    def test_running_time_none_when_off(self, running_time_entity: ElectroluxSensor):
        """Test runningTime returns None when appliance is off."""
        running_time_entity.reported_state["applianceState"] = "POWEROFF"
        assert running_time_entity.native_value is None

    def test_running_time_zero_when_just_started(
        self, running_time_entity: ElectroluxSensor
    ):
        """Test runningTime shows 0 when appliance just started."""
        running_time_entity.reported_state["runningTime"] = 0
        # 0 is valid for just-started appliance
        assert running_time_entity.native_value == 0

    def test_running_time_none_when_value_is_negative_one(
        self, running_time_entity: ElectroluxSensor
    ):
        """Test runningTime returns None when value is -1 (not set)."""
        running_time_entity.reported_state["runningTime"] = -1
        assert running_time_entity.native_value is None

    def test_running_time_none_when_value_is_none(
        self, running_time_entity: ElectroluxSensor
    ):
        """Test runningTime returns None when value is None."""
        running_time_entity.reported_state["runningTime"] = None
        assert running_time_entity.native_value is None


class TestAlertsSensor:

    @pytest.fixture
    def alerts_entity(self, mock_coordinator) -> ElectroluxSensor:
        """Create an alerts sensor entity."""
        capability = {
            "access": "read",
            "type": "array",
            "values": {
                "ERROR_CODE_1": "Error code 1 description",
                "ERROR_CODE_2": "Error code 2 description",
                "WARNING_CODE_1": "Warning code 1 description",
            },
        }
        entity = ElectroluxSensor(
            coordinator=mock_coordinator,
            name="Alerts",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SENSOR,
            entity_name="alerts",
            entity_attr="alerts",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:alert",
        )
        entity.hass = mock_coordinator.hass
        entity.config_entry = mock_coordinator.config_entry
        entity.appliance_status = {
            "applianceId": "test_appliance",
            "properties": {
                "reported": {"alerts": []},
                "desired": {},
                "metadata": {},
            },
        }
        entity.reported_state = {"alerts": []}
        return entity

    def test_alerts_returns_count_when_list(self, alerts_entity: ElectroluxSensor):
        """Test alerts sensor returns count of alerts."""
        alerts_entity.reported_state["alerts"] = [
            {
                "code": "ERROR_CODE_1",
                "severity": "ERROR",
                "acknowledgeStatus": "UNACKNOWLEDGED",
            },
            {
                "code": "WARNING_CODE_1",
                "severity": "WARNING",
                "acknowledgeStatus": "ACKNOWLEDGED",
            },
        ]
        assert alerts_entity.native_value == 2

    def test_alerts_returns_zero_when_empty_list(self, alerts_entity: ElectroluxSensor):
        """Test alerts sensor returns 0 when no alerts."""
        assert alerts_entity.native_value == 0

    def test_alerts_returns_zero_when_not_list(self, alerts_entity: ElectroluxSensor):
        """Test alerts sensor returns 0 when value is not a list."""
        alerts_entity.reported_state["alerts"] = "invalid"
        assert alerts_entity.native_value == 0

    def test_alerts_extra_state_attributes_empty(self, alerts_entity: ElectroluxSensor):
        """Test alerts extra attributes shows all OFF when no alerts."""
        attributes = alerts_entity.extra_state_attributes
        assert attributes == {
            "ERROR_CODE_1": "OFF",
            "ERROR_CODE_2": "OFF",
            "WARNING_CODE_1": "OFF",
        }

    def test_alerts_extra_state_attributes_with_alerts(
        self, alerts_entity: ElectroluxSensor
    ):
        """Test alerts extra attributes shows alert details."""
        alerts_entity.reported_state["alerts"] = [
            {
                "code": "ERROR_CODE_1",
                "severity": "CRITICAL",
                "acknowledgeStatus": "UNACKNOWLEDGED",
            },
        ]
        attributes = alerts_entity.extra_state_attributes
        assert attributes == {
            "ERROR_CODE_1": "CRITICAL-UNACKNOWLEDGED",
            "ERROR_CODE_2": "OFF",
            "WARNING_CODE_1": "OFF",
        }

    def test_alerts_extra_state_attributes_multiple_alerts(
        self, alerts_entity: ElectroluxSensor
    ):
        """Test alerts extra attributes with multiple active alerts."""
        alerts_entity.reported_state["alerts"] = [
            {
                "code": "ERROR_CODE_1",
                "severity": "ERROR",
                "acknowledgeStatus": "UNACKNOWLEDGED",
            },
            {
                "code": "WARNING_CODE_1",
                "severity": "WARNING",
                "acknowledgeStatus": "ACKNOWLEDGED",
            },
        ]
        attributes = alerts_entity.extra_state_attributes
        assert attributes == {
            "ERROR_CODE_1": "ERROR-UNACKNOWLEDGED",
            "ERROR_CODE_2": "OFF",
            "WARNING_CODE_1": "WARNING-ACKNOWLEDGED",
        }


class TestValueMapping:

    @pytest.fixture
    def mapped_sensor_entity(self, mock_coordinator) -> ElectroluxSensor:
        """Create a sensor entity with value mapping."""
        catalog = MagicMock()
        catalog.friendly_name = "Appliance State"
        catalog.value_mapping = {
            1: "RUNNING",
            2: "PAUSED",
            3: "STOPPED",
        }
        capability = {"access": "read", "type": "number"}
        entity = ElectroluxSensor(
            coordinator=mock_coordinator,
            name="Mapped Sensor",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SENSOR,
            entity_name="testAttribute",
            entity_attr="testAttribute",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:test",
            catalog_entry=catalog,
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "applianceId": "test_appliance",
            "properties": {
                "reported": {"testAttribute": 1},
                "desired": {},
                "metadata": {},
            },
        }
        entity.reported_state = {"testAttribute": 1}
        return entity

    def test_value_mapping_converts_integer_to_string(
        self, mapped_sensor_entity: ElectroluxSensor
    ):
        """Test value mapping converts integer to mapped string."""
        # String values are always title-cased in sensor
        assert mapped_sensor_entity.native_value == "Running"

    def test_value_mapping_returns_original_if_not_in_map(
        self, mapped_sensor_entity: ElectroluxSensor
    ):
        """Test value mapping returns original value if not in mapping."""
        mapped_sensor_entity.reported_state["testAttribute"] = 99
        assert mapped_sensor_entity.native_value == 99

    def test_string_formatting_replaces_underscores(
        self, basic_sensor_entity: ElectroluxSensor
    ):
        """Test string values have underscores replaced with spaces."""
        basic_sensor_entity.reported_state["testAttribute"] = "STEAM_TANK_FULL"
        assert basic_sensor_entity.native_value == "Steam Tank Full"

    def test_string_formatting_title_case(self, basic_sensor_entity: ElectroluxSensor):
        """Test string values are title-cased."""
        basic_sensor_entity.reported_state["testAttribute"] = "running"
        assert basic_sensor_entity.native_value == "Running"


class TestTimeUnitConversion:

    @pytest.fixture
    def time_sensor_entity(self, mock_coordinator) -> ElectroluxSensor:
        """Create a time sensor entity."""
        capability = {"access": "read", "type": "number"}
        entity = ElectroluxSensor(
            coordinator=mock_coordinator,
            name="Time Sensor",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=SENSOR,
            entity_name="testAttribute",
            entity_attr="testAttribute",
            entity_source=None,
            capability=capability,
            unit=UnitOfTime.MINUTES,
            device_class=None,
            entity_category=None,
            icon="mdi:timer",
        )
        entity.hass = mock_coordinator.hass
        entity.appliance_status = {
            "applianceId": "test_appliance",
            "properties": {
                "reported": {"testAttribute": 180},  # 180 seconds = 3 minutes
                "desired": {},
                "metadata": {},
            },
        }
        entity.reported_state = {"testAttribute": 180}
        return entity

    def test_time_conversion_seconds_to_minutes(
        self, time_sensor_entity: ElectroluxSensor
    ):
        """Test time values are converted from seconds to minutes."""
        assert time_sensor_entity.native_value == 3.0

    def test_time_conversion_returns_none_for_zero(
        self, time_sensor_entity: ElectroluxSensor
    ):
        """Test time values return None when 0."""
        time_sensor_entity.reported_state["testAttribute"] = 0
        assert time_sensor_entity.native_value is None

    def test_time_conversion_returns_none_for_negative_one(
        self, time_sensor_entity: ElectroluxSensor
    ):
        """Test time values return None when -1 (unset)."""
        time_sensor_entity.reported_state["testAttribute"] = -1
        assert time_sensor_entity.native_value is None

    def test_time_conversion_handles_float_values(
        self, time_sensor_entity: ElectroluxSensor
    ):
        """Test time conversion handles float values."""
        time_sensor_entity.reported_state["testAttribute"] = (
            120.0  # 2.0 minutes exactly
        )
        result = time_sensor_entity.native_value
        assert isinstance(result, float)
        assert result == 2.0


class TestConstantAccessSensors:

    def test_constant_access_uses_default_value(
        self, basic_sensor_entity: ElectroluxSensor
    ):
        """Test sensors with constant access use default value."""
        basic_sensor_entity.capability = {
            "access": "constant",
            "type": "string",
            "default": "CONSTANT_VALUE",
        }
        basic_sensor_entity.reported_state = {}
        # String values are title-cased with underscores replaced
        assert basic_sensor_entity.native_value == "Constant Value"

    def test_constant_access_overridden_by_live_data_for_special_keys(
        self, basic_sensor_entity: ElectroluxSensor
    ):
        """Test special sensors use live data even with constant access."""
        basic_sensor_entity.entity_key = "ovwater_tank_empty"
        basic_sensor_entity.entity_attr = "waterTankEmpty"
        basic_sensor_entity.reported_state = {"waterTankEmpty": "STEAM_TANK_EMPTY"}
        basic_sensor_entity.capability = {
            "access": "constant",
            "type": "boolean",
            "default": False,
        }
        # When waterTankEmpty is not STEAM_TANK_FULL, tank is empty (True)
        assert basic_sensor_entity.native_value is True
