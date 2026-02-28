# 🏠 Home Assistant Electrolux Integration
<p align="center">
  <img src="https://img.shields.io/github/v/release/TTLucian/ha-electrolux?style=for-the-badge" />
  <img src="https://img.shields.io/github/license/TTLucian/ha-electrolux?style=for-the-badge" />
  <img src="https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge" />
  <img src="https://img.shields.io/github/actions/workflow/status/TTLucian/ha-electrolux/ci.yml?style=for-the-badge" />
  <a href="https://buymeacoffee.com/ttlucian"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Donate-yellow?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee" /></a>
</p>

# 📖 Description

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

## 🔌 Supported Devices

**All Electrolux Group appliances connected via the official app should work with this integration.** Every connected appliance will have entities created dynamically from whatever the API reports — at minimum including connectivity state, software version, and network interface.

Full catalog support means the integration has been tested against real diagnostic data for that model — providing correct `device_class`, units, icons, and entity categories for all available entities. Without a catalog entry, entities are still created for everything the API reports but appear as generic sensors with no device class, unit, icon, or friendly name.

> 📎 **Help improve support for your appliance** — download your diagnostics from **Settings → Devices & Services → Electrolux → three-dot menu → Download diagnostics** and [open a GitHub issue](https://github.com/TTLucian/ha-electrolux/issues) with the file attached.

### ✅ Fully Catalog-Supported Models (verified from diagnostic samples)

The table below lists all appliance types and the known-tested diagnostic samples that have shaped the catalog. All appliance types in the **Full** column receive entity enrichment (device class, unit, icon, entity category). Types marked **Partial** have a catalog but may be missing entries for some models — submit your diagnostics to help close the gaps. **Stub** means the type code is registered but the catalog has no entries yet (requires user diagnostic samples to build from).

| Type | Appliance | Status | Known-Tested Samples / Models |
|------|-----------|--------|-------------------------------|
| `OV` | Oven | Full | Based on model `OV-944188772` |
| `SO` | Steam Oven | Full | Based on model `SO-944035035` |
| `RF` | Refrigerator | Partial | No diagnostic samples received yet — [submit yours](https://github.com/TTLucian/ha-electrolux/issues) |
| `CR` | Combined Refrigerator | Full ✨ *new* | Based on model `CR-925060324` |
| `WM` | Washing Machine | Full | Based on models `WM-EW7F3816DB`, `WM-914501128`, `WM-914915144` |
| `WD` | Washer-Dryer | Full | Based on models `WD-914611000`, `WD-914611500` |
| `TD` | Tumble Dryer | Full | Based on models `TD-916099949`, `TD-916098401`, `TD-916098618`, `TD-916099548` |
| `AC` | Air Conditioner | Full | Based on model `AC-910280820` |
| `DW` | Dishwasher | Full | Based on models `DW-911434654`, `DW-911434834` |
| `A9` / `Muju` | Air Purifier | Full | A9 series; UltimateHome 500 (EP53) |
| `MW` | Microwave | Stub | No diagnostic samples received yet — [submit yours](https://github.com/TTLucian/ha-electrolux/issues) |
| Newer `DAM` Apliances | Partial support | No diagnostic samples received yet — [submit yours](https://github.com/TTLucian/ha-electrolux/issues) |

> Appliance types not listed above still have all their entities created dynamically from whatever the API reports in the device capabilities — no entities are suppressed. However, without a catalog entry they appear as generic sensors and controls with no device class, unit, icon, or friendly name. The base catalog (connectivity state, software version, network interface) applies to all appliance types regardless.

### � Diagnostics Wanted

The following appliance types need real diagnostic JSON samples before full support can be built. If you own one of these devices, please download your diagnostics from **Settings → Devices & Services → Electrolux → three-dot menu → Download diagnostics** and [open a GitHub issue](https://github.com/TTLucian/ha-electrolux/issues) with the file attached.

| Appliance | Issue title | Why it's needed |
|-----------|-------------|----------------|
| 🤖 **Robot Vacuum** (Pure i8, Pure i9, Gordias, Cybele, or any RVC) | `RVC diagnostics — [your model]` | Appliance type code unknown; no capability keys; room-cleaning support blocked entirely |
| 🍽️ **Microwave Oven** (any `MW` model) | `MW diagnostics — [your model]` | Type code registered but catalog is empty — all entities appear as generic sensors |
| ⚡ **DAM Appliance** (appliance ID starts with `1:` or type starts with `DAM_`) | `DAM diagnostics — [your model]` | DAM connectivity fixed in v3.4.1 but catalog enrichment requires per-type samples |

### �🔍 Finding Your Model Number

The model number (PNC — Product Number Code) is the key used to identify your appliance in the catalog. It appears in the HA device info panel as **`Model: {type}-{PNC}_{suffix}`** (e.g. ` Model: TD-916099949_00`).

**How to find it:**
1. Go to **Settings → Devices & Services → Electrolux**
2. Click on your appliance device
3. The **Model** field in the device info card shows `Model: {type}-{PNC}_{suffix}` — the number before the `_` is your PNC (e.g. `916099949` from `Model: TD-916099949_00`)

Alternatively, the PNC is visible on the appliance's rating plate (usually inside the door or on the back) and in the official Electrolux app under appliance details.

If your model number appears in the table above, your appliance has been verified against real diagnostic data and will have full entity enrichment. If it does not appear, basic entities will still be created — [submit your diagnostics](https://github.com/TTLucian/ha-electrolux/issues) to add full support.

---

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

**Good news!** This integration is now available directly in the HACS default repository.

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Search for "Electrolux"
4. Click **Install**
5. Restart Home Assistant

**Note:** No custom repository URL needed anymore!

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

## ⚠️ Important: Entity Management

**The integration creates ALL entities reported by the Electrolux API, even if they are not useful or not implemented in your appliance's firmware.**

### What This Means For You

After setup, you may see many entities that:
- Have no value or show "unknown" status
- Are not actually implemented in your appliance's firmware
- Are for diagnostic or maintenance purposes that you don't need

**This is intentional behavior.** The integration gives you full visibility into everything the API reports, allowing you to decide what's useful for your needs.

### � Automatic Security Protection

**The integration automatically blocks dangerous entities that could damage your appliances.**

Certain API-reported entities control low-level system functions that can permanently damage appliance functionality. These are **automatically blocked** and will never be created:

- **Network Interface Commands**: Authorization commands that can unpair your appliance from your account
- **Start Up Commands**: Commands like UNINSTALL that can factory reset the network module

**Examples of blocked entities:**
- `button.oven_network_interface_start_up_command_uninstall`
- `button.[appliance]_network_interface_command_appliance_authorize`
- `button.[appliance]_network_interface_command_user_authorize`

**You won't see these entities** - they are filtered at the code level for your protection. This prevents accidental activation through dashboards, automations, or voice assistants that could:
- Factory reset your appliance
- Break network connectivity permanently
- Unpair the appliance from your account
- Require professional service to restore functionality

The security blacklist is maintained in the codebase and updated as new dangerous entities are discovered.

### Recommended Actions for Other Entities

While dangerous entities are automatically blocked, you may still want to clean up other unnecessary entities:

1. **After initial setup**, review all entities for your appliances
2. **Disable any entities** that:
   - Show "unknown" or empty values consistently
   - Are not relevant to your daily use (diagnostic sensors you don't need)
3. **Keep only the entities you actually need** for monitoring and control

**How to disable entities:**
1. Go to **Settings** → **Devices & Services** → **Entities**
2. Search for your appliance name
3. Click on the entity you want to disable
4. Click the **Disable** button
5. Confirm the action

**Note:** Disabled entities remain in Home Assistant's database but won't be updated or visible in your dashboards. You can re-enable them later if needed.

## 🔌 Supported Appliances

This integration works with Electrolux and Electrolux-owned brands (AEG, Frigidaire, +home) across multiple regions:

- **Europe/Middle East/Africa** (EMEA): My Electrolux Care, My AEG Care, Electrolux Kitchen, AEG Kitchen
- **Asia Pacific** (APAC): Electrolux Life
- **Latin America** (LATAM): Electrolux Home+
- **North America** (NA): Electrolux Oven, Frigidaire 2.0

### 🏷️ Device Types

**🍳 Ovens**
- AEG AssistedCooking series
- Real-time temperature monitoring
- Program control and status
- Safety lock validation
- Multiple cooking programs (Bake, Broil, Convection)
- Food probe monitoring and control
- Delayed start and timers

**🍲 Steam Ovens** ✨ NEW v3.3.4
- AEG Steam Ovens
- Electrolux Steam Ovens
- **Full dedicated implementation with 40+ entities**
- All standard oven features plus steam-specific controls:
  - Water tank level monitoring
  - Descaling reminders and maintenance alerts
  - Steam programs (FULL_STEAM, STEAM_HIGH, STEAMIFY, MOIST_FAN_BAKING)
  - Water hardness configuration
  - Drip tray detection
- Enhanced UI configuration:
  - Display brightness control (5 levels)
  - Sound volume and key tone settings
  - Language selection (26 languages)
  - Clock display format
- Nested capability structure with upperOven controls
- Real-time temperature and probe monitoring
- Program-specific constraints and safety validation

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

**🌊 Microwaves** - ⚠️ Basic Support (In Preparation)
- Appliance state monitoring
- Microwave power sensor (Watts)
- Time-to-end countdown
- **Status**: Foundation infrastructure added in v3.2.7
- **Full support pending**: Requires diagnostic JSON files from users with microwave appliances
- **Coming soon**: Power level controls, cooking modes, timer controls, quick start, defrost settings, child lock

> **Help me improve microwave support!** If you have an Electrolux microwave, please submit diagnostic files via Settings → Devices & Services → Electrolux → [Your Microwave] → Download Diagnostics.

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
- Microwave monitoring (power output, time-to-end)

### 🎮 Controls
- **Manual Sync Button** (⚠️ **Use Sparingly**):
  - Forces a complete refresh of all appliance data
  - Disconnects and reconnects the real-time data stream
  - Updates all appliances simultaneously
  - **Rate limited**: 60-second cooldown between syncs
  - **⚠️ Warning**: This causes significant API load. Only use when:
    - Data appears stale or stuck
    - After appliance power cycle or network interruption
    - As a last resort troubleshooting step
  - **Normal operation**: Real-time updates via SSE work automatically - manual sync is rarely needed
  - Each appliance has its own manual sync button, but triggering any button refreshes ALL appliances
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

### � Stale or Stuck Data
If sensor values appear outdated or frozen:

**First, check the basics:**
- Verify appliance is powered on and connected to Wi-Fi
- Check if appliance shows as "connected" in the official Electrolux app
- Wait 5-10 minutes - data updates automatically via real-time SSE stream

**If data is still stuck:**
- Use the **Manual Sync** button (available on each appliance)
- **⚠️ Important**: This button is rate-limited (60 seconds cooldown) and causes heavy API load
- **Only use when necessary** - normal operation doesn't require manual sync
- The button refreshes ALL appliances, not just the one triggered

**When Manual Sync is appropriate:**
- After appliance power cycle or firmware update
- After router reboot or network interruption
- Data hasn't updated for 30+ minutes despite appliance being online
- As a troubleshooting step before reporting an issue

**Manual Sync is NOT needed for:**
- Normal operation - real-time updates work automatically
- Immediate feedback after commands - state updates happen within seconds via SSE
- Regular data refreshes - integration polls every 6 hours automatically

### �🔢 Model Shows as Numbers
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
- Click the Electrolux card.
- Click the three dots (⋮) in the upper right of the page and select Enable debug logging.
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
- Click the 3 dots in the upper right corner, click Show Raw Logs button.
- Scroll the logs upwards a few times so that more log entries get loaded
- Use the search/filter bar at the top and type electrolux.
- This will hide all unrelated system noise, leaving only the Electrolux-specific entries.
- Select, copy and paste in your issue editor the full text that is showing.

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

## 🔧 Troubleshooting

### Missing Entities / "No Entities After Reinstall"

**Symptoms:**
- Appliance shows only 7 basic entities (network command buttons, connectivity sensor, manual sync button)
- Missing functional entities (applianceState, doorState, program selects, temperature controls, etc.)
- Previously working appliance suddenly has minimal entities
- Reinstalling integration doesn't help

**Root Cause:**
This occurs when the integration creates a "minimal appliance" due to API communication issues during setup:

1. **When It Happens:** During Home Assistant startup/restart, integration reload, or token refresh, if the Electrolux API times out or token refresh fails
2. **Safety Mechanism:** Instead of losing the appliance entirely, the integration creates a minimal entry with basic catalog entities
3. **The Problem:** Regular update cycles (every 6 hours) only refresh existing entity *state* - they don't check for or create missing entities
4. **Result:** The appliance stays "minimal" with only 7 entities until manual intervention

**Why Reinstalling Doesn't Help:**
Reinstalling the integration doesn't fix the issue because:
- The problem is in the integration's recovery logic (fixed in v3.3.1+), not your configuration
- If you reinstall during an API timeout or token issue, you'll get another minimal appliance
- Entity creation happens only once during setup; reinstalling under the same conditions recreates the same problem

**Solution - Upgrade to v3.3.1+ (Recommended):**

Versions 3.3.1 and later include automatic recovery for this issue:

1. **Upgrade** to the latest version via HACS
2. **Restart Home Assistant**
3. **Press the "Manual Sync" button** on the affected appliance device
4. The integration will automatically:
   - Detect the minimal appliance condition (no capabilities data)
   - Trigger a full integration reload
   - Recreate all missing entities properly

**Manual Workaround (for v3.3.0 and earlier):**

If you cannot upgrade immediately:

1. **Wait for API Stability:** Ensure your network connection is stable and working
2. **Remove Integration:**
   - Go to Settings → Devices & Services → Electrolux
   - Click the three dots → "Delete"
3. **Restart Home Assistant** (ensures clean state)
4. **Re-add Integration:**
   - Add the Electrolux integration again
   - Enter your API credentials
   - Integration will fetch full appliance data and create all entities

**Prevention:**
- Keep your integration updated to the latest version
- Ensure stable network connection during Home Assistant restarts
- The fix in v3.3.1+ includes:
  - Token refresh race condition fix (prevents entity recreation during problematic moments)
  - Automatic minimal appliance detection and recovery via Manual Sync button

**How to Verify You're Affected:**

For dishwashers, you should have 20+ entities including:
- `sensor.{name}_appliance_state` (RUNNING/IDLE/PAUSED)
- `binary_sensor.{name}_door_state` (OPEN/CLOSED)
- `sensor.{name}_cycle_phase` (MAINWASH/RINSE/DRYING)
- `sensor.{name}_time_to_end`
- `select.{name}_program` (ECO/INTENSIVE/QUICK)
- `switch.{name}_extra_power_option`
- `number.{name}_rinse_aid_level`
- And more...

If you only see network command buttons and a connectivity sensor, you have a minimal appliance.

**Still Having Issues?**

If the above solutions don't resolve your issue:
1. [Download diagnostics](#-json-diagnostics-for-device-issues) from your integration
2. Check the diagnostic JSON for `"capabilities": {}` or missing capabilities data
3. Report the issue on [GitHub Issues](https://github.com/TTLucian/ha-electrolux/issues) with your diagnostic file

## 🧪 Testing Scripts

This repository includes comprehensive testing scripts to help you verify appliance compatibility and test API functionality before installing the integration. These scripts allow direct interaction with the Electrolux API to inspect your appliances and test commands.

📖 **[Testing Scripts Documentation](scripts/TESTING_SCRIPTS_README.md)** - Complete guide for using the testing tools

## 🤝 Contributing

Contributions are welcome! This integration is actively maintained and improved.

## 🤝 Special **Thank You!** to all users who helped fund this project!!!

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
