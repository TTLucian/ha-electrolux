"""SSE-vs-REST ordering guard for applied snapshots (#233).

A REST poll can return a snapshot older than the SSE event that armed it, because
the cloud's REST view lags its own SSE bus. Applying it verbatim makes an entity
jump backwards - measured as a false `Running` 13.9s after a dishwasher cycle
ended, which fires `to: "Running"` triggers.

The guard rejects a polled value only when SSE has *already moved away from that
exact value* inside a short window. A value SSE never delivered still comes
through, so a dropped SSE event is recovered by the next poll rather than
suppressed for up to the 6-hourly refresh.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.electrolux import coordinator as coord_mod
from custom_components.electrolux.const import CONF_API_KEY
from custom_components.electrolux.coordinator import ElectroluxCoordinator
from custom_components.electrolux.models import Appliance, Appliances, _get_nested_value

PNC = "dw1"


class _Clock:
    """Monotonic clock the coordinator reads through hass.loop.time()."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _make_coordinator() -> tuple[ElectroluxCoordinator, _Clock]:
    clock = _Clock()
    hass = MagicMock()
    hass.loop = MagicMock()
    hass.loop.time.side_effect = clock
    entry = MagicMock()
    entry.data = {CONF_API_KEY: "k"}
    entry.entry_id = "e1"
    entry.title = "T"

    with patch(
        "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = ElectroluxCoordinator.__new__(ElectroluxCoordinator)
    coord.hass = hass
    coord.api = MagicMock()
    coord.platforms = []
    coord.renew_interval = 7200
    coord.renew_task = None
    coord.listen_task = None
    coord.data = {}
    coord._deferred_tasks = set()
    coord._deferred_tasks_by_appliance = {}
    coord._appliances_lock = __import__("asyncio").Lock()
    coord._manual_sync_lock = __import__("asyncio").Lock()
    coord._last_cleanup_time = 0
    coord._last_update_times = {}
    coord._last_known_connectivity = {}
    coord._last_sse_restart_time = 0.0
    coord._last_sse_message_time = 0.0
    coord._sse_stall_monitor_task = None
    coord._consecutive_sse_restarts = 0
    coord._last_manual_sync_time = 0.0
    coord._last_time_to_end = {}
    coord._last_time_to_end_seen = {}
    coord._consecutive_auth_failures = 0
    coord._auth_failure_threshold = 3
    coord._last_token_update = 0.0
    coord._appliances_cache = None
    coord.config_entry = entry
    coord.last_update_success = True
    coord._last_remote_control = {}
    coord._pending_state_refresh_tasks = {}
    coord._sse_value_history = {}
    coord._sse_retry_task = None
    return coord, clock


def _make_appliance(reported: dict) -> Appliance:
    state = {"properties": {"reported": dict(reported)}}
    return Appliance(
        coordinator=None,
        name="dw",
        pnc_id=PNC,
        brand="Electrolux",
        model="dw",
        state=state,
        appliance_type="DW",
    )


def _rest_body(reported: dict) -> dict:
    return {"properties": {"reported": dict(reported)}}


def _sse(coord: ElectroluxCoordinator, prop: str, value, clock: _Clock) -> None:
    """Record one SSE delivery the way _process_incremental_update does."""
    coord._record_sse_values(PNC, {prop: value})
    clock.advance(0.0)


def _feed_history(coord, clock, *values) -> None:
    for value in values:
        _sse(coord, "applianceState", value, clock)
        clock.advance(0.2)


def _wire(coord: ElectroluxCoordinator, appliance: Appliance) -> None:
    # The real container rather than a mock: coordinator declares
    # _appliances_cache as None first, so a MagicMock is not assignable and, more
    # to the point, the real Appliances is what production hands it.
    apps = Appliances({PNC: appliance})
    coord.data = {"appliances": apps}
    coord._appliances_cache = apps


class TestSupersededValueRejected:
    """The measured failure: the poll returns a value SSE already left behind."""

    def test_superseded_appliance_state_is_not_restored(self):
        """RUNNING -> END_OF_CYCLE -> OFF, then a poll proposing RUNNING."""
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "END_OF_CYCLE", "OFF")
        appliance = _make_appliance({"applianceState": "OFF"})
        _wire(coord, appliance)

        coord._apply_rest_status(appliance, _rest_body({"applianceState": "RUNNING"}))

        assert appliance.reported_state["applianceState"] == "OFF"

    def test_end_of_cycle_transition_is_preserved(self):
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "END_OF_CYCLE")
        appliance = _make_appliance({"applianceState": "END_OF_CYCLE"})
        _wire(coord, appliance)

        coord._apply_rest_status(appliance, _rest_body({"applianceState": "RUNNING"}))

        assert appliance.reported_state["applianceState"] == "END_OF_CYCLE"

    def test_guard_reports_the_retained_property(self):
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "OFF")

        retain = coord._superseded_by_sse(PNC, {"applianceState": "RUNNING"})

        assert retain == {"applianceState"}


