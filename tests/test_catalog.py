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
            assert isinstance(
                value, ElectroluxDevice
            ), f"Catalog entry '{key}' is {type(value)}, expected ElectroluxDevice"

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
    """Tests for catalog_oven.py."""

    def test_catalog_oven_loads(self):
        """Oven catalog loads without error."""
        from custom_components.electrolux.catalog_oven import CATALOG_OVEN

        assert isinstance(CATALOG_OVEN, dict)
        assert len(CATALOG_OVEN) > 0

    def test_oven_entities_are_electrolux_devices(self):
        """All oven catalog values are ElectroluxDevice instances."""
        from custom_components.electrolux.catalog_oven import CATALOG_OVEN

        for key, value in CATALOG_OVEN.items():
            assert isinstance(
                value, ElectroluxDevice
            ), f"Oven catalog entry '{key}' is {type(value)}"

    def test_oven_has_temperature_entities(self):
        """Oven catalog has temperature entities."""
        from custom_components.electrolux.catalog_oven import CATALOG_OVEN

        assert (
            "targetTemperatureC" in CATALOG_OVEN
            or "displayTemperatureC" in CATALOG_OVEN
        )

    def test_oven_has_execute_command(self):
        """Oven catalog has executeCommand entity."""
        from custom_components.electrolux.catalog_oven import CATALOG_OVEN

        assert "executeCommand" in CATALOG_OVEN


class TestCatalogWasher:
    """Tests for catalog_washer.py."""

    def test_catalog_washer_loads(self):
        """Washer catalog loads without error."""
        from custom_components.electrolux.catalog_washer import CATALOG_WASHER

        assert isinstance(CATALOG_WASHER, dict)
        assert len(CATALOG_WASHER) > 0

    def test_washer_entities_are_electrolux_devices(self):
        """All washer catalog values are ElectroluxDevice instances."""
        from custom_components.electrolux.catalog_washer import CATALOG_WASHER

        for key, value in CATALOG_WASHER.items():
            assert isinstance(
                value, ElectroluxDevice
            ), f"Washer catalog entry '{key}' is {type(value)}"


class TestCatalogWasherDryer:
    """Tests for catalog_washer_dryer.py."""

    def test_catalog_washer_dryer_loads(self):
        """Washer-dryer catalog loads without error."""
        from custom_components.electrolux.catalog_washer_dryer import (
            CATALOG_WASHER_DRYER,
        )

        assert isinstance(CATALOG_WASHER_DRYER, dict)
        assert len(CATALOG_WASHER_DRYER) > 0


class TestCatalogDryer:
    """Tests for catalog_dryer.py."""

    def test_catalog_dryer_loads(self):
        """Dryer catalog loads without error."""
        from custom_components.electrolux.catalog_dryer import CATALOG_DRYER

        assert isinstance(CATALOG_DRYER, dict)
        assert len(CATALOG_DRYER) > 0


class TestCatalogRefrigerator:
    """Tests for catalog_refrigerator.py."""

    def test_catalog_refrigerator_loads(self):
        """Refrigerator catalog loads without error."""
        from custom_components.electrolux.catalog_refrigerator import (
            CATALOG_REFRIGERATOR,
        )

        assert isinstance(CATALOG_REFRIGERATOR, dict)
        assert len(CATALOG_REFRIGERATOR) > 0

    def test_refrigerator_has_temperature_entities(self):
        """Refrigerator catalog has temperature tracking entities."""
        from custom_components.electrolux.catalog_refrigerator import (
            CATALOG_REFRIGERATOR,
        )

        assert "fridge/targetTemperatureC" in CATALOG_REFRIGERATOR
        assert "freezer/targetTemperatureC" in CATALOG_REFRIGERATOR


class TestCatalogPurifier:
    """Tests for catalog_purifier.py."""

    def test_catalog_purifier_loads(self):
        """Purifier catalog loads without error (exported as A9 dict)."""
        from custom_components.electrolux.catalog_purifier import A9

        assert isinstance(A9, dict)
        assert len(A9) > 0

    def test_purifier_has_fan_entity(self):
        """Purifier catalog has a fan platform entity in catalog_core."""
        # The fan entity is in core as Workmode/fan which references purifier catalog
        from custom_components.electrolux.catalog_core import CATALOG_BY_TYPE

        catalog = CATALOG_BY_TYPE()
        # Muju maps to purifier catalog
        assert "Muju" in catalog


class TestCatalogDishwasher:
    """Tests for catalog_dishwasher.py."""

    def test_catalog_dishwasher_loads(self):
        """Dishwasher catalog loads without error."""
        from custom_components.electrolux.catalog_dishwasher import CATALOG_DISHWASHER

        assert isinstance(CATALOG_DISHWASHER, dict)
        assert len(CATALOG_DISHWASHER) > 0


class TestCatalogMicrowave:
    """Tests for catalog_microwave.py."""

    def test_catalog_microwave_loads(self):
        """Microwave catalog loads without error."""
        from custom_components.electrolux.catalog_microwave import CATALOG_MICROWAVE

        assert isinstance(CATALOG_MICROWAVE, dict)
        assert len(CATALOG_MICROWAVE) > 0


class TestCatalogAirConditioner:
    """Tests for catalog_air_conditioner.py."""

    def test_catalog_air_conditioner_loads(self):
        """Air conditioner catalog loads without error."""
        from custom_components.electrolux.catalog_air_conditioner import (
            CATALOG_AIR_CONDITIONER,
        )

        assert isinstance(CATALOG_AIR_CONDITIONER, dict)
        assert len(CATALOG_AIR_CONDITIONER) > 0

    def test_air_conditioner_has_mode(self):
        """Air conditioner catalog has mode control entity."""
        from custom_components.electrolux.catalog_air_conditioner import (
            CATALOG_AIR_CONDITIONER,
        )

        assert (
            "mode" in CATALOG_AIR_CONDITIONER
            or "executeCommand" in CATALOG_AIR_CONDITIONER
        )


class TestCatalogSteamOven:
    """Tests for catalog_steam_oven.py."""

    def test_catalog_steam_oven_loads(self):
        """Steam oven catalog loads without error."""
        from custom_components.electrolux.catalog_steam_oven import CATALOG_STEAM_OVEN

        assert isinstance(CATALOG_STEAM_OVEN, dict)
        assert len(CATALOG_STEAM_OVEN) > 0


class TestCatalogUtils:
    """Tests for catalog_utils.py helper functions."""

    def test_create_diagnostic_string_entity(self):
        """create_diagnostic_string_entity returns an ElectroluxDevice."""
        from homeassistant.helpers.entity import EntityCategory

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
        from homeassistant.helpers.entity import EntityCategory

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
