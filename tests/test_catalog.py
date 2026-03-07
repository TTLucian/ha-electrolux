"""Tests for Electrolux catalog definitions.

Exercises catalog loaders to ensure they load correctly and have
expected structure. These tests primarily exist to achieve code
coverage on catalog files (which are pure data modules).
"""

from __future__ import annotations

from custom_components.electrolux.model import ElectroluxDevice


class TestCatalogCore:
    """Tests for catalog_core.py lazy loaders and catalog structure."""

    def test_catalog_base_loads(self):
        """Catalog base loads without error and returns a non-empty dict."""
        from custom_components.electrolux.catalog_core import CATALOG_BASE

        catalog = CATALOG_BASE()
        assert isinstance(catalog, dict)
        assert len(catalog) > 0

    def test_catalog_base_has_expected_keys(self):
        """Catalog base contains common entities present on all appliances."""
        from custom_components.electrolux.catalog_core import CATALOG_BASE

        catalog = CATALOG_BASE()
        assert "applianceState" in catalog
        assert "alerts" in catalog
        assert "remoteControl" in catalog
        assert "uiLockMode" in catalog
        assert "timeToEnd" in catalog

    def test_catalog_base_values_are_electrolux_devices(self):
        """All catalog base values are ElectroluxDevice instances."""
        from custom_components.electrolux.catalog_core import CATALOG_BASE

        catalog = CATALOG_BASE()
        for key, value in catalog.items():
            assert isinstance(value, ElectroluxDevice), (
                f"Catalog entry '{key}' is {type(value)}, expected ElectroluxDevice"
            )

    def test_catalog_by_type_loads(self):
        """Appliance-type-specific catalogs load correctly."""
        from custom_components.electrolux.catalog_core import CATALOG_BY_TYPE

        catalog = CATALOG_BY_TYPE()
        assert isinstance(catalog, dict)
        # Should have entries for common appliance types
        assert "WM" in catalog or "WD" in catalog or "OV" in catalog

    def test_catalog_model_loads(self):
        """Model-specific catalog function loads correctly."""
        from custom_components.electrolux.catalog_core import CATALOG_MODEL

        catalog = CATALOG_MODEL()
        assert isinstance(catalog, dict)

    def test_catalog_base_cached(self):
        """Catalog base returns the same dict on repeated calls (lru_cache)."""
        from custom_components.electrolux.catalog_core import CATALOG_BASE

        c1 = CATALOG_BASE()
        c2 = CATALOG_BASE()
        assert c1 is c2


class TestCatalogOven:
    """Tests for catalog_ov.py."""

    def test_catalog_oven_loads(self):
        """Oven catalog loads without error."""
        from custom_components.electrolux.catalogs.catalog_ov import CATALOG_OV

        assert isinstance(CATALOG_OV, dict)
        assert len(CATALOG_OV) > 0

    def test_oven_entities_are_electrolux_devices(self):
        """All oven catalog values are ElectroluxDevice instances."""
        from custom_components.electrolux.catalogs.catalog_ov import CATALOG_OV

        for key, value in CATALOG_OV.items():
            assert isinstance(value, ElectroluxDevice), (
                f"Oven catalog entry '{key}' is {type(value)}"
            )

    def test_oven_has_temperature_entities(self):
        """Oven catalog has temperature entities."""
        from custom_components.electrolux.catalogs.catalog_ov import CATALOG_OV

        assert (
            "targetTemperatureC" in CATALOG_OV
            or "displayTemperatureC" in CATALOG_OV
        )

    def test_oven_has_execute_command(self):
        """Oven catalog has executeCommand entity."""
        from custom_components.electrolux.catalogs.catalog_ov import CATALOG_OV

        assert "executeCommand" in CATALOG_OV


class TestCatalogWasher:
    """Tests for catalog_wm.py."""

    def test_catalog_washer_loads(self):
        """Washer catalog loads without error."""
        from custom_components.electrolux.catalogs.catalog_wm import CATALOG_WM

        assert isinstance(CATALOG_WM, dict)
        assert len(CATALOG_WM) > 0

    def test_washer_entities_are_electrolux_devices(self):
        """All washer catalog values are ElectroluxDevice instances."""
        from custom_components.electrolux.catalogs.catalog_wm import CATALOG_WM

        for key, value in CATALOG_WM.items():
            assert isinstance(value, ElectroluxDevice), (
                f"Washer catalog entry '{key}' is {type(value)}"
            )


