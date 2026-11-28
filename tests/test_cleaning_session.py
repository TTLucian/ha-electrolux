"""Tests for the PUREi9 last-cleaning-run tracker and sensors."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.electrolux.cleaning_session import (
    CleaningRunTracker,
    ElectroluxLastCleaningSensor,
    create_last_cleaning_sensors,
)

T0 = datetime(2026, 11, 18, 7, 0, 1, tzinfo=UTC)


def _at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def _run(tracker: CleaningRunTracker, steps: list[tuple[float, Any, Any]]) -> None:
    for minute, status, counter in steps:
        tracker.update(status, counter, _at(minute))


class TestCleaningRunTracker:
    def test_run_as_in_the_app(self):
        """The run the app lists as 36 min, ~29 m², 0 recharges."""
        tracker = CleaningRunTracker()
        _run(
            tracker,
            [
                (-5, 10, 366.0),  # sleeping on the dock
                (0, 1, 366.0),  # cleaning
                (34.3, 5, 366.0),  # returning
                (35.7, 9, 366.0),  # docked, counter not updated yet
            ],
        )
        run = tracker.last
        assert run is not None
        assert run.start == T0
        assert run.end == _at(35.7)
        assert run.duration_minutes == 36
        assert run.recharges == 0
        assert run.area == 0.0
        # the robot updates the counter a few seconds after docking
        assert tracker.update(9, 396.39, _at(35.8)) is True
        assert run.area == 30.4

    def test_recharges_are_counted_once_per_pitstop(self):
        tracker = CleaningRunTracker()
        _run(
            tracker,
            [(0, 10, 0), (1, 1, 0), (10, 7, 0), (11, 12, 0), (40, 12, 0), (41, 1, 0), (60, 7, 0), (62, 12, 0)],
        )
        _run(tracker, [(90, 1, 0), (100, 5, 0), (101, 10, 80)])
        assert tracker.last is not None
        assert tracker.last.recharges == 2
        assert tracker.last.area == 80.0

    def test_spot_cleaning_starts_a_run(self):
        tracker = CleaningRunTracker()
        _run(tracker, [(0, 10, 5), (1, 3, 5), (3, 9, 6)])
        assert tracker.last is not None
        assert tracker.last.duration_minutes == 2

    def test_restart_in_the_middle_of_returning_does_not_start_a_run(self):
        tracker = CleaningRunTracker()
        _run(tracker, [(0, 5, 10), (1, 9, 12)])
        assert tracker.last is None
        assert tracker.current is None

    def test_first_seen_cleaning_starts_a_run(self):
        tracker = CleaningRunTracker()
        _run(tracker, [(0, 1, 10), (5, 10, 12)])
        assert tracker.last is not None
        assert tracker.last.area == 2.0

    def test_resume_after_pause_is_the_same_run(self):
        tracker = CleaningRunTracker()
        _run(tracker, [(0, 10, 0), (1, 1, 0), (5, 2, 0), (8, 1, 0), (20, 10, 10)])
        assert tracker.last is not None
        assert tracker.last.start == _at(1)

    def test_missing_counter_and_invalid_values(self):
        tracker = CleaningRunTracker()
        _run(tracker, [(0, 10, None), (1, "1", None), (2, True, "x"), (3, None, None), (4, 10, None)])
        assert tracker.last is not None
        assert tracker.last.area is None
        assert tracker.last.duration_minutes == 3

    def test_counter_seen_late_is_used_as_start(self):
        tracker = CleaningRunTracker()
        _run(tracker, [(0, 10, None), (1, 1, None), (2, 1, 100.0), (10, 10, 104.0)])
        assert tracker.last is not None
        assert tracker.last.area == 4.0

    def test_next_run_replaces_the_last(self):
        tracker = CleaningRunTracker()
        _run(tracker, [(0, 10, 0), (1, 1, 0), (5, 10, 3)])
        _run(tracker, [(60, 1, 3), (70, 10, 9)])
        assert tracker.last is not None
        assert tracker.last.start == _at(60)
        assert tracker.last.area == 6.0

    def test_no_end_means_no_duration(self):
        tracker = CleaningRunTracker()
        _run(tracker, [(0, 10, 0), (1, 1, 0)])
        assert tracker.current is not None
        assert tracker.current.duration_minutes is None


def _sensors(reported: dict[str, Any]) -> list[ElectroluxLastCleaningSensor]:
    coordinator = MagicMock()
    appliance = MagicMock(pnc_id="RVC_PNC")
    appliance.name = "Robot"
    sensors = create_last_cleaning_sensors(coordinator, MagicMock(), appliance)
    for sensor in sensors:
        sensor.hass = MagicMock()
        sensor.appliance_status = {"properties": {"reported": reported}}
        sensor.reported_state = reported
    return sensors


class TestLastCleaningSensors:
    def test_five_sensors_share_one_tracker(self):
        sensors = _sensors({"robotStatus": 10})
        assert [s.translation_key for s in sensors] == [
            "lastcleaningstart",
            "lastcleaningend",
            "lastcleaningduration",
            "lastcleaningarea",
            "lastcleaningrecharges",
        ]
        assert len({id(s._tracker) for s in sensors}) == 1
        assert sensors[0].device_class == SensorDeviceClass.TIMESTAMP
        assert sensors[3].native_unit_of_measurement == "m²"
        assert sensors[2].state_class is not None
        assert all(s.entity_domain == "sensor" for s in sensors)

    def test_values_follow_the_last_run(self):
        sensors = _sensors({"robotStatus": 10, "filter_sqm": 100.0})
        tracker = sensors[0]._tracker
        assert [s.native_value for s in sensors] == [None] * 5
        _run(tracker, [(0, 10, 100.0), (1, 1, 100.0), (40, 10, 112.5)])
        start, end, duration, area, recharges = (s.native_value for s in sensors)
        assert (start, end, duration, area, recharges) == (_at(1), _at(40), 39, 12.5, 0)

    def test_coordinator_update_feeds_the_tracker_and_writes_on_change(self):
        reported: dict[str, Any] = {"robotStatus": 10, "filter_sqm": 50.0}
        sensor = _sensors(reported)[3]
        appliance = MagicMock()
        appliance.state = {"properties": {"reported": reported}}
        sensor.coordinator.data = {"appliances": MagicMock()}
        sensor.coordinator.data["appliances"].get_appliance.return_value = appliance
        with patch.object(ElectroluxLastCleaningSensor, "async_write_ha_state") as write_state:
            sensor._handle_coordinator_update()
            reported["robotStatus"] = 1
            sensor._handle_coordinator_update()
            reported.update(robotStatus=9, filter_sqm=57.0)
            sensor._handle_coordinator_update()
        # one write per update from the base class, plus one when the run ended
        assert write_state.call_count == 4
        assert sensor.native_value == 7.0

    @pytest.mark.asyncio
    async def test_restore_values(self):
        start_sensor, _end, duration_sensor, *_ = _sensors({"robotStatus": 10})
        with (
            patch(
                "custom_components.electrolux.entity.ElectroluxEntity.async_added_to_hass",
                new=AsyncMock(),
            ),
            patch.object(
                ElectroluxLastCleaningSensor,
                "async_get_last_sensor_data",
                new=AsyncMock(
                    side_effect=[MagicMock(native_value="2026-11-18T07:00:01+00:00"), MagicMock(native_value=36)]
                ),
            ),
        ):
            await start_sensor.async_added_to_hass()
            await duration_sensor.async_added_to_hass()
        assert start_sensor.native_value == T0
        assert duration_sensor.native_value == 36

    @pytest.mark.asyncio
    async def test_nothing_to_restore(self):
        sensor = _sensors({"robotStatus": 10})[4]
        with (
            patch(
                "custom_components.electrolux.entity.ElectroluxEntity.async_added_to_hass",
                new=AsyncMock(),
            ),
            patch.object(ElectroluxLastCleaningSensor, "async_get_last_sensor_data", new=AsyncMock(return_value=None)),
        ):
            await sensor.async_added_to_hass()
        assert sensor.native_value is None


@pytest.mark.asyncio
async def test_sensor_setup_adds_last_cleaning_for_purei9():
    from custom_components.electrolux.sensor import async_setup_entry

    appliance = MagicMock(appliance_type="PUREi9", pnc_id="RVC_PNC", entities=[])
    appliance.name = "Robot"
    coordinator = MagicMock()
    coordinator.data = {"appliances": MagicMock()}
    coordinator.data["appliances"].appliances = {"RVC_PNC": appliance}
    add_entities = MagicMock()
    await async_setup_entry(MagicMock(), MagicMock(runtime_data=coordinator), add_entities)
    added = add_entities.call_args.args[0]
    assert sum(isinstance(e, ElectroluxLastCleaningSensor) for e in added) == 5