class TestNewValuesStillPass:
    """The reason this is value-scoped rather than a blanket time window."""

    def test_value_sse_never_delivered_is_applied(self):
        """A dropped SSE event must not strand the state until the 6h refresh."""
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "OFF")
        appliance = _make_appliance({"applianceState": "OFF"})
        _wire(coord, appliance)

        coord._apply_rest_status(appliance, _rest_body({"applianceState": "ALARM"}))

        assert appliance.reported_state["applianceState"] == "ALARM"

    def test_poll_agreeing_with_sse_is_applied(self):
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "OFF")
        appliance = _make_appliance({"applianceState": "OFF"})
        _wire(coord, appliance)

        coord._apply_rest_status(appliance, _rest_body({"applianceState": "OFF"}))

        assert appliance.reported_state["applianceState"] == "OFF"

    def test_no_sse_history_means_no_guard(self):
        coord, _ = _make_coordinator()
        appliance = _make_appliance({"applianceState": "OFF"})
        _wire(coord, appliance)

        coord._apply_rest_status(appliance, _rest_body({"applianceState": "RUNNING"}))

        assert appliance.reported_state["applianceState"] == "RUNNING"


class TestWindow:
    def test_poll_wins_once_the_window_has_expired(self):
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "OFF")
        clock.advance(coord_mod.SSE_AUTHORITY_WINDOW + 1)
        appliance = _make_appliance({"applianceState": "OFF"})
        _wire(coord, appliance)

        coord._apply_rest_status(appliance, _rest_body({"applianceState": "RUNNING"}))

        assert appliance.reported_state["applianceState"] == "RUNNING"

    def test_window_exceeds_the_measured_10_147s_gap(self):
        """A 10s window would still let the reported snapshot through."""
        assert coord_mod.SSE_AUTHORITY_WINDOW > 10.147
        assert coord_mod.SSE_AUTHORITY_WINDOW == coord_mod.STATE_CHANGE_REFRESH_DELAY + 5