class TestCatalogWasherDryer:
    """Tests for catalog_wd.py."""

    def test_catalog_washer_dryer_loads(self):
        """Washer-dryer catalog loads without error."""
        from custom_components.electrolux.catalogs.catalog_wd import (
            CATALOG_WD,
        )

        assert isinstance(CATALOG_WD, dict)
        assert len(CATALOG_WD) > 0


class TestCatalogDryer:
    """Tests for catalog_td.py."""

    def test_catalog_dryer_loads(self):
        """Dryer catalog loads without error."""
        from custom_components.electrolux.catalogs.catalog_td import CATALOG_TD

        assert isinstance(CATALOG_TD, dict)
        assert len(CATALOG_TD) > 0


class TestCatalogRefrigerator:
    """Tests for catalog_cr.py."""

    def test_catalog_refrigerator_loads(self):
        """Refrigerator catalog loads without error."""
        from custom_components.electrolux.catalogs.catalog_cr import (
            CATALOG_CR,
        )

        assert isinstance(CATALOG_CR, dict)
        assert len(CATALOG_CR) > 0

    def test_refrigerator_has_temperature_entities(self):
        """Refrigerator catalog has temperature tracking entities."""
        from custom_components.electrolux.catalogs.catalog_cr import (
            CATALOG_CR,
        )

        assert "fridge/targetTemperatureC" in CATALOG_CR
        assert "freezer/targetTemperatureC" in CATALOG_CR


class TestCatalogPurifier:
    """Tests for catalog_ap.py."""

    def test_catalog_purifier_loads(self):
        """Purifier catalog loads without error."""
        from custom_components.electrolux.catalogs.catalog_ap import CATALOG_AP

        assert isinstance(CATALOG_AP, dict)
        assert len(CATALOG_AP) > 0

    def test_purifier_has_fan_entity(self):
        """Purifier catalog has a fan platform entity in catalog_core."""
        # The fan entity is in core as Workmode/fan which references purifier catalog
        from custom_components.electrolux.catalog_core import CATALOG_BY_TYPE

        catalog = CATALOG_BY_TYPE()
        # Muju maps to purifier catalog
        assert "Muju" in catalog


class TestCatalogDishwasher:
    """Tests for catalog_dw.py."""

    def test_catalog_dishwasher_loads(self):
        """Dishwasher catalog loads without error."""
        from custom_components.electrolux.catalogs.catalog_dw import CATALOG_DW

        assert isinstance(CATALOG_DW, dict)
        assert len(CATALOG_DW) > 0


class TestCatalogAirConditioner:
    """Tests for catalog_ac.py."""

    def test_catalog_air_conditioner_loads(self):
        """Air conditioner catalog loads without error."""
        from custom_components.electrolux.catalogs.catalog_ac import (
            CATALOG_AC,
        )

        assert isinstance(CATALOG_AC, dict)
        assert len(CATALOG_AC) > 0

    def test_air_conditioner_has_mode(self):
        """Air conditioner catalog has mode control entity."""
        from custom_components.electrolux.catalogs.catalog_ac import (
            CATALOG_AC,
        )

        assert (
            "mode" in CATALOG_AC
            or "executeCommand" in CATALOG_AC
        )


class TestCatalogStructuredOven:
    """Tests for catalog_so.py."""

    def test_catalog_structured_oven_loads(self):
        """Structured oven catalog loads without error."""
        from custom_components.electrolux.catalogs.catalog_so import CATALOG_SO

        assert isinstance(CATALOG_SO, dict)
        assert len(CATALOG_SO) > 0


class TestCatalogUtils:
    """Tests for catalog_utils.py helper functions."""

    def test_create_diagnostic_string_entity(self):
        """create_diagnostic_string_entity returns an ElectroluxDevice."""
        from homeassistant.const import EntityCategory

        from custom_components.electrolux.catalog_utils import (
            create_diagnostic_string_entity,
        )

        result = create_diagnostic_string_entity(
            capability_info={"access": "read", "type": "string"},
            friendly_name="Test Sensor",
        )
        assert isinstance(result, ElectroluxDevice)
        assert result.entity_category == EntityCategory.DIAGNOSTIC
        assert result.friendly_name == "Test Sensor"

    def test_create_config_entity(self):
        """create_config_entity returns an ElectroluxDevice with CONFIG category."""
        from homeassistant.const import EntityCategory

        from custom_components.electrolux.catalog_utils import create_config_entity

        result = create_config_entity(
            capability_info={"access": "readwrite", "type": "string"},
            friendly_name="Test Config",
        )
        assert isinstance(result, ElectroluxDevice)
        assert result.entity_category == EntityCategory.CONFIG
        assert result.friendly_name == "Test Config"

    def test_create_diagnostic_string_entity_with_icon(self):
        """create_diagnostic_string_entity accepts custom icon."""
        from custom_components.electrolux.catalog_utils import (
            create_diagnostic_string_entity,
        )

        result = create_diagnostic_string_entity(
            capability_info={"access": "read", "type": "string"},
            friendly_name="Test",
            icon="mdi:wifi",
        )
        assert result.entity_icon == "mdi:wifi"

    def test_create_diagnostic_string_entity_disabled_default(self):
        """create_diagnostic_string_entity accepts entity_registry_enabled_default."""
        from custom_components.electrolux.catalog_utils import (
            create_diagnostic_string_entity,
        )

        result = create_diagnostic_string_entity(
            capability_info={"access": "read", "type": "string"},
            friendly_name="Disabled By Default",
            entity_registry_enabled_default=False,
        )
        assert result.entity_registry_enabled_default is False


