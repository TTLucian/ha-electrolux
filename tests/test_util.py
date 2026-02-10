"""Tests for Electrolux util helpers."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_report_token_refresh_creates_issue(monkeypatch):
    """Assert an HA issue is created when token refresh fails and hass is available."""

    captured = {}

    def fake_create_issue(hass_arg, domain, issue_id, **kwargs):
        captured["args"] = (hass_arg, domain, issue_id)
        captured["kwargs"] = kwargs

    monkeypatch.setattr(
        "custom_components.electrolux.util.issue_registry.async_create_issue",
        fake_create_issue,
    )

    from custom_components.electrolux.util import DOMAIN, ElectroluxApiClient

    hass = MagicMock()
    # Mock config_entries to return empty list so issue_id doesn't include entry_id
    hass.config_entries.async_entries.return_value = []

    client = ElectroluxApiClient("api", "access", "refresh", hass)

    await client._report_token_refresh_error("Refresh token is invalid.")

    assert "args" in captured
    assert captured["args"][0] is hass
    assert captured["args"][1] == DOMAIN
    assert captured["args"][2] == "invalid_refresh_token"
    assert (
        captured["kwargs"]["translation_placeholders"]["message"]
        == "Refresh token is invalid."
    )
    assert captured["kwargs"]["is_fixable"] is True


@pytest.mark.asyncio
async def test_report_token_refresh_no_hass_does_not_create_issue(monkeypatch):
    """Assert no issue is created if hass is not provided."""

    called = {}

    def fake_create_issue(*args, **kwargs):
        called["called"] = True

    monkeypatch.setattr(
        "custom_components.electrolux.util.issue_registry.async_create_issue",
        fake_create_issue,
    )

    from custom_components.electrolux.util import ElectroluxApiClient

    client = ElectroluxApiClient("api", "access", "refresh", hass=None)

    await client._report_token_refresh_error("No HA available")

    assert "called" not in called
