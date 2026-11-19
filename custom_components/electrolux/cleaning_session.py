"""Last cleaning run of a PUREi9, derived from its state.

The Electrolux app shows a history entry per run (area cleaned, duration,
start and end time, number of recharges). The developer API has no history
endpoint and no longer reports ``cleaningSession``, so the run is derived here:

- a run starts when ``robotStatus`` goes from an idle state to cleaning (1) or
  spot cleaning (3), and ends when the robot is back on the dock (9 charging,
  10 sleeping);
- every entry into "returning for pitstop" (7) or "pitstop" (12) is a recharge;
- the area is the increase of the ``filter_sqm`` wear counter, which the robot
  updates a few seconds after docking.

Checked against the app on a PUREi9: 07:00:01-07:35:45 and a counter increase
of about 30 m² for a run the app lists as 36 min (8:00-8:36 local), 29 m²,
0 recharges.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfArea, UnitOfTime
from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from .const import SENSOR
from .entity import ElectroluxEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)

_START_STATES = {1, 3}  # cleaning, spot cleaning
_ACTIVE_STATES = {1, 2, 3, 4, 5, 6, 7, 8, 12, 13}
_DOCKED_STATES = {9, 10}  # charging, sleeping
_RECHARGE_STATES = {7, 12}  # returning for pitstop, pitstop
AREA_COUNTER = "filter_sqm"


@dataclass
class CleaningRun:
    """One cleaning run."""

    start: datetime
    counter_start: float | None = None
    end: datetime | None = None
    recharges: int = 0
    area: float | None = None

    @property
    def duration_minutes(self) -> int | None:
        """Duration from start to dock, in whole minutes (as the app shows it)."""
        if self.end is None:
            return None
        return round((self.end - self.start).total_seconds() / 60)


def _status(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _counter(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


class CleaningRunTracker:
    """Follow robotStatus and the area counter to find the last finished run."""

    def __init__(self) -> None:
        """Initialize the tracker."""
        self.current: CleaningRun | None = None
        self.last: CleaningRun | None = None
        self._previous: int | None = None

    def update(self, status_value: Any, counter_value: Any, now: datetime) -> bool:
        """Feed the latest state; return True when the last run changed."""
        status = _status(status_value)
        counter = _counter(counter_value)
        changed = False
        previous = self._previous

        if status is not None:
            if self.current is None:
                if status in _START_STATES and (previous is None or previous not in _ACTIVE_STATES):
                    self.current = CleaningRun(start=now, counter_start=counter)
            else:
                if status in _RECHARGE_STATES and previous not in _RECHARGE_STATES:
                    self.current.recharges += 1
                if self.current.counter_start is None:
                    self.current.counter_start = counter
                if status in _DOCKED_STATES:
                    self.current.end = now
                    self.last = self.current
                    self.current = None
                    changed = True
            self._previous = status

        # The counter is updated shortly after docking: keep the area current
        # until the next run starts.
        last = self.last
        if last is not None and last.counter_start is not None and counter is not None:
            area = round(max(0.0, counter - last.counter_start), 1)
            if area != last.area:
                last.area = area
                changed = True
        return changed


@dataclass(frozen=True)
class _Field:
    key: str
    device_class: SensorDeviceClass | None
    unit: str | None
    state_class: SensorStateClass | None
    icon: str


_FIELDS = (
    _Field("lastCleaningStart", SensorDeviceClass.TIMESTAMP, None, None, "mdi:clock-start"),
    _Field("lastCleaningEnd", SensorDeviceClass.TIMESTAMP, None, None, "mdi:clock-end"),
    _Field(
        "lastCleaningDuration",
        SensorDeviceClass.DURATION,
        UnitOfTime.MINUTES,
        SensorStateClass.MEASUREMENT,
        "mdi:timer-outline",
    ),
    _Field(
        "lastCleaningArea",
        SensorDeviceClass.AREA,
        UnitOfArea.SQUARE_METERS,
        SensorStateClass.MEASUREMENT,
        "mdi:floor-plan",
    ),
    _Field("lastCleaningRecharges", None, None, SensorStateClass.MEASUREMENT, "mdi:battery-charging"),
)


class ElectroluxLastCleaningSensor(ElectroluxEntity, RestoreSensor):
    """One value of the last cleaning run, kept across restarts."""

    def __init__(self, tracker: CleaningRunTracker, field: _Field, **kwargs: Any) -> None:
        """Initialize the sensor."""
        super().__init__(**kwargs)
        self._tracker = tracker
        self._field = field
        self._attr_device_class = field.device_class
        self._attr_native_unit_of_measurement = field.unit
        self._attr_state_class = field.state_class
        self._restored: Any = None

    @property
    def entity_domain(self) -> str:
        """Entity domain for the entry. Used for consistent entity_id."""
        return SENSOR

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the device class of this value."""
        return self._field.device_class

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of this value."""
        return self._field.unit

    @property
    def state_class(self) -> SensorStateClass | None:
        """Return the state class of this value."""
        return self._field.state_class

    async def async_added_to_hass(self) -> None:
        """Restore the last known value."""
        await super().async_added_to_hass()
        if (data := await self.async_get_last_sensor_data()) is not None:
            value = data.native_value
            if self._field.device_class == SensorDeviceClass.TIMESTAMP and isinstance(value, str):
                value = dt_util.parse_datetime(value)
            self._restored = value
        self._feed_tracker()

    def _feed_tracker(self) -> bool:
        status = self.get_state_attr("robotStatus")
        return self._tracker.update(status, self.get_state_attr(AREA_COUNTER), dt_util.utcnow())

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update the tracker with the new state."""
        super()._handle_coordinator_update()
        if self._feed_tracker():
            self.async_write_ha_state()

    @property
    def native_value(self) -> Any:
        """Return this value of the last finished run (or the restored one)."""
        run = self._tracker.last
        if run is None:
            return self._restored
        match self._field.key:
            case "lastCleaningStart":
                return run.start
            case "lastCleaningEnd":
                return run.end
            case "lastCleaningDuration":
                return run.duration_minutes
            case "lastCleaningArea":
                return run.area
            case _:
                return run.recharges


def create_last_cleaning_sensors(coordinator: Any, entry: Any, appliance: Any) -> list[ElectroluxLastCleaningSensor]:
    """Create the last-cleaning sensors for one PUREi9 (sharing one tracker)."""
    tracker = CleaningRunTracker()
    return [
        ElectroluxLastCleaningSensor(
            tracker,
            field,
            coordinator=coordinator,
            name=appliance.name,
            config_entry=entry,
            pnc_id=appliance.pnc_id,
            entity_type=SENSOR,
            entity_name=field.key,
            entity_attr=field.key,
            entity_source=None,
            capability={},
            unit=field.unit,
            device_class=field.device_class,
            entity_category=None,
            icon=field.icon,
        )
        for field in _FIELDS
    ]
