"""Test program capabilities lookup for different appliance types.

This test suite validates the fix for program-dependent entity support across
different appliance types (ovens vs dryers) which store capabilities in different
locations in the data structure.
"""

from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.electrolux.const import NUMBER
from custom_components.electrolux.number import ElectroluxNumber


class TestProgramCapabilitiesLookup:
    """Test _get_program_capabilities helper method works for all appliance types."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.hass.loop = MagicMock()
        coordinator.hass.loop.time.return_value = 1000000.0
        coordinator.config_entry = MagicMock()
        coordinator._last_update_times = {}

        # Setup mock appliances structure
        mock_appliances = MagicMock()
        mock_appliance = MagicMock()
        mock_appliances.get_appliance.return_value = mock_appliance
        coordinator.data = {"appliances": mock_appliances}

        return coordinator

    @pytest.fixture
    def base_entity(self, mock_coordinator):
        """Create a base test entity."""
        capability = {"access": "readwrite", "type": "number"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Test Control",
            config_entry=mock_coordinator.config_entry,
            pnc_id="TEST_PNC",
            entity_type=NUMBER,
            entity_name="test_control",
            entity_attr="userSelections/antiCreaseValue",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=EntityCategory.CONFIG,
            icon="mdi:test",
        )
        entity.hass = mock_coordinator.hass
        return entity

    def test_get_program_capabilities_oven_structure(
        self, base_entity, mock_coordinator
    ):
        """Test program capabilities lookup for oven-style appliances.

        Ovens store program capabilities under:
        capabilities["program"]["values"][program_name]
        """
        # Setup oven-style capabilities structure through coordinator
        mock_appliance = mock_coordinator.data["appliances"].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "program": {
                "values": {
                    "ECO_MODE": {
                        "targetTemperatureC": {
                            "min": 30,
                            "max": 230,
                            "step": 5,
                            "disabled": False,
                        }
                    },
                    "DEFROST": {
                        "targetTemperatureC": {
                            "min": 30,
                            "max": 60,
                            "step": 5,
                            "disabled": False,
                        }
                    },
                }
            }
        }

        # Test ECO_MODE capabilities
        eco_caps = base_entity._get_program_capabilities("ECO_MODE")
        assert "targetTemperatureC" in eco_caps
        assert eco_caps["targetTemperatureC"]["min"] == 30
        assert eco_caps["targetTemperatureC"]["max"] == 230

        # Test DEFROST capabilities have different constraints
        defrost_caps = base_entity._get_program_capabilities("DEFROST")
        assert "targetTemperatureC" in defrost_caps
        assert defrost_caps["targetTemperatureC"]["min"] == 30
        assert defrost_caps["targetTemperatureC"]["max"] == 60

    def test_get_program_capabilities_dryer_structure(
        self, base_entity, mock_coordinator
    ):
        """Test program capabilities lookup for dryer-style appliances.

        Dryers store program capabilities under:
        capabilities["userSelections/programUID"]["values"][program_name]
        """
        # Setup dryer-style capabilities structure through coordinator
        mock_appliance = mock_coordinator.data["appliances"].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "userSelections/programUID": {
                "values": {
                    "COTTON_PR_COTTONSECO": {
                        "userSelections/antiCreaseValue": {
                            "min": 30,
                            "max": 120,
                            "step": 30,
                            "disabled": False,
                        },
                        "userSelections/humidityTarget": {
                            "values": {"CUPBOARD": {}, "IRON": {}}
                        },
                    },
                    "SHOES_PR_RUNNINGSHOES": {
                        "userSelections/drynessValue": {
                            "values": {"MAXIMUM": {}, "MEDIUM": {}, "MINIMUM": {}}
                        }
                        # Note: antiCreaseValue NOT in this program
                    },
                }
            }
        }

        # Test COTTON program has antiCreaseValue
        cotton_caps = base_entity._get_program_capabilities("COTTON_PR_COTTONSECO")
        assert "userSelections/antiCreaseValue" in cotton_caps
        assert cotton_caps["userSelections/antiCreaseValue"]["min"] == 30
        assert cotton_caps["userSelections/antiCreaseValue"]["max"] == 120
        assert cotton_caps["userSelections/antiCreaseValue"]["step"] == 30

        # Test SHOES program doesn't have antiCreaseValue
        shoes_caps = base_entity._get_program_capabilities("SHOES_PR_RUNNINGSHOES")
        assert "userSelections/antiCreaseValue" not in shoes_caps
        assert "userSelections/drynessValue" in shoes_caps

    def test_get_program_capabilities_cycle_personalization_structure(
        self, base_entity, mock_coordinator
    ):
        """Test program capabilities lookup with cyclePersonalization fallback."""
        # Setup alternative structure through coordinator
        mock_appliance = mock_coordinator.data["appliances"].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "cyclePersonalization/programUID": {
                "values": {
                    "SOME_PROGRAM": {
                        "someControl": {"min": 0, "max": 100, "disabled": False}
                    }
                }
            }
        }

        # Should find capabilities in fallback location
        caps = base_entity._get_program_capabilities("SOME_PROGRAM")
        assert "someControl" in caps
        assert caps["someControl"]["min"] == 0

    def test_get_program_capabilities_no_appliance_data(
        self, base_entity, mock_coordinator
    ):
        """Test graceful handling when appliance data is missing."""
        # Return None for get_appliance
        mock_coordinator.data["appliances"].get_appliance.return_value = None
        caps = base_entity._get_program_capabilities("ANY_PROGRAM")
        assert caps == {}

    def test_get_program_capabilities_program_not_found(
        self, base_entity, mock_coordinator
    ):
        """Test when program doesn't exist in any location."""
        mock_appliance = mock_coordinator.data["appliances"].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "program": {"values": {"EXISTING_PROGRAM": {}}}
        }

        caps = base_entity._get_program_capabilities("NONEXISTENT_PROGRAM")
        assert caps == {}