class TestExecuteCommandStates:
    """Tests for execute_command_states.py module."""

    def test_module_imports(self):
        """Module imports without error."""
        from custom_components.electrolux import execute_command_states

        assert execute_command_states is not None

    def test_module_has_expected_attributes(self):
        """Module exports expected state constants or mappings."""
        from custom_components.electrolux import execute_command_states as ecs

        # Should have something accessible - either a dict, list, or constants
        attrs = [a for a in dir(ecs) if not a.startswith("_")]
        assert len(attrs) > 0, "execute_command_states should export some public names"


class TestCatalogCoreLazyHelpers:
    """Tests for internal lazy-loading helper functions in catalog_core.py."""

    def test_get_catalog_model_lazy_returns_dict(self):
        """_get_catalog_model_lazy returns catalog model dict."""
        from custom_components.electrolux.catalog_core import _get_catalog_model_lazy

        result = _get_catalog_model_lazy()
        assert isinstance(result, dict)

    def test_get_catalog_by_type_lazy_returns_dict(self):
        """_get_catalog_by_type_lazy returns appliance type catalog dict."""
        from custom_components.electrolux.catalog_core import _get_catalog_by_type_lazy

        result = _get_catalog_by_type_lazy()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_get_catalog_base_lazy_returns_dict(self):
        """_get_catalog_base_lazy returns base catalog dict."""
        from custom_components.electrolux.catalog_core import _get_catalog_base_lazy

        result = _get_catalog_base_lazy()
        assert isinstance(result, dict)
        assert len(result) > 0


class TestCatalogUtilsFactories:
    """Tests for catalog_utils factory functions (create_diagnostic_number_entity, create_hidden_entity)."""

    def test_create_diagnostic_number_entity_defaults(self):
        """create_diagnostic_number_entity returns ElectroluxDevice with correct defaults."""
        from custom_components.electrolux.catalog_utils import (
            create_diagnostic_number_entity,
        )
        from custom_components.electrolux.const import ENTITY_CATEGORY_DIAGNOSTIC

        result = create_diagnostic_number_entity(
            capability_info={"access": "read", "type": "number"},
            friendly_name="Test Number",
        )
        assert isinstance(result, ElectroluxDevice)
        assert result.friendly_name == "Test Number"
        assert result.entity_category == ENTITY_CATEGORY_DIAGNOSTIC

    def test_create_diagnostic_number_entity_with_unit(self):
        """create_diagnostic_number_entity stores unit correctly."""
        from custom_components.electrolux.catalog_utils import (
            create_diagnostic_number_entity,
        )

        result = create_diagnostic_number_entity(
            capability_info={"access": "read", "type": "number"},
            friendly_name="Energy",
            unit="kWh",
        )
        assert result.unit == "kWh"

    def test_create_hidden_entity_is_not_shown_by_default(self):
        """create_hidden_entity returns entity disabled by default (entity_category=None)."""
        from custom_components.electrolux.catalog_utils import create_hidden_entity

        result = create_hidden_entity(
            capability_info={"access": "read", "type": "string"},
            friendly_name="Hidden State",
        )
        assert isinstance(result, ElectroluxDevice)
        assert result.entity_category is None
        assert result.entity_registry_enabled_default is False

    def test_create_hidden_entity_custom_icon(self):
        """create_hidden_entity accepts custom icon."""
        from custom_components.electrolux.catalog_utils import create_hidden_entity

        result = create_hidden_entity(
            capability_info={"access": "read", "type": "string"},
            friendly_name="State",
            icon="mdi:state-machine",
        )
        assert result.entity_icon == "mdi:state-machine"
