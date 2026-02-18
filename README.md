# 🏠 Home Assistant Electrolux Integration
<p align="center">
  <img src="https://img.shields.io/github/v/release/TTLucian/ha-electrolux?style=for-the-badge" />
  <img src="https://img.shields.io/github/license/TTLucian/ha-electrolux?style=for-the-badge" />
  <img src="https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge" />
  <img src="https://img.shields.io/github/actions/workflow/status/TTLucian/ha-electrolux/ci.yml?style=for-the-badge" />
  <a href="https://buymeacoffee.com/ttlucian"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Donate-yellow?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee" /></a>
</p>
## 📖 Description

A comprehensive Home Assistant integration for Electrolux appliances using the official Electrolux Group Developer API. This integration provides real-time monitoring and control of Electrolux and Electrolux-owned brand appliances including AEG, Frigidaire, and +home.

**Key Features:**
- ✅ Real-time appliance status updates via Server-Sent Events (SSE)
- ✅ Remote control with safety validation (respects appliance safety locks)
- ✅ Automatic model detection from Product Number Codes (PNC)
- ✅ Comprehensive sensor coverage (temperatures, states, diagnostics)
- ✅ Control entities (buttons, switches, numbers, selects)
- ✅ Multi-language support
- ✅ Robust error handling and connection management

**⚠️ Disclaimer:** This Home Assistant integration was not made by Electrolux. It is not official, not developed, and not supported by Electrolux.

## 🌟 Credits

