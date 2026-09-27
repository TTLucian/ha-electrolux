"""Tests for config_flow coverage gaps.

These tests specifically target uncovered code paths in config_flow.py to achieve 100% coverage.
Coverage targets:
- Line 122: None return when credentials are missing
- Lines 438-453: Exception handling in _test_credentials (reauth)
- Lines 523-538: Exception handling in _test_credentials (options flow)
- Lines 764-779: Exception handling in _test_credentials (reconfigure)
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.electrolux.config_flow import (
    ElectroluxRepairFlow,
    ElectroluxStatusFlowHandler,
    _validate_credentials_and_capture_rotation,
)
from custom_components.electrolux.const import CONF_API_KEY


class TestConfigFlowCoverageGaps:
    """Tests targeting uncovered code paths in config_flow."""

    # =====================================================================
    # Line 122: _validate_credentials_and_capture_rotation returns None
    # when credentials missing
    # =====================================================================

    @pytest.mark.asyncio
    async def test_validate_creds_returns_none_with_missing_api_key(self):
        """Test _validate_credentials_and_capture_rotation returns None when api_key is None."""
        result = await _validate_credentials_and_capture_rotation(None, "token", "refresh")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_creds_returns_none_with_missing_access_token(self):
        """Test returns None when access_token is None."""
        result = await _validate_credentials_and_capture_rotation("key", None, "refresh")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_creds_returns_none_with_missing_refresh_token(self):
        """Test returns None when refresh_token is None."""
        result = await _validate_credentials_and_capture_rotation("key", "token", None)
        assert result is None

    # =====================================================================
    # Lines 438-453: Exception in ReauthFlowHandler._test_credentials
    # =====================================================================

    @pytest.mark.asyncio
    async def test_reauth_test_credentials_exception_returns_false(self):
        """Test reauth _test_credentials returns False on exception."""
        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()
        flow._errors = {}

        with patch(
            "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
            new=AsyncMock(side_effect=Exception("API Error")),
        ):
            result = await flow._test_credentials("key", "token", "refresh")

        assert result is False

    # =====================================================================
    # Lines 523-538: Exception in OptionsFlowHandler._test_credentials
    # =====================================================================

    @pytest.mark.asyncio
    async def test_options_flow_test_credentials_exception_returns_false(self):
        """Test options flow _test_credentials returns False on exception."""
        mock_config_entry = Mock()
        mock_config_entry.entry_id = "test_entry"
        mock_config_entry.data = {CONF_API_KEY: "key"}

        flow = ElectroluxStatusFlowHandler()
        flow.hass = Mock()

        with (
            patch.object(flow, "_config_entry", mock_config_entry, create=True),
            patch.object(flow, "_errors", {}, create=True),
            patch(
                "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
                new=AsyncMock(side_effect=Exception("API Error")),
            ),
        ):
            result = await flow._test_credentials("key", "token", "refresh")

        assert result is False

    # =====================================================================
    # Lines 764-779: Exception in RepairFlow._test_credentials
    # =====================================================================

    @pytest.mark.asyncio
    async def test_repair_flow_test_credentials_exception_returns_false(self):
        """Test repair flow _test_credentials returns False on exception."""
        flow = ElectroluxRepairFlow("test_issue")
        flow.hass = Mock()

        with patch(
            "custom_components.electrolux.config_flow._validate_credentials_and_capture_rotation",
            new=AsyncMock(side_effect=Exception("API Error")),
        ):
            result = await flow._test_credentials("key", "token", "refresh")

        assert result is False
