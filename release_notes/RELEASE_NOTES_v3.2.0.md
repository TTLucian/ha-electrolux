# Release Notes - v3.2.0

## ❄️ **MAJOR ENHANCEMENT: Air Conditioner, Refrigerator & Washing Machine Control Suites**

This release introduces **comprehensive air conditioner support** with full climate control capabilities, **complete refrigerator control capabilities** with advanced monitoring and precise temperature management, and **extensive washing machine control capabilities** with advanced cycle management and auto-dosing systems, all based on actual Electrolux API specifications.

### ✅ **New Features**

#### 🏠 **Climate Platform Integration**
- **Full AC Support**: Complete climate entity implementation for Electrolux air conditioners
- **Automatic Detection**: Appliances with type "AC" are automatically configured as climate entities
- **Dual Protocol Support**: Seamless handling of both DAM (One Connected Platform) and legacy air conditioners

#### 🌡️ **Temperature Control**
- **Dual Temperature Scales**: Support for both Celsius (°C) and Fahrenheit (°F) temperature units
- **Target Temperature Setting**: Precise temperature control with device-specific ranges (16-30°C / 60-86°F)
- **Ambient Temperature Monitoring**: Real-time room temperature sensor readings
- **Step-Compliant Controls**: Automatic step enforcement (1° increments) for precise control

#### 🎛️ **Operating Modes**
- **AUTO Mode**: Intelligent automatic temperature regulation
- **COOL Mode**: Cooling operation for hot environments
- **HEAT Mode**: Heating operation for cold environments
- **DRY Mode**: Dehumidification mode for moisture control
- **FAN Mode**: Air circulation without temperature control

#### 🌬️ **Fan Speed Control**
- **Multiple Speed Options**: AUTO, LOW, MEDIUM, HIGH, QUIET, and TURBO fan speeds
- **Adaptive Fan Control**: Automatic fan speed adjustment based on operating mode
- **Quiet Operation**: Dedicated QUIET mode for silent operation
- **Turbo Boost**: High-power TURBO mode for rapid cooling/heating

#### 🔄 **Swing & Airflow Control**
- **Swing Modes**: OFF, VERTICAL, HORIZONTAL, and BOTH directional control
- **Air Distribution**: Precise control over airflow direction and spread
- **Comfort Optimization**: Adjustable swing patterns for optimal comfort

#### 💧 **Humidity Management**
- **Humidity Control**: Target humidity setting (30-70% range, 5% steps)
- **Ambient Humidity Monitoring**: Real-time humidity sensor readings
- **Dehumidification Integration**: Humidity control integrated with DRY mode

#### ⚡ **Power & Control**
- **Power State Management**: Full power on/off control through climate entity
- **Execute Commands**: Support for ON, OFF, START, and STOPRESET commands
- **State Synchronization**: Real-time synchronization with appliance status

#### � **Dual Control Interface**
- **Unified Climate Entity**: Primary interface for comprehensive AC control
- **Individual Control Entities**: Separate number, select, sensor, switch, and button entities for granular control  - **Select entities**: Operating mode, fan speed, swing direction
  - **Number entities**: Temperature and humidity settings
  - **Sensor entities**: Current temperature, humidity, and status readings
  - **Switch entities**: Power state control
  - **Button entities**: Execute commands (start/stop/reset)- **Flexible Usage**: Use climate entity for everyday control or individual entities for automation
- **Entity Management**: All entities can be disabled/enabled per user preference in Home Assistant settings

#### �🎨 **Dynamic Icon System**
- **Value-Based Icons**: Icons now change dynamically based on selected values
- **Capability-Driven Icons**: Support for icons defined in device capability values
- **Catalog Icon Maps**: Enhanced support for `entity_icons_value_map` in catalog entries
- **Visual Feedback**: Real-time icon updates reflecting current appliance state
- **Example Implementations**: Added dynamic icons for AC modes (❄️ COOL, 🔥 HEAT, 💨 FAN) and fan speeds (1️⃣ LOW, 2️⃣ MEDIUM, 3️⃣ HIGH)

### 🔧 **Technical Improvements**

#### **Climate Entity Architecture**
- **ElectroluxClimate Class**: Dedicated climate entity implementation inheriting from ElectroluxEntity
- **Capability Integration**: Full integration with catalog_air_conditioner.py capability definitions
- **Platform Registration**: Climate platform properly registered in PLATFORMS configuration
- **Remote Control Logic**: Removed unnecessary remote control checks for air conditioners (not applicable to AC devices)