**Maintained by [TTLucian](https://github.com/TTLucian)**

| Contributors | Support Link |
|-------------|-------------|
| [TTLucian](https://github.com/TTLucian) | [!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/TTLucian) |

## 📋 Prerequisites

### 🔑 API Credentials Required

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

**⚠️ Important:** Keep your API credentials secure and never share them publicly.

### 📱 Device Setup

All appliances must be:
- Connected to your Electrolux account via the official mobile app
- Properly configured with aliases/names in the app
- Connected to the internet

## 💾 Installation

### 🎯 HACS Installation (Recommended)

1. Add this repository to HACS: `https://github.com/TTLucian/ha-electrolux`
2. Search for "Electrolux" in HACS
3. Click Install
4. Restart Home Assistant

### 🔧 Manual Installation

1. Download the `custom_components/electrolux/` directory
2. Copy it to your Home Assistant `custom_components` folder
3. Restart Home Assistant

## ⚙️ Configuration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Electrolux"
4. Enter your API credentials:
   - API Key
   - Access Token
   - Refresh Token
5. The integration will automatically discover and add your appliances

## 🔌 Supported Appliances

This integration works with Electrolux and Electrolux-owned brands (AEG, Frigidaire, +home) across multiple regions:

- **Europe/Middle East/Africa** (EMEA): My Electrolux Care, My AEG Care, Electrolux Kitchen, AEG Kitchen
- **Asia Pacific** (APAC): Electrolux Life
- **Latin America** (LATAM): Electrolux Home+
- **North America** (NA): Electrolux Oven, Frigidaire 2.0

### 🏷️ Device Types

**🍳 Ovens** - tested
- Electrolux SteamBake series
- AEG SteamBake and AssistedCooking series
- Real-time temperature monitoring
- Program control and status
- Safety lock validation

**❄️ Refrigerators**
- Electrolux UltimateTaste series
- Temperature monitoring and control for fridge, freezer, and extra cavity
- Fast mode control for rapid cooling/freezing
- Appliance mode selection (Normal/Demo/Service)
- Vacation mode and child lock controls (internal/external)
- Ice maker control and monitoring with defrost temperature
- Extra cavity with temperature cloning and fan control
- Filter status monitoring and reset (water and air filters)
- Humidity sensor and reminder time settings
- Cooling valve and defrost routine monitoring
- Door status monitoring for all compartments

**🧺 Washing Machines**
- Electrolux UltimateCare and PerfectCare series
- AEG ÖKOKombi and AbsoluteCare series
- Comprehensive cycle monitoring and control
- Appliance state tracking (IDLE, RUNNING, PAUSED, END_OF_CYCLE, etc.)
- Cycle phase and sub-phase monitoring
- Door status and lock control
- Start time scheduling and delayed start
- Time-to-end countdown
- Auto-dosing system with tank configurations and fine-tuning
- Steam level control (OFF, MIN, MED, MAX)
- Spin speed selection (400-1600 RPM)
- Temperature settings (COLD, 20°C-90°C)
- Program selection with per-program configurations
- Extra rinse and end-of-cycle sound options
- Load weight monitoring and optisense results
- Maintenance alerts and diagnostics
- Remote control enablement
- Network interface monitoring (WiFi quality, OTA updates, software version)
- Appliance working time and cycle counters

**🧺💨 Washer-Dryers**
- Electrolux UltimateCare and PerfectCare series
- AEG AbsoluteCare series
- Full integrated washing and drying control
- Dry mode toggle with dedicated drying controls
- Drying time selection (0-300 minutes)
- Dryness level selection (CUPBOARD, EXTRA, IRON)
- Wet mode control for specialized washing
- Dual load weight monitoring (washing and drying cycles)
- Integrated wash+dry program cycles
- All washing machine features plus dryer-specific controls
- Fluff drawer maintenance alerts
- Separate drying cycle counters and statistics

**❄️🌡️ Air Conditioners**
- Electrolux air conditioning units
- Full climate control integration with Home Assistant
- Temperature control (16-30°C / 60-86°F) with dual scale support
- Operating modes: AUTO, COOL, HEAT, DRY, FAN
- Fan speed control: AUTO, LOW, MEDIUM, HIGH, QUIET, TURBO
- Swing control: OFF, VERTICAL, HORIZONTAL, BOTH
- Humidity control and monitoring (30-70% range)
- Ambient temperature and humidity sensors
- Power state management with safety validation
- Start/stop/reset command support
- Real-time status monitoring and diagnostics
- Network interface monitoring and OTA updates

**💨 Dryers (Tumble Dryers)**
- Electrolux UltimateCare and PerfectCare series
- AEG AbsoluteCare series
- Comprehensive drying cycle monitoring and control
- Appliance state tracking (IDLE, RUNNING, PAUSED, END_OF_CYCLE, etc.)
- Cycle phase and sub-phase monitoring
- Door status and lock control
- Start time scheduling and delayed start
- Time-to-end countdown
- Drying time selection (0-300 minutes)
- Dryness level selection (CUPBOARD, EXTRA, IRON, AIR_DRY)
- Temperature settings (HIGH, MEDIUM, LOW, REFRESH)
- Program selection with per-program configurations (COTTON, SYNTHETICS, DELICATES, WOOL, etc.)
- Anti-crease protection
- Load weight monitoring
- Network interface monitoring (WiFi quality, OTA updates, software version)
- Remote control enablement
- Appliance working time and cycle counters
- Fluff filter maintenance alerts and cleaning reminders
- Energy efficiency tracking and statistics

**🍽️ Dishwashers**

- Comprehensive dishwashing cycle monitoring and control
- Appliance state tracking (IDLE, RUNNING, PAUSED, END_OF_CYCLE, etc.)
- Cycle phase and sub-phase monitoring
- Door status and lock control
- Start time scheduling and delayed start
- Time-to-end countdown
- Program selection with per-program configurations (ECO, INTENSIVE, QUICK, GLASS, etc.)
- Temperature settings for optimal cleaning performance
- Extra options (hygiene rinse, extra dry, intensive zones)
- Salt level monitoring and alerts
- Rinse aid level monitoring and alerts
- Filter cleaning maintenance alerts
- Remote control enablement
- Network interface monitoring (WiFi quality, OTA updates, software version)
- Appliance working time and cycle counters
- Error detection and reporting with specific dishwasher error messages

**💨🌿 Air Purifiers**
- Air quality monitoring and control
- Fan speed control (1-9 levels)
- Work mode selection (Manual/Auto/Power Off)
- UI light control
- Safety lock
- Ionizer control

## ⚡ Features

### 📊 Sensors
- Appliance state and status
- Temperature readings (current, target, food probe, ambient)
- Program and phase information
- Connection quality and diagnostics
- Door and safety lock status
- Water levels and tank status
- Filter life and maintenance alerts
- Load weight monitoring (washing machines, washer-dryers)
- Humidity sensors (refrigerators, air conditioners)
- Air quality sensors (air purifiers)
- Cycle counters and working time statistics
- Drying cycle monitoring (washer-dryers)
- Dryer monitoring (tumble dryers: fluff filter status, dryness levels, load weight)
- Dishwasher monitoring (salt levels, rinse aid levels, filter status)

### 🎮 Controls
- Power on/off (with safety validation)
- Program selection
- Temperature settings
- Timer controls
- Light controls (ovens)
- Start/stop/reset commands
- Climate control (air conditioners):
  - Operating mode selection (AUTO, COOL, HEAT, DRY, FAN)
  - Fan speed control (AUTO, LOW, MEDIUM, HIGH, QUIET, TURBO)
  - Swing direction control (OFF, VERTICAL, HORIZONTAL, BOTH)
  - Target temperature and humidity settings
- Drying controls (washer-dryers):
  - Dry mode toggle
  - Drying time selection
  - Dryness level selection (CUPBOARD, EXTRA, IRON)
  - Wet mode control
- Dryer controls (tumble dryers):
  - Program selection (COTTON, SYNTHETICS, DELICATES, WOOL, etc.)
  - Drying time selection (0-300 minutes)
  - Dryness level selection (CUPBOARD, EXTRA, IRON, AIR_DRY)
  - Temperature settings (HIGH, MEDIUM, LOW, REFRESH)
  - Anti-crease protection
  - Delay start scheduling
- Dishwasher controls:
  - Program selection (ECO, INTENSIVE, QUICK, GLASS, etc.)
  - Temperature settings for optimal cleaning
  - Delay start scheduling
  - Extra options (hygiene rinse, extra dry, intensive zones)

### 🔴🟢 Binary Sensors
- Door status
- Connection state
- Alert conditions
- Dryer alerts (fluff filter maintenance)
- Dishwasher alerts (salt level, rinse aid level, filter cleaning)

### 🔍 Diagnostics
- Network interface information
- Software versions
- OTA update status
- Communication quality

## 🛠️ Troubleshooting

### 🔐 Authentication Issues
- **403 Forbidden**: Check your API credentials from the developer portal - they may have expired. Regenerate your access token and refresh token from [Electrolux Developer Portal](https://developer.electrolux.one/dashboard)
- **Invalid Credentials**: Double-check your API key, access token, and refresh token from the developer portal

### 🌐 Connection Issues
- Ensure appliances are connected to your Electrolux account
- Check internet connectivity of appliances
- Verify appliances are powered on and online

### 🎛️ Control Not Working
- Check if appliance has safety locks enabled (door open, child lock, etc.)
- Integration respects all appliance safety features
- Some controls may be disabled during active cycles

### 🔢 Model Shows as Numbers
- The integration displays the actual product code (e.g., "944188772") used by Electrolux internally
- This is the most specific identifier available through the API
- Marketing model names (e.g., "BSE788380M") are not exposed by the API

### 🛠️ Troubleshooting & Debugging
If you encounter issues with the Electrolux integration, providing debug logs is the fastest way to get help. Follow the steps below to capture and share the necessary information.

#### 1. Enable Debug Logging
Choose one of the two methods below:

##### Option A: The Easy Way (UI)
Best for capturing issues happening right now without a restart.

- Go to Settings > Devices & Services.
- Locate the Electrolux card.
- Click the three dots (⋮) and select Enable debug logging.
- Reproduce the issue (e.g., try to trigger a device command).
- Go back to the card and click Disable debug logging.
- The log file will automatically download to your computer.

##### Option B: The Persistent Way (YAML)
Required for troubleshooting startup issues or long-term monitoring.

Add this to your configuration.yaml and restart Home Assistant:

```YAML
logger:
  default: info
  logs:
    custom_components.electrolux: debug
```
#### 2. Viewing and Filtering Raw Logs
If you want to inspect the logs manually or copy specific lines:
- Navigate to Settings > System > Logs.
- Click the Load Full Logs button at the bottom of the page.
- Use the search/filter bar in the top right corner and type electrolux.
- This will hide all unrelated system noise, leaving only the Electrolux-specific entries.

#### 3. Sharing Logs on GitHub
##### How to Download
If you used Option B, you can download the entire log file by clicking Download logs at the bottom of the Settings > System > Logs page.

##### How to Copy/Paste (Recommended for snippets)
- To keep the GitHub issue clean, please wrap your logs in a code block.
- Highlight the filtered log text in your browser and copy it.
- In your GitHub issue description, paste it like this:

````
```text
PASTE YOUR LOGS HERE
```
````

[!CAUTION]
Privacy Check: The integration automatically redacts any sensitive information like api key and tokens but, just to be safe, before posting, scan the logs for sensitive data. Delete or mask any email addresses, passwords, unique API tokens, or GPS coordinates.

### 📄 JSON Diagnostics for Device Issues 
ATTENTION!!! You only need to send the diagnostics json once. It contains the same information every time you generate it. 
For device-specific issues or when certain features aren't working as expected, a JSON diagnostics file is **very helpful** for troubleshooting:

**How to get diagnostics:**
1. Go to **Settings → Devices & Services → Electrolux**
2. Click on your integration entry
3. Scroll down and click **"Download diagnostics"**

**What it contains:**
- Complete device capabilities schema (what your appliance supports)
- Current appliance state data (real-time values)
- API communication details and errors
- Model and firmware information

**🔒 Privacy & Security:** All sensitive information (API keys, tokens, personal data, emails, addresses, device identifiers, and other PII) is automatically redacted from diagnostics files. They are safe to share when reporting issues but check it yourselves before sending just to be sure

**When to provide diagnostics:**
- **Missing or incorrect sensors/controls**: If your appliance is missing expected sensors or controls, or if existing ones show wrong values or don't work properly
- Appliance not showing expected controls or sensors
- Commands not working or responding
- New appliance models with unknown features
- Integration setup issues
- Feature requests for specific appliance capabilities

Include this file when reporting issues - it helps identify device-specific problems quickly!

## 🧪 Testing Scripts

This repository includes comprehensive testing scripts to help you verify appliance compatibility and test API functionality before installing the integration. These scripts allow direct interaction with the Electrolux API to inspect your appliances and test commands.

📖 **[Testing Scripts Documentation](scripts/TESTING_SCRIPTS_README.md)** - Complete guide for using the testing tools

## 🤝 Contributing

Contributions are welcome! This integration is actively maintained and improved.

### 👨‍💻 Development Setup
1. Fork the repository
2. Clone your fork
3. Install development dependencies: `pip install -r requirements-dev.txt`
4. Test scripts are available in the root directory for API testing

### 🧪 Testing Your Appliances
Use the provided test scripts to verify API connectivity:
- `test_api_simple.py` - Basic appliance list test
- `test_appliance_details.py` - Detailed appliance information

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/TTLucian/ha-electrolux/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TTLucian/ha-electrolux/discussions)
- **Documentation**: [Electrolux Developer Portal](https://developer.electrolux.one/)
