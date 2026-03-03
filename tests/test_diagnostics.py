"""Tests for diagnostics.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.electrolux.const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)
from custom_components.electrolux.diagnostics import (
    REDACT_ALL,
    REDACT_CONFIG,
    REDACT_KEYS,
    _async_device_as_dict,
    _async_get_diagnostics,
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestRedactConstants:
    def test_redact_config_contains_credential_keys(self):
        assert CONF_API_KEY in REDACT_CONFIG
        assert CONF_ACCESS_TOKEN in REDACT_CONFIG
        assert CONF_REFRESH_TOKEN in REDACT_CONFIG

    def test_redact_keys_contains_pii(self):
        for key in ("email", "userId", "macAddress", "ipAddress", "serialNumber"):
            assert key in REDACT_KEYS

    def test_redact_all_is_union(self):
        assert REDACT_CONFIG.issubset(REDACT_ALL)
        assert REDACT_KEYS.issubset(REDACT_ALL)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hass(entry_id: str) -> MagicMock:
    hass = MagicMock()
    hass.data = {}
    hass.states.get = MagicMock(return_value=None)
    return hass


def _make_entry(
    entry_id: str = "test_entry",
    data: dict | None = None,
    options: dict | None = None,
    coordinator=None,
):
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.domain = DOMAIN
    entry.title = "Test Electrolux"
    entry.data = data or {"api_key": "secret_key", "access_token": "secret_token"}
    entry.options = options or {}
    entry.unique_id = "unique-1"
    entry.disabled_by = None
    entry.runtime_data = coordinator
    return entry


def _make_coordinator(
    user_meta=None,
    appliances_list=None,
    appliances_info=None,
    capabilities=None,
    state=None,
    health_status=None,
    fail_user_meta=False,
    fail_appliances_list=False,
    fail_appliances_info=False,
    fail_capabilities=False,
    fail_state=False,
    fail_health=False,
) -> MagicMock:
    api = MagicMock()

    if fail_user_meta:
        api.get_user_metadata = AsyncMock(side_effect=Exception("meta error"))
    else:
        api.get_user_metadata = AsyncMock(return_value=user_meta or {"userId": "u1"})

    if fail_appliances_list:
        api.get_appliances_list = AsyncMock(
            side_effect=Exception("appliances list error")
        )
    else:
        app_list = (
            appliances_list
            if appliances_list is not None
            else [{"applianceId": "APP1"}]
        )
        api.get_appliances_list = AsyncMock(return_value=app_list)

    if fail_appliances_info:
        api.get_appliances_info = AsyncMock(
            side_effect=Exception("appliances info error")
        )
    else:
        api.get_appliances_info = AsyncMock(
            return_value=appliances_info or [{"applianceId": "APP1", "model": "M1"}]
        )

    if fail_capabilities:
        api.get_appliance_capabilities = AsyncMock(side_effect=Exception("cap error"))
    else:
        api.get_appliance_capabilities = AsyncMock(
            return_value=capabilities or {"powerState": {}}
        )

    if fail_state:
        api.get_appliance_state = AsyncMock(side_effect=Exception("state error"))
    else:
        api.get_appliance_state = AsyncMock(
            return_value=state or {"properties": {"reported": {"powerState": "on"}}}
        )

    coord = MagicMock()
    coord.api = api

    if fail_health:
        coord.get_health_status = MagicMock(side_effect=Exception("health error"))
    else:
        coord.get_health_status = MagicMock(return_value=health_status or "ok")

    return coord


# ---------------------------------------------------------------------------
# _async_get_diagnostics
# ---------------------------------------------------------------------------


class TestAsyncGetDiagnostics:
    @pytest.mark.asyncio
    async def test_successful_full_run(self):
        """All API calls succeed — data is populated and redacted."""
        coord = _make_coordinator(
            user_meta={"userId": "user123"},
            appliances_list=[{"applianceId": "A1"}],
            appliances_info=[{"applianceId": "A1", "model": "M1"}],
            capabilities={"temp": {}},
            state={"properties": {"reported": {}}},
            health_status="healthy",
        )
        hass = _make_hass("e1")
        entry = _make_entry("e1", coordinator=coord)

        result = await _async_get_diagnostics(hass, entry)

        # userId PII should be redacted
        assert result["user_metadata"]["userId"] == "**REDACTED**"
        # appliances fetched
        assert result["appliances_list"] is not None
        assert "A1" in result["appliances_detail"]
        assert result["appliances_detail"]["A1"]["capabilities"] == {"temp": {}}
        assert result["health_status"] == "healthy"
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_user_metadata_failure_continues(self):
        """Failure on get_user_metadata is collected in errors and run continues."""
        coord = _make_coordinator(fail_user_meta=True)
        hass = _make_hass("e1")
        entry = _make_entry("e1", coordinator=coord)

        result = await _async_get_diagnostics(hass, entry)

        assert result["user_metadata"] is None
        assert any("user metadata" in e for e in result["errors"])
        # appliances should still have been attempted
        assert result["appliances_list"] is not None

    @pytest.mark.asyncio
    async def test_appliances_list_failure_returns_early(self):
        """Failure on get_appliances_list causes early return with partial data."""
        coord = _make_coordinator(fail_appliances_list=True)
        hass = _make_hass("e1")
        entry = _make_entry("e1", coordinator=coord)

        result = await _async_get_diagnostics(hass, entry)

        assert result["appliances_list"] is None
        assert result["appliances_detail"] == {}
        assert any("appliances list" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_appliances_info_failure_continues(self):
        """Failure on get_appliances_info is logged but per-appliance detail continues."""
        coord = _make_coordinator(fail_appliances_info=True)
        hass = _make_hass("e1")
        entry = _make_entry("e1", coordinator=coord)

        result = await _async_get_diagnostics(hass, entry)

        assert result["appliances_info"] is None
        assert any("appliances info" in e for e in result["errors"])
        # Per-appliance detail still attempted
        assert "APP1" in result["appliances_detail"]

    @pytest.mark.asyncio
    async def test_capabilities_failure_stored_in_detail(self):
        """Failure on get_appliance_capabilities is stored under capabilities_error."""
        coord = _make_coordinator(fail_capabilities=True)
        hass = _make_hass("e1")
        entry = _make_entry("e1", coordinator=coord)

        result = await _async_get_diagnostics(hass, entry)

        app_detail = result["appliances_detail"]["APP1"]
        assert "capabilities_error" in app_detail
        assert "cap error" in app_detail["capabilities_error"]

    @pytest.mark.asyncio
    async def test_state_failure_stored_in_detail(self):
        """Failure on get_appliance_state is stored under state_error."""
        coord = _make_coordinator(fail_state=True)
        hass = _make_hass("e1")
        entry = _make_entry("e1", coordinator=coord)

        result = await _async_get_diagnostics(hass, entry)

        app_detail = result["appliances_detail"]["APP1"]
        assert "state_error" in app_detail
        assert "state error" in app_detail["state_error"]

    @pytest.mark.asyncio
    async def test_health_status_failure_continues(self):
        """Failure on get_health_status is logged but run still returns data."""
        coord = _make_coordinator(fail_health=True)
        hass = _make_hass("e1")
        entry = _make_entry("e1", coordinator=coord)

        result = await _async_get_diagnostics(hass, entry)

        assert result["health_status"] is None
        assert any("health status" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_empty_appliances_list_skips_detail(self):
        """Empty appliances list means no per-appliance fetching."""
        coord = _make_coordinator(appliances_list=[])
        hass = _make_hass("e1")
        entry = _make_entry("e1", coordinator=coord)

        result = await _async_get_diagnostics(hass, entry)

        assert result["appliances_detail"] == {}
        coord.api.get_appliance_capabilities.assert_not_called()
        coord.api.get_appliance_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_sensitive_fields_are_redacted(self):
        """api_key, access_token and other PII must be redacted in output."""
        coord = _make_coordinator(
            user_meta={
                "userId": "u123",
                "email": "test@example.com",
                "macAddress": "AA:BB:CC:DD:EE:FF",
            }
        )
        hass = _make_hass("e1")
        entry = _make_entry(
            "e1", data={"api_key": "secret", "access_token": "tok"}, coordinator=coord
        )

        result = await _async_get_diagnostics(hass, entry)

        # PII inside user_metadata should be redacted
        meta = result["user_metadata"]
        assert meta["userId"] == "**REDACTED**"
        assert meta["email"] == "**REDACTED**"
        assert meta["macAddress"] == "**REDACTED**"


# ---------------------------------------------------------------------------
# async_get_config_entry_diagnostics
# ---------------------------------------------------------------------------


class TestAsyncGetConfigEntryDiagnostics:
    @pytest.mark.asyncio
    async def test_includes_config_entry_block(self):
        """Result contains a config_entry key with entry metadata."""
        coord = _make_coordinator()
        entry = _make_entry("e2", data={"api_key": "mykey"}, coordinator=coord)
        hass = _make_hass("e2")

        with (
            patch(
                "custom_components.electrolux.diagnostics.dr.async_get",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.diagnostics.dr.async_entries_for_config_entry",
                return_value=[],
            ),
        ):
            result = await async_get_config_entry_diagnostics(hass, entry)

        assert "config_entry" in result
        assert result["config_entry"]["entry_id"] == "e2"
        # api_key must be redacted
        assert result["config_entry"]["data"].get("api_key") == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_includes_device_info_list(self):
        """device_info key is a list (even if empty)."""
        coord = _make_coordinator()
        entry = _make_entry("e3", coordinator=coord)
        hass = _make_hass("e3")

        with (
            patch(
                "custom_components.electrolux.diagnostics.dr.async_get",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.diagnostics.dr.async_entries_for_config_entry",
                return_value=[],
            ),
        ):
            result = await async_get_config_entry_diagnostics(hass, entry)

        assert "device_info" in result
        assert isinstance(result["device_info"], list)


# ---------------------------------------------------------------------------
# async_get_device_diagnostics
# ---------------------------------------------------------------------------


class TestAsyncGetDeviceDiagnostics:
    @pytest.mark.asyncio
    async def test_includes_device_info_dict(self):
        """device_info key is a dict (single device) not a list."""
        coord = _make_coordinator()
        entry = _make_entry("e4", coordinator=coord)
        hass = _make_hass("e4")

        mock_device = MagicMock()
        mock_device.id = "dev1"

        with (
            patch(
                "custom_components.electrolux.diagnostics.er.async_get",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.diagnostics.er.async_entries_for_device",
                return_value=[],
            ),
            patch(
                "custom_components.electrolux.diagnostics.attr.asdict", return_value={}
            ),
        ):
            result = await async_get_device_diagnostics(hass, entry, mock_device)

        assert "config_entry" in result
        assert result["config_entry"]["entry_id"] == "e4"
        # device_info is a dict, not a list
        assert isinstance(result["device_info"], dict)

    @pytest.mark.asyncio
    async def test_credentials_redacted(self):
        """Credentials in config_entry.data are redacted."""
        coord = _make_coordinator()
        entry = _make_entry(
            "e5",
            data={
                "api_key": "secret_api",
                "access_token": "secret_access",
                "refresh_token": "secret_refresh",
            },
            coordinator=coord,
        )
        hass = _make_hass("e5")
        mock_device = MagicMock()
        mock_device.id = "dev2"

        with (
            patch(
                "custom_components.electrolux.diagnostics.er.async_get",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.diagnostics.er.async_entries_for_device",
                return_value=[],
            ),
            patch(
                "custom_components.electrolux.diagnostics.attr.asdict", return_value={}
            ),
        ):
            result = await async_get_device_diagnostics(hass, entry, mock_device)

        cfg_data = result["config_entry"]["data"]
        assert cfg_data["api_key"] == "**REDACTED**"
        assert cfg_data["access_token"] == "**REDACTED**"
        assert cfg_data["refresh_token"] == "**REDACTED**"


# ---------------------------------------------------------------------------
# _async_device_as_dict
# ---------------------------------------------------------------------------


class TestAsyncDeviceAsDict:
    def test_returns_dict_with_entities_key(self):
        """Basic structure: contains 'entities' list."""
        hass = MagicMock()
        hass.states.get = MagicMock(return_value=None)

        mock_device = MagicMock()
        mock_device.id = "dev_x"

        with (
            patch(
                "custom_components.electrolux.diagnostics.er.async_get",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.diagnostics.er.async_entries_for_device",
                return_value=[],
            ),
            patch(
                "custom_components.electrolux.diagnostics.attr.asdict",
                return_value={"id": "dev_x", "name": "My Oven", "serialNumber": "SN1"},
            ),
        ):
            result = _async_device_as_dict(hass, mock_device)

        assert "entities" in result
        assert isinstance(result["entities"], list)
        # serialNumber is PII — must be redacted
        assert result.get("serialNumber") == "**REDACTED**"

    def test_entity_state_included(self):
        """Entity state is included when hass.states.get returns a state."""
        hass = MagicMock()
        mock_state = MagicMock()
        mock_state.as_dict.return_value = {
            "entity_id": "sensor.temp",
            "state": "25",
            "context": "ctx",
        }
        hass.states.get = MagicMock(return_value=mock_state)

        mock_device = MagicMock()
        mock_device.id = "dev_y"

        mock_entity_entry = MagicMock()
        mock_entity_entry.entity_id = "sensor.temp"

        with (
            patch(
                "custom_components.electrolux.diagnostics.er.async_get",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.diagnostics.er.async_entries_for_device",
                return_value=[mock_entity_entry],
            ),
            patch(
                "custom_components.electrolux.diagnostics.attr.asdict",
                side_effect=[
                    {"id": "dev_y"},  # device asdict call
                    {"entity_id": "sensor.temp"},  # entity asdict call
                ],
            ),
        ):
            result = _async_device_as_dict(hass, mock_device)

        assert len(result["entities"]) == 1
        entity = result["entities"][0]
        assert entity["state"]["entity_id"] == "sensor.temp"
        # context must be stripped
        assert "context" not in entity["state"]

    def test_entity_no_state(self):
        """Entity without a HA state gets state=None."""
        hass = MagicMock()
        hass.states.get = MagicMock(return_value=None)

        mock_device = MagicMock()
        mock_device.id = "dev_z"

        mock_entity_entry = MagicMock()
        mock_entity_entry.entity_id = "sensor.missing"

        with (
            patch(
                "custom_components.electrolux.diagnostics.er.async_get",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.electrolux.diagnostics.er.async_entries_for_device",
                return_value=[mock_entity_entry],
            ),
            patch(
                "custom_components.electrolux.diagnostics.attr.asdict",
                side_effect=[{"id": "dev_z"}, {"entity_id": "sensor.missing"}],
            ),
        ):
            result = _async_device_as_dict(hass, mock_device)

        assert result["entities"][0]["state"] is None