#### **Protocol Compatibility**
- **DAM Command Format**: Commands wrapped in `{"commands": [{"airConditioner": {...}}]}` structure for DAM appliances
- **Legacy Command Format**: Direct property commands for legacy appliances
- **Automatic Protocol Detection**: PNC-based detection (IDs starting with "1:" for DAM appliances)

#### **Sensor Integration**
- **Temperature Sensors**: Ambient temperature monitoring with proper unit handling
- **Humidity Sensors**: Humidity readings integrated into climate entity
- **Status Sensors**: Appliance state, connectivity, and diagnostic information

### 📊 **Compatibility**

- **Home Assistant**: Compatible with Home Assistant 2024.1+
- **Appliance Types**: Works with all Electrolux air conditioners (DAM and legacy)
- **API Compatibility**: Full compatibility with Electrolux Group Developer SDK
- **Backward Compatibility**: All existing functionality preserved

### 🎯 **User Experience Improvements**

- **Unified Climate Control**: All air conditioner controls accessible through standard Home Assistant climate interface
- **Intuitive Operation**: Familiar climate controls with Electrolux-specific features
- **Real-time Feedback**: Immediate status updates and sensor readings
- **Mode Integration**: Seamless switching between cooling, heating, and fan-only modes

### 📝 **Migration Notes**

- **No Breaking Changes**: This is a non-breaking enhancement release
- **Automatic Detection**: Existing air conditioners will be automatically configured as climate entities
- **New Entity Creation**: Users will see new climate entities for their air conditioners
- **Configuration Required**: No additional configuration needed - entities appear automatically
- **Entity Management**: Individual control entities can be disabled/enabled per user preference in Home Assistant device settings

### ❄️ **Air Conditioner Features**

**Complete Climate Control:**
- Temperature setting and monitoring
- Operating mode selection (AUTO/COOL/HEAT/DRY/FAN)
- Fan speed control (AUTO/LOW/MEDIUM/HIGH/QUIET/TURBO)
- Swing mode control (OFF/VERTICAL/HORIZONTAL/BOTH)
- Humidity control and monitoring
- Power state management

**Smart Integration:**
- Real-time status updates via Server-Sent Events
- Safety validation and error handling
- Multi-language support
- Diagnostic capabilities

### 🧊 **MAJOR ENHANCEMENT: Comprehensive Refrigerator Control Suite**

This release also introduces **complete refrigerator control capabilities** with advanced monitoring, precise temperature management, and comprehensive appliance controls based on actual Electrolux API specifications.

#### 🧊 **Advanced Refrigerator Controls**
- **Multi-Compartment Temperature Control**: Precise temperature settings for fridge (-23°C to -13°C), freezer (1°C to 7°C), and extra cavity with 1°C increments
- **Fast Mode Controls**: Rapid cooling and freezing modes for all compartments
- **Appliance Mode Selection**: Normal, Demo, and Service modes with proper command formatting
- **Vacation Mode**: Energy-saving mode with automatic temperature adjustments
- **Child Lock System**: Internal and external child lock controls for safety

#### ❄️ **Ice Maker & Defrost System**
- **Ice Maker Control**: Full executeCommand support for ice maker operations
- **Defrost Temperature Monitoring**: Real-time defrost temperature tracking
- **Defrost Routine State**: Monitoring of defrost cycle status

#### 🔧 **Filter Management System**
- **Water Filter Reset**: Manual reset capability for water filter status
- **Air Filter Reset**: Manual reset capability for air filter status
- **Filter Status Monitoring**: Real-time filter status tracking

#### 🌡️ **Environmental Controls**
- **Humidity Sensor**: Ambient humidity monitoring
- **Reminder Time Settings**: Configurable reminder intervals
- **Cooling Valve Monitoring**: Real-time cooling valve status
- **Door Status Sensors**: Individual door sensors for all compartments

#### 🎛️ **Extra Cavity Features**
- **Temperature Cloning**: Copy temperature settings between compartments
- **Fan Control**: Dedicated fan control for extra cavity
- **Independent Operation**: Full autonomous control of extra cavity functions

#### 🐛 **Refrigerator Bug Fixes**
- **Temperature Range Accuracy**: Corrected temperature ranges based on actual API capabilities (-23°C to -13°C freezer, 1°C to 7°C fridge)
- **Command Structure Validation**: Enhanced command formatting for refrigerator-specific operations
- **Entity State Synchronization**: Improved real-time updates for all refrigerator sensors and controls