class TestScope:
    def test_untracked_property_is_never_retained(self):
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "OFF")
        appliance = _make_appliance({"doorState": "OPEN"})
        _wire(coord, appliance)

        # doorState is not in SSE_ORDERED_PROPERTIES here, so nothing is remembered
        # for it and the poll wins.
        assert "doorState" not in coord._superseded_by_sse(PNC, {"doorState": "CLOSED"})
        assert "doorState" not in coord._sse_value_history.get(PNC, {})

    def test_duplicate_sse_values_do_not_grow_history(self):
        coord, clock = _make_coordinator()
        for _ in range(5):
            _sse(coord, "applianceState", "OFF", clock)
            clock.advance(0.1)

        history = coord._sse_value_history[PNC]["applianceState"]
        assert len(history) == 1

    def test_history_depth_is_kept_within_the_window(self):
        """Age pruning, not a fixed depth - a poll may return a value 3 steps back."""
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "END_OF_CYCLE", "OFF")

        history = coord._sse_value_history[PNC]["applianceState"]
        assert [value for _, value in history] == ["RUNNING", "END_OF_CYCLE", "OFF"]

    def test_history_is_pruned_by_age(self):
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "END_OF_CYCLE", "OFF")
        clock.advance(coord_mod.SSE_AUTHORITY_WINDOW + 1)
        _sse(coord, "applianceState", "READY_TO_START", clock)

        history = coord._sse_value_history[PNC]["applianceState"]
        assert [value for _, value in history] == ["READY_TO_START"]

    def test_history_has_a_hard_cap(self):
        coord, clock = _make_coordinator()
        for index in range(20):
            _sse(coord, "applianceState", f"STATE_{index}", clock)
            clock.advance(0.01)

        assert len(coord._sse_value_history[PNC]["applianceState"]) <= coord_mod.SSE_VALUE_HISTORY_MAX

    def test_other_properties_are_left_alone_by_the_retain(self):
        """Only the ordered property is held back; the rest of the body applies."""
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "OFF")
        appliance = _make_appliance({"applianceState": "OFF", "timeToEnd": 0})
        _wire(coord, appliance)

        coord._apply_rest_status(
            appliance, _rest_body({"applianceState": "RUNNING", "timeToEnd": 60})
        )

        assert appliance.reported_state["applianceState"] == "OFF"
        assert appliance.reported_state["timeToEnd"] == 60

    def test_appliances_do_not_share_history(self):
        coord, clock = _make_coordinator()
        _feed_history(coord, clock, "RUNNING", "OFF")

        assert coord._superseded_by_sse("other-appliance", {"applianceState": "RUNNING"}) == set()


class TestNestedPaths:
    def test_nested_retain_uses_the_path_helpers(self):
        """Retain must work for slash-separated paths, not flat names."""
        coord, clock = _make_coordinator()
        _sse(coord, "upperOven/targetTemperatureC", 180, clock)
        clock.advance(0.2)
        _sse(coord, "upperOven/targetTemperatureC", 200, clock)
        appliance = _make_appliance({"upperOven": {"targetTemperatureC": 200}})
        _wire(coord, appliance)

        coord._apply_rest_status(appliance, {"properties": {"reported": {"upperOven": {"targetTemperatureC": 180}}}})

        assert _get_nested_value(appliance.reported_state, "upperOven/targetTemperatureC") == 200

    def test_get_nested_value_missing_returns_default(self):
        assert _get_nested_value({"a": {"b": 1}}, "a/zzz", "fallback") == "fallback"
        assert _get_nested_value({"a": {"b": 1}}, "a/b") == 1
        assert _get_nested_value({}, "x") is None


class TestAllApplySitesAreGuarded:
    @pytest.mark.parametrize(
        ("line_hint", "marker"),
        [
            ("deferred_update", "appliance_status"),
            ("_refresh_after_appliance_state_change", "status"),
        ],
    )
    def test_no_unguarded_appliance_update_remains(self, line_hint, marker):
        """Regression: any new `appliance.update(` must go through the guard."""
        import inspect

        source = inspect.getsource(coord_mod)
        # Everything after the guard's own definition is call sites; the two calls
        # inside _apply_rest_status are the guard itself.
        _, _, after = source.partition("def _apply_rest_status(")
        _, _, call_sites = after.partition("    def incoming_data(")
        offenders = [
            line.strip()
            for line in call_sites.splitlines()
            if "appliance.update(" in line or "app_obj.update(" in line
        ]
        assert offenders == [], f"unguarded apply sites: {offenders}"

    def test_cleanup_pops_the_history(self):
        """#180 precedent: the dict must not leak on appliance removal."""
        import inspect

        source = inspect.getsource(coord_mod)
        assert "_sse_value_history.pop(appliance_id, None)" in source
