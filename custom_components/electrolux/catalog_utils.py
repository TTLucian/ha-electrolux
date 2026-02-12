"""Catalog utility functions for creating common entity patterns."""

from typing import Any, Optional

from homeassistant.helpers.entity import EntityCategory

from .const import (
    ENTITY_CATEGORY_DIAGNOSTIC,
    ICON_INFORMATION,
    ICON_NUMERIC,
    ICON_STATE_MACHINE,
)
from .model import ElectroluxDevice


def create_diagnostic_string_entity(
    capability_info: dict[str, Any],
    friendly_name: str,
    icon: str = ICON_INFORMATION,
    entity_category: EntityCategory = ENTITY_CATEGORY_DIAGNOSTIC,
    entity_registry_enabled_default: bool = True,
) -> ElectroluxDevice:
    """Create a diagnostic string entity with common defaults."""
    return ElectroluxDevice(
        capability_info=capability_info,
        device_class=None,
        unit=None,
        entity_category=entity_category,
        entity_icon=icon,
        friendly_name=friendly_name,
        entity_registry_enabled_default=entity_registry_enabled_default,
    )


def create_diagnostic_number_entity(
    capability_info: dict[str, Any],
    friendly_name: str,
    unit: Optional[str] = None,
    icon: str = ICON_NUMERIC,
    entity_category: EntityCategory = ENTITY_CATEGORY_DIAGNOSTIC,
) -> ElectroluxDevice:
    """Create a diagnostic number entity with common defaults."""
    return ElectroluxDevice(
        capability_info=capability_info,
        device_class=None,
        unit=unit,
        entity_category=entity_category,
        entity_icon=icon,
        friendly_name=friendly_name,
    )


def create_config_entity(
    capability_info: dict[str, Any],
    friendly_name: str,
    icon: str = ICON_INFORMATION,
) -> ElectroluxDevice:
    """Create a config entity with common defaults."""
    return ElectroluxDevice(
        capability_info=capability_info,
        device_class=None,
        unit=None,
        entity_category=EntityCategory.CONFIG,
        entity_icon=icon,
        friendly_name=friendly_name,
    )


def create_hidden_entity(
    capability_info: dict[str, Any],
    friendly_name: str,
    icon: str = ICON_STATE_MACHINE,
) -> ElectroluxDevice:
    """Create a hidden entity (not shown in UI by default) with common defaults."""
    return ElectroluxDevice(
        capability_info=capability_info,
        device_class=None,
        unit=None,
        entity_category=None,
        entity_icon=icon,
        friendly_name=friendly_name,
        entity_registry_enabled_default=False,
    )
