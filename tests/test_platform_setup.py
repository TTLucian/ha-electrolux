"""Test platform setup for all Electrolux platforms."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import Platform


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "api_key": "test_api_key",
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
    }
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with appliances."""
    coordinator = MagicMock()
    coordinator.data = {"appliances": MagicMock()}

    # Mock appliances
    mock_appliance = MagicMock()
    mock_appliance.pnc_id = "test_appliance_123"
    mock_appliance.name = "Test Appliance"
    mock_appliance.brand = "Electrolux"
    mock_appliance.model = "TEST123"
    mock_appliance.appliance_type = "OV"  # Oven
    mock_appliance.entities = []

    coordinator.data["appliances"].appliances = {"test_appliance_123": mock_appliance}
    return coordinator


class TestSensorPlatformSetup:
    """Test sensor platform setup."""

    @pytest.mark.asyncio
    async def test_sensor_platform_setup_success(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test successful sensor platform setup."""
        from custom_components.electrolux.sensor import async_setup_entry

        # Add entities to the appliance
        mock_entity = MagicMock()
        mock_entity.entity_type = Platform.SENSOR
        mock_coordinator.data["appliances"].appliances[
            "test_appliance_123"
        ].entities = [mock_entity]

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None  # Function returns None on success
        mock_add_entities.assert_called_once()
        # Verify entities were added
        call_args = mock_add_entities.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0] == mock_entity

    @pytest.mark.asyncio
    async def test_sensor_platform_setup_no_appliances(
        self, mock_hass, mock_config_entry
    ):
        """Test sensor platform setup with no appliances."""
        from custom_components.electrolux.sensor import async_setup_entry

        mock_coordinator = MagicMock()
        mock_coordinator.data = {}  # No appliances
        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_not_called()


class TestNumberPlatformSetup:
    """Test number platform setup."""

    @pytest.mark.asyncio
    async def test_number_platform_setup_success(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test successful number platform setup."""
        from custom_components.electrolux.number import async_setup_entry

        # Add number entities
        mock_entity = MagicMock()
        mock_entity.entity_type = Platform.NUMBER
        mock_coordinator.data["appliances"].appliances[
            "test_appliance_123"
        ].entities = [mock_entity]

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_called_once()


class TestSelectPlatformSetup:
    """Test select platform setup."""

    @pytest.mark.asyncio
    async def test_select_platform_setup_success(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test successful select platform setup."""
        from custom_components.electrolux.select import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = Platform.SELECT
        mock_coordinator.data["appliances"].appliances[
            "test_appliance_123"
        ].entities = [mock_entity]

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_called_once()


class TestSwitchPlatformSetup:
    """Test switch platform setup."""

    @pytest.mark.asyncio
    async def test_switch_platform_setup_success(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test successful switch platform setup."""
        from custom_components.electrolux.switch import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = Platform.SWITCH
        mock_coordinator.data["appliances"].appliances[
            "test_appliance_123"
        ].entities = [mock_entity]

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_called_once()


class TestBinarySensorPlatformSetup:
    """Test binary sensor platform setup."""

    @pytest.mark.asyncio
    async def test_binary_sensor_platform_setup_success(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test successful binary sensor platform setup."""
        from custom_components.electrolux.binary_sensor import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = Platform.BINARY_SENSOR
        mock_coordinator.data["appliances"].appliances[
            "test_appliance_123"
        ].entities = [mock_entity]

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_called_once()


class TestButtonPlatformSetup:
    """Test button platform setup."""

    @pytest.mark.asyncio
    async def test_button_platform_setup_success(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test successful button platform setup."""
        from custom_components.electrolux.button import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = Platform.BUTTON
        mock_coordinator.data["appliances"].appliances[
            "test_appliance_123"
        ].entities = [mock_entity]

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_called_once()


class TestTextPlatformSetup:
    """Test text platform setup."""

    @pytest.mark.asyncio
    async def test_text_platform_setup_success(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test successful text platform setup."""
        from custom_components.electrolux.text import async_setup_entry

        mock_entity = MagicMock()
        mock_entity.entity_type = Platform.TEXT
        mock_coordinator.data["appliances"].appliances[
            "test_appliance_123"
        ].entities = [mock_entity]

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_called_once()


class TestClimatePlatformSetup:
    """Test climate platform setup."""

    @pytest.mark.asyncio
    async def test_climate_platform_setup_ac_appliance(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test climate platform creates entity for AC appliances."""
        from custom_components.electrolux.climate import async_setup_entry

        # Set appliance type to AC
        mock_coordinator.data["appliances"].appliances[
            "test_appliance_123"
        ].appliance_type = "AC"

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_called_once()
        # Verify climate entity was created
        call_args = mock_add_entities.call_args[0][0]
        assert len(call_args) == 1

    @pytest.mark.asyncio
    async def test_climate_platform_setup_non_ac_appliance(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test climate platform ignores non-AC appliances."""
        from custom_components.electrolux.climate import async_setup_entry

        # Appliance type is "OV" (oven), not "AC"
        mock_coordinator.data["appliances"].appliances[
            "test_appliance_123"
        ].appliance_type = "OV"

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        # No entities should be added for non-AC appliances
        call_args = mock_add_entities.call_args[0][0]
        assert len(call_args) == 0

    @pytest.mark.asyncio
    async def test_climate_platform_setup_multiple_ac_appliances(
        self, mock_hass, mock_config_entry
    ):
        """Test climate platform handles multiple AC appliances."""
        from custom_components.electrolux.climate import async_setup_entry

        # Create multiple AC appliances
        mock_coordinator = MagicMock()
        mock_appliances = {}

        for i in range(3):
            mock_appliance = MagicMock()
            mock_appliance.pnc_id = f"test_ac_{i}"
            mock_appliance.name = f"AC {i}"
            mock_appliance.appliance_type = "AC"
            mock_appliances[f"test_ac_{i}"] = mock_appliance

        mock_coordinator.data = {"appliances": MagicMock(appliances=mock_appliances)}

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_called_once()
        # Verify 3 climate entities were created
        call_args = mock_add_entities.call_args[0][0]
        assert len(call_args) == 3

    @pytest.mark.asyncio
    async def test_climate_setup_extracts_capabilities_from_appliance_data(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test line 53 — capabilities_dict is populated from appliance.data.capabilities."""
        from custom_components.electrolux.climate import async_setup_entry

        mock_appliance = mock_coordinator.data["appliances"].appliances[
            "test_appliance_123"
        ]
        mock_appliance.appliance_type = "AC"
        # Give the appliance real data with capabilities
        mock_appliance.data = MagicMock()
        mock_appliance.data.capabilities = {
            "mode": {"values": {"AUTO": {}, "COOL": {}}},
            "targetTemperatureC": {"min": 16, "max": 30},
            "unknownAttr": {},  # Not in climate_attrs, should be ignored
        }

        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        call_args = mock_add_entities.call_args[0][0]
        assert len(call_args) == 1
        entity = call_args[0]
        # Verified climate-relevant attrs were extracted; unknown attr was not
        assert "mode" in entity.capability
        assert "targetTemperatureC" in entity.capability
        assert "unknownAttr" not in entity.capability


class TestPlatformSetupErrorHandling:
    """Test error handling in platform setup."""

    @pytest.mark.asyncio
    async def test_platform_setup_handles_missing_coordinator(
        self, mock_hass, mock_config_entry
    ):
        """Test platform setup handles coordinator with empty data gracefully."""
        from custom_components.electrolux.sensor import async_setup_entry

        mock_coordinator = MagicMock()
        mock_coordinator.data = {}  # No appliances key
        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_platform_setup_handles_none_appliances(
        self, mock_hass, mock_config_entry
    ):
        """Test platform setup handles None appliances."""
        from custom_components.electrolux.sensor import async_setup_entry

        mock_coordinator = MagicMock()
        mock_coordinator.data = {"appliances": None}
        mock_config_entry.runtime_data = mock_coordinator
        mock_add_entities = MagicMock()

        result = await async_setup_entry(
            mock_hass, mock_config_entry, mock_add_entities
        )

        assert result is None
        mock_add_entities.assert_not_called()