#### 🔧 **Refrigerator Technical Improvements**
- **Complete API Capability Mapping**: All refrigerator entities now match actual Electrolux API specifications
- **Advanced Entity Hierarchy**: Multi-level entity organization for complex appliance controls
- **Capability-Driven Entity Creation**: Dynamic entity generation based on device capabilities

### 🧺 **MAJOR ENHANCEMENT: Comprehensive Washing Machine Control Suite**

This release also introduces **complete washing machine control capabilities** with advanced cycle management, auto-dosing systems, and comprehensive monitoring based on actual Electrolux API specifications.

#### 🧺 **Advanced Washing Machine Controls**
- **Comprehensive State Management**: Full appliance state tracking (IDLE, RUNNING, PAUSED, END_OF_CYCLE, DELAYED_START, etc.)
- **Cycle Phase Monitoring**: Real-time cycle phase and sub-phase tracking (WASH, RINSE, SPIN, DRY, STEAM, etc.)
- **Door Control System**: Door status monitoring and lock control (LOCKING, ON, OFF, UNLOCKING)
- **Start Time Scheduling**: Delayed start functionality with 30-minute increments (up to 20 hours)
- **Time-to-End Countdown**: Real-time remaining cycle time display

#### 🔧 **Auto-Dosing System**
- **Dual Tank Configuration**: Separate detergent and softener tanks with independent controls
- **Standard Dose Settings**: Configurable dosing amounts (5-200ml range, 1ml steps)
- **Fine-Tune Controls**: Precise detergent and softener level adjustments
- **Tank Status Monitoring**: Real-time tank reserve levels and load tracking

#### 🎛️ **Program & Settings Control**
- **Program Selection**: Extensive program library with per-program configurations
- **Temperature Control**: Full temperature range (COLD, 20°C-90°C)
- **Spin Speed Selection**: Variable spin speeds (0-1600 RPM in 200 RPM increments)
- **Steam Level Control**: Four steam settings (OFF, MIN, MED, MAX)
- **Extra Rinse Options**: Additional rinse cycle control
- **End-of-Cycle Sound**: Audible completion notifications

#### 📊 **Advanced Monitoring**
- **Load Weight Sensing**: OptiSense load weight detection and results
- **Water Usage Tracking**: Real-time water consumption monitoring
- **Cycle Counters**: Total cycles and working time statistics
- **Maintenance Alerts**: Comprehensive alert system for 14+ different issues
- **Network Diagnostics**: WiFi quality, OTA update status, software version

#### 🚨 **Alert & Safety System**
- **Comprehensive Alerts**: Door checks, drain filters, inlet taps, detergent overdosing, power failures, water leaks, unbalanced loads, and more
- **Remote Control Management**: Remote access enablement and safety controls
- **Maintenance Tracking**: Appliance care and maintenance scheduling

#### 🔧 **Washing Machine Technical Improvements**
- **Complete API Capability Mapping**: All washing machine entities match actual Electrolux API specifications
- **Complex State Triggers**: Advanced command availability based on appliance state
- **Multi-Level User Selections**: Nested configuration system for program-specific settings
- **Maintenance System Integration**: Full integration with appliance care and maintenance framework

---

## 🐛 **Reporting Issues with Missing or Incorrect Sensors/Controls**

If you encounter any issues with missing sensors, incorrect controls, or malfunctioning entities on your Electrolux appliances, please help improve the integration by reporting them:

### How to Report Issues:
1. **Open a GitHub Issue**: Visit [GitHub Issues](https://github.com/TTLucian/ha-electrolux/issues) and create a new issue
2. **Provide Diagnostics**: Include a JSON diagnostics file to help identify the problem:
   - Go to **Settings → Devices & Services → Electrolux**
   - Click on your integration entry
   - Scroll down and click **"Download diagnostics"**
3. **Describe the Issue**: Clearly explain what's missing, wrong, or not working as expected

### What Diagnostics Contain:
- Complete device capabilities schema (what your appliance actually supports)
- Current appliance state data (real-time values)
- API communication details
- Model and firmware information

**🔒 Privacy & Security**: All sensitive information is automatically redacted from diagnostics files - they are safe to share.

This helps identify device-specific problems and ensures all appliance models are properly supported!

---

*For questions or support, please visit the [GitHub Issues](https://github.com/TTLucian/ha-electrolux/issues) page.*</content>
<parameter name="filePath">d:\Lucian\Documents\Github\ha-electrolux\RELEASE_NOTES_v3.2.00.md