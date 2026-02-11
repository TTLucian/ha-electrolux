# Release Notes - v3.2.1

## 🌀 **MAJOR ENHANCEMENT: Washer-Dryer Appliance Support**

This release introduces **comprehensive washer-dryer support** with full integrated washing and drying control capabilities, providing users with complete control over their Electrolux washer-dryer appliances.

### ✅ **New Features**

#### 🏠 **Washer-Dryer Platform Integration**
- **Full WD Support**: Complete entity suite for Electrolux washer-dryer appliances
- **Automatic Detection**: Appliances with type "WD" are automatically configured with comprehensive controls
- **Integrated Wash+Dry Cycles**: Support for appliances that combine washing and drying in unified programs

#### 🌡️ **Advanced Drying Controls**
- **Dry Mode Toggle**: Switch to enable/disable drying functionality (`userSelections/EWX1493A_dryMode`)
- **Drying Time Control**: Precise drying duration setting (0-300 minutes, 10-minute steps)
- **Dryness Level Selection**: Choose target dryness: CUPBOARD, EXTRA, IRON, or UNDEFINED
- **Wet Mode Option**: Dedicated wet mode control for specialized washing cycles

#### 📊 **Enhanced Monitoring**
- **Dual Load Weight Sensors**: Separate monitoring for washing and drying load weights
- **Drying Load Weight**: Real-time weight monitoring during drying cycles (`dryingNominalLoadWeight`)
- **Washing Load Weight**: Real-time weight monitoring during washing cycles (`washingNominalLoadWeight`)

#### 🔧 **Maintenance & Alerts**
- **Fluff Drawer Alert**: Binary sensor for dryer maintenance notifications (`alerts/CLEAN_FLUFF_DRAWER`)
- **Enhanced Alert System**: All existing washing machine alerts plus dryer-specific maintenance alerts
- **Load Balancing**: Unbalanced laundry detection for both washing and drying cycles

#### 🎛️ **Complete Control Suite**
- **Program Selection**: Full program catalog with integrated wash+dry cycles
- **Temperature Control**: Precise temperature settings for both wash and dry phases
- **Spin Speed Control**: Adjustable spin speeds for washing cycles
- **Steam Options**: Steam treatment controls for enhanced cleaning and drying
- **Time Management**: Flexible timing controls for both washing and drying phases
- **Auto-Dosing**: Advanced detergent and softener auto-dosing systems

#### ⚙️ **Technical Implementation**
- **Dedicated Catalog**: New `CATALOG_WASHER_DRYER` with 60+ entity definitions
- **Type-Based Mapping**: Automatic routing of "WD" appliances to washer-dryer catalog
- **Backward Compatibility**: Existing washing machine ("WM") support unchanged
- **API Compliance**: Based on actual Electrolux API capabilities from production appliances

### 🔧 **Technical Details**

#### **Catalog Architecture**
```python
CATALOG_BY_TYPE = {
    "WM": CATALOG_WASHER,        # Washing Machine (unchanged)
    "WD": CATALOG_WASHER_DRYER,  # Washer-Dryer (new)
    # ... other appliance types
}
```

#### **New Entity Categories**
- **Dryer Controls**: Dry mode, drying time, humidity target
- **Load Sensors**: Dual weight monitoring for wash/dry cycles
- **Maintenance**: Fluff drawer and dryer-specific alerts
- **Cycle Management**: Integrated wash+dry program handling

### 📈 **User Experience Improvements**

#### **Before v3.2.1**
- Washer-dryer appliances showed only: `sensor.pracka_se_susickou_connection_state`
- No control capabilities available
- Limited to basic connectivity monitoring

#### **After v3.2.1**
- **60+ entities** available including:
  - Program selection and control
  - Drying time and dryness level settings
  - Load weight monitoring
  - Maintenance alerts
  - Full washing machine controls
  - Real-time cycle status

### 🧪 **Quality Assurance**
- **132 unit tests** passing
- **Zero regressions** in existing functionality
- **API compatibility** verified with production appliances
- **Code formatting** compliant with project standards

### 📋 **Migration Notes**
- **Automatic**: No user action required - washer-dryer appliances are automatically detected and configured
- **Backward Compatible**: Existing washing machine installations unaffected
- **No Breaking Changes**: All existing entities and functionality preserved

### 🐛 **Bug Fixes**
- Fixed washer-dryer appliances showing only connection state instead of full controls
- Resolved catalog mapping issue for "WD" appliance type
- Improved entity naming and categorization for better user experience

---

**Full appliance control for Electrolux washer-dryers is now available!** 🎉

*This release is based on actual Electrolux API capabilities extracted from model `914611500` washer-dryer appliance diagnostics.*