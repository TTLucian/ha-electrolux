"""Repairs support for the Electrolux integration."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowHandler

from .config_flow import ElectroluxRepairFlow


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> FlowHandler:
    """Create a fix flow for Electrolux repair issues."""
    return ElectroluxRepairFlow(issue_id)
