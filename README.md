# Home Assistant Electrolux Integration
<p align="center">
  <img src="https://img.shields.io/github/v/release/TTLucian/ha-electrolux?style=for-the-badge" />
  <img src="https://img.shields.io/github/license/TTLucian/ha-electrolux?style=for-the-badge" />
  <img src="https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge" />
  <img src="https://img.shields.io/github/actions/workflow/status/TTLucian/ha-electrolux/ci.yml?style=for-the-badge" />
  <a href="https://buymeacoffee.com/ttlucian"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Donate-yellow?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee" /></a>
</p>
## Description

A comprehensive Home Assistant integration for Electrolux appliances using the official Electrolux Group Developer API. This integration provides real-time monitoring and control of Electrolux and Electrolux-owned brand appliances including AEG, Frigidaire, and +home.

**Key Features:**
- ✅ Real-time appliance status updates via Server-Sent Events (SSE)
- ✅ Remote control with safety validation (respects appliance safety locks)
- ✅ Automatic model detection from Product Number Codes (PNC)
- ✅ Comprehensive sensor coverage (temperatures, states, diagnostics)
- ✅ Control entities (buttons, switches, numbers, selects)
- ✅ Multi-language support
- ✅ Robust error handling and connection management

**Disclaimer:** This Home Assistant integration was not made by Electrolux. It is not official, not developed, and not supported by Electrolux.

## Credits

**Maintained by [TTLucian](https://github.com/TTLucian)**

## 🧪 Testing Scripts

This repository includes comprehensive testing scripts to help you verify appliance compatibility and test API functionality before installing the integration. These scripts allow direct interaction with the Electrolux API to inspect your appliances and test commands.

📖 **[Testing Scripts Documentation](scripts/TESTING_SCRIPTS_README.md)** - Complete guide for using the testing tools

| Contributors | Support Link |
|-------------|-------------|
| [TTLucian](https://github.com/TTLucian) | [!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/TTLucian) |

## Prerequisites

### API Credentials Required

This integration requires API credentials from the official Electrolux Developer Portal.

**Note:** The official Electrolux API requires developer credentials obtained through their official developer portal.

#### How to Obtain API Credentials:

1. Visit the [Electrolux Developer Portal](https://developer.electrolux.one/dashboard)
2. Create a free developer account
3. Register a new application
4. Generate your API credentials:
   - **API Key** (Client ID)
   - **Access Token**
   - **Refresh Token**

**Important:** Keep your API credentials secure and never share them publicly.

### Device Setup

All appliances must be:
- Connected to your Electrolux account via the official mobile app
- Properly configured with aliases/names in the app
- Connected to the internet

## Installation

### HACS Installation (Recommended)

1. Add this repository to HACS: `https://github.com/TTLucian/ha-electrolux`
2. Search for "Electrolux" in HACS
3. Click Install
4. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/electrolux/` directory
2. Copy it to your Home Assistant `custom_components` folder
3. Restart Home Assistant

## Configuration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Electrolux"
4. Enter your API credentials:
   - API Key
   - Access Token
   - Refresh Token
5. The integration will automatically discover and add your appliances

## Supported Appliances

This integration works with Electrolux and Electrolux-owned brands (AEG, Frigidaire, +home) across multiple regions:

- **Europe/Middle East/Africa** (EMEA): My Electrolux Care, My AEG Care, Electrolux Kitchen, AEG Kitchen
- **Asia Pacific** (APAC): Electrolux Life
- **Latin America** (LATAM): Electrolux Home+
- **North America** (NA): Electrolux Oven, Frigidaire 2.0

### Device Types

**Ovens - tested**
- Electrolux SteamBake series
- AEG SteamBake and AssistedCooking series
- Real-time temperature monitoring
- Program control and status
- Safety lock validation

**Refrigerators**
- Electrolux UltimateTaste series
- Temperature monitoring
- Door status sensors

**Washing Machines**
- Electrolux UltimateCare and PerfectCare series
- AEG ÖKOKombi and AbsoluteCare series
- Cycle monitoring and control

**Dryers**
- Electrolux UltimateCare and PerfectCare series
- AEG AbsoluteCare series

**Dishwashers**
- Electrolux GlassCare and MaxiFlex series
- AEG GlassCare series

**Air Purifiers**
- Electrolux Pure A9 series
- Air quality monitoring and control

## Features

### Sensors
- Appliance state and status
- Temperature readings (current, target, food probe)
- Program and phase information
- Connection quality and diagnostics
- Door and safety lock status
- Water levels and tank status
- Filter life and maintenance alerts

### Controls
- Power on/off (with safety validation)
- Program selection
- Temperature settings
- Timer controls
- Light controls (ovens)
- Start/stop/reset commands

### Binary Sensors
- Door status
- Connection state
- Alert conditions

### Diagnostics
- Network interface information
- Software versions
- OTA update status
- Communication quality

## Troubleshooting

### Authentication Issues
- **403 Forbidden**: Check your API credentials from the developer portal - they may have expired. Regenerate your access token and refresh token from [Electrolux Developer Portal](https://developer.electrolux.one/dashboard)
- **Invalid Credentials**: Double-check your API key, access token, and refresh token from the developer portal

### Connection Issues
- Ensure appliances are connected to your Electrolux account
- Check internet connectivity of appliances
- Verify appliances are powered on and online

### Control Not Working
- Check if appliance has safety locks enabled (door open, child lock, etc.)
- Integration respects all appliance safety features
- Some controls may be disabled during active cycles

### Model Shows as Numbers
- The integration displays the actual product code (e.g., "944188772") used by Electrolux internally
- This is the most specific identifier available through the API
- Marketing model names (e.g., "BSE788380M") are not exposed by the API

### Debug Logging
Enable debug logging for detailed troubleshooting:
```yaml
logger:
  logs:
    custom_components.electrolux: debug
```

## Contributing

Contributions are welcome! This integration is actively maintained and improved.

### Development Setup
1. Fork the repository
2. Clone your fork
3. Install development dependencies: `pip install -r requirements-dev.txt`
4. Test scripts are available in the root directory for API testing

### Testing Your Appliances
Use the provided test scripts to verify API connectivity:
- `test_api_simple.py` - Basic appliance list test
- `test_appliance_details.py` - Detailed appliance information

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/TTLucian/ha-electrolux/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TTLucian/ha-electrolux/discussions)
- **Documentation**: [Electrolux Developer Portal](https://developer.electrolux.one/)