class TestIsSupportedByProgramWithRealData:
    """Test _is_supported_by_program with real appliance data structures."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.config_entry = MagicMock()

        # Setup mock appliances structure
        mock_appliances = MagicMock()
        mock_appliance = MagicMock()
        mock_appliances.get_appliance.return_value = mock_appliance
        coordinator.data = {"appliances": mock_appliances}

        return coordinator

    def test_dryer_anticrease_supported_by_cotton_program(self, mock_coordinator):
        """Test antiCreaseValue is supported by COTTON program on dryers."""
        # Create entity for antiCreaseValue
        capability = {"access": "readwrite", "type": "number"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Anti-Crease Duration",
            config_entry=mock_coordinator.config_entry,
            pnc_id="916099971",
            entity_type=NUMBER,
            entity_name="anti_crease_duration",
            entity_attr="userSelections/antiCreaseValue",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:hanger",
        )

        # Setup dryer with COTTON program that supports antiCreaseValue
        mock_appliance = mock_coordinator.data["appliances"].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "userSelections/programUID": {
                "values": {
                    "COTTON_PR_COTTONSECO": {
                        "userSelections/antiCreaseValue": {
                            "min": 30,
                            "max": 120,
                            "step": 30,
                            "disabled": False,
                        }
                    }
                }
            }
        }
        entity._reported_state_cache = {
            "userSelections": {"programUID": "COTTON_PR_COTTONSECO"}
        }
        entity._program_cache_key = "COTTON_PR_COTTONSECO"

        # Clear cache to force recomputation
        entity._is_supported_cache = None

        # Test that entity IS supported by this program
        assert entity._is_supported_by_program() is True

    def test_dryer_anticrease_not_supported_by_shoes_program(self, mock_coordinator):
        """Test antiCreaseValue is NOT supported by SHOES program on dryers."""
        capability = {"access": "readwrite", "type": "number"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Anti-Crease Duration",
            config_entry=mock_coordinator.config_entry,
            pnc_id="916099971",
            entity_type=NUMBER,
            entity_name="anti_crease_duration",
            entity_attr="userSelections/antiCreaseValue",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:hanger",
        )

        # Setup dryer with SHOES program that does NOT support antiCreaseValue
        mock_appliance = mock_coordinator.data["appliances"].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "userSelections/programUID": {
                "values": {
                    "SHOES_PR_RUNNINGSHOES": {
                        "userSelections/drynessValue": {
                            "values": {"MAXIMUM": {}, "MEDIUM": {}, "MINIMUM": {}}
                        }
                        # antiCreaseValue NOT present
                    }
                }
            }
        }
        entity._reported_state_cache = {
            "userSelections": {"programUID": "SHOES_PR_RUNNINGSHOES"}
        }
        entity._program_cache_key = "SHOES_PR_RUNNINGSHOES"

        # Clear cache to force recomputation
        entity._is_supported_cache = None

        # Test that entity is NOT supported by this program
        assert entity._is_supported_by_program() is False

    def test_oven_temperature_supported_by_program(self, mock_coordinator):
        """Test oven temperature control supported by program."""
        capability = {"access": "readwrite", "type": "number"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:thermometer",
        )

        # Setup oven with program that supports temperature control
        mock_appliance = mock_coordinator.data["appliances"].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "program": {
                "values": {
                    "CONVENTIONAL": {
                        "targetTemperatureC": {
                            "min": 30,
                            "max": 250,
                            "step": 5,
                            "disabled": False,
                        }
                    }
                }
            }
        }
        entity._reported_state_cache = {"program": "CONVENTIONAL"}
        entity._program_cache_key = "CONVENTIONAL"

        # Clear cache
        entity._is_supported_cache = None

        # Test that entity IS supported
        assert entity._is_supported_by_program() is True


class TestGetProgramConstraintWithRealData:
    """Test _get_program_constraint with real appliance data structures."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.hass = MagicMock()
        coordinator.config_entry = MagicMock()

        # Setup mock appliances structure
        mock_appliances = MagicMock()
        mock_appliance = MagicMock()
        mock_appliances.get_appliance.return_value = mock_appliance
        coordinator.data = {"appliances": mock_appliances}

        return coordinator

    def test_dryer_anticrease_constraints_from_userselections(self, mock_coordinator):
        """Test retrieving min/max/step constraints for dryer controls."""
        capability = {"access": "readwrite", "type": "number"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Anti-Crease Duration",
            config_entry=mock_coordinator.config_entry,
            pnc_id="916099971",
            entity_type=NUMBER,
            entity_name="anti_crease_duration",
            entity_attr="userSelections/antiCreaseValue",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:hanger",
        )

        # Setup dryer with program-specific constraints
        mock_appliance = mock_coordinator.data["appliances"].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "userSelections/programUID": {
                "values": {
                    "COTTON_PR_COTTONSECO": {
                        "userSelections/antiCreaseValue": {
                            "min": 30,
                            "max": 120,
                            "step": 30,
                            "default": 30,
                        }
                    }
                }
            }
        }
        entity.reported_state = {
            "userSelections": {"programUID": "COTTON_PR_COTTONSECO"}
        }

        # Clear constraint cache
        entity._constraints_cache = {}

        # Test constraint retrieval
        assert entity._get_program_constraint("min") == 30
        assert entity._get_program_constraint("max") == 120
        assert entity._get_program_constraint("step") == 30
        assert entity._get_program_constraint("default") == 30

    def test_oven_temperature_constraints_from_program(self, mock_coordinator):
        """Test retrieving constraints for oven temperature from program location."""
        capability = {"access": "readwrite", "type": "number"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Target Temperature",
            config_entry=mock_coordinator.config_entry,
            pnc_id="OVEN_123",
            entity_type=NUMBER,
            entity_name="target_temperature",
            entity_attr="targetTemperatureC",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:thermometer",
        )

        # Setup oven with program-specific temperature constraints
        mock_appliance = mock_coordinator.data["appliances"].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "program": {
                "values": {
                    "DEFROST": {
                        "targetTemperatureC": {
                            "min": 30,
                            "max": 60,
                            "step": 5,
                            "default": 40,
                        }
                    }
                }
            }
        }
        entity.reported_state = {"program": "DEFROST"}

        # Clear constraint cache
        entity._constraints_cache = {}

        # Test constraint retrieval for DEFROST program
        assert entity._get_program_constraint("min") == 30
        assert entity._get_program_constraint("max") == 60
        assert entity._get_program_constraint("step") == 5
        assert entity._get_program_constraint("default") == 40

    def test_constraints_change_when_program_changes(self, mock_coordinator):
        """Test that constraints update when switching between programs."""
        capability = {"access": "readwrite", "type": "number"}
        entity = ElectroluxNumber(
            coordinator=mock_coordinator,
            name="Anti-Crease Duration",
            config_entry=mock_coordinator.config_entry,
            pnc_id="916099971",
            entity_type=NUMBER,
            entity_name="anti_crease_duration",
            entity_attr="userSelections/antiCreaseValue",
            entity_source=None,
            capability=capability,
            unit=None,
            device_class=None,
            entity_category=None,
            icon="mdi:hanger",
        )

        # Setup dryer with two programs with different constraints
        mock_appliance = mock_coordinator.data["appliances"].get_appliance.return_value
        mock_appliance.data.capabilities = {
            "userSelections/programUID": {
                "values": {
                    "COTTON_PR_COTTONSECO": {
                        "userSelections/antiCreaseValue": {
                            "min": 30,
                            "max": 120,
                            "step": 30,
                        }
                    },
                    "SYNTHETIC_PR_SYNTHETICS": {
                        "userSelections/antiCreaseValue": {
                            "min": 30,
                            "max": 90,
                            "step": 30,
                        }
                    },
                }
            }
        }

        # Test with COTTON program
        entity.reported_state = {
            "userSelections": {"programUID": "COTTON_PR_COTTONSECO"}
        }
        entity._constraints_cache = {}
        assert entity._get_program_constraint("max") == 120

        # Switch to SYNTHETIC program
        entity.reported_state = {
            "userSelections": {"programUID": "SYNTHETIC_PR_SYNTHETICS"}
        }
        entity._constraints_cache = {}  # Cache would be cleared by program change
        assert entity._get_program_constraint("max") == 90
