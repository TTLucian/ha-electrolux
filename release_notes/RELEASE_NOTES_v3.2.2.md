# Release Notes - v3.2.2

## 🌀 **Dishwasher Appliance Support**

This release introduces **comprehensive dishwasher support** with full control over Electrolux dishwasher appliances, providing users with complete management of their dishwashing cycles and monitoring capabilities.

### ✅ **New Features**

#### 🏠 **Dishwasher Platform Integration**
- **Full DW Support**: Complete entity suite for Electrolux dishwasher appliances
- **Automatic Detection**: Appliances with type "DW" are automatically configured with comprehensive controls
- **Program-Based Cycles**: Support for various dishwashing programs with customizable options

#### 🌡️ **Advanced Dishwashing Controls**
- **Program Selection**: Choose from multiple dishwashing programs (ECO, INTENSIVE, QUICK, etc.)
- **Temperature Control**: Adjustable water temperature settings for optimal cleaning
- **Delay Start**: Schedule dishwashing cycles to start at a later time
- **Extra Options**: Additional features like hygiene rinse, extra dry, and intensive zones

#### 📊 **Enhanced Monitoring**
- **Cycle Progress**: Real-time monitoring of dishwashing cycle progress
- **Time Remaining**: Display of remaining time for current cycle
- **Status Indicators**: Current operation status (running, finished, paused, etc.)
- **Error Detection**: Automatic detection and reporting of dishwasher errors

#### 🔧 **Maintenance & Alerts**
- **Salt Level Monitoring**: Binary sensor for dishwasher salt level alerts
- **Rinse Aid Monitoring**: Binary sensor for rinse aid level alerts
- **Filter Cleaning Alerts**: Notifications for filter maintenance requirements
- **Door Status**: Monitoring of dishwasher door open/closed state

#### 🎛️ **Complete Control Suite**
- **Start/Stop Control**: Ability to start, pause, and stop dishwashing cycles
- **Program Management**: Full program catalog with dishwasher-specific options
- **Timer Controls**: Flexible timing and delay options
- **Power Management**: Energy-efficient operation controls

#### ⚙️ **Technical Implementation**
- **Dedicated Catalog**: New `CATALOG_DISHWASHER` with comprehensive entity definitions
- **Type-Based Mapping**: Automatic routing of "DW" appliances to dishwasher catalog
- **API Compliance**: Based on actual Electrolux API capabilities for dishwasher appliances

## 📝 **Log and Messaging Enhancements**

This release significantly improves logging and user messaging throughout the integration, providing better diagnostics and user experience.

### ✅ **Enhanced Error Messages**
- **Specific Validation Messages**: Detailed error messages for appliance state validation failures
- **User-Friendly Descriptions**: Clear, actionable error messages instead of generic "command not accepted"
- **Context-Aware Messaging**: Error messages tailored to specific appliance types and operations

### ✅ **Improved Logging**
- **Structured Logging**: Consistent log formatting across all components
- **Debug Information**: Enhanced debug logging for troubleshooting appliance issues
- **Performance Monitoring**: Logging of API response times and error patterns
- **Connection Status**: Detailed logging of appliance connectivity and communication status

### ✅ **Error Handling Improvements**
- **Graceful Degradation**: Better handling of partial failures and network issues
- **Retry Logic**: Intelligent retry mechanisms for transient failures
- **Fallback Messages**: Appropriate fallback messages when specific error details are unavailable

## 🔄 **Catalog Consolidation**

This release consolidates and optimizes the appliance catalog system for better maintainability and performance.

### ✅ **Catalog Architecture Improvements**
- **Unified Structure**: Consolidated catalog definitions with consistent patterns
- **Reduced Duplication**: Eliminated duplicate entity definitions across catalogs
- **Modular Design**: Better organization of catalog components by appliance type

### ✅ **Performance Optimizations**
- **Faster Loading**: Optimized catalog loading and entity creation
- **Memory Efficiency**: Reduced memory usage through shared catalog components
- **Lookup Optimization**: Improved entity lookup performance

### ✅ **Maintainability Enhancements**
- **Clear Documentation**: Better documented catalog structure and entity mappings
- **Consistent Naming**: Standardized naming conventions across all catalogs
- **Version Control**: Improved tracking of catalog changes and updates

### 🔧 **Technical Details**

#### **Catalog Architecture**
```python
CATALOG_BY_TYPE = {
    "WM": CATALOG_WASHER,        # Washing Machine
    "WD": CATALOG_WASHER_DRYER,  # Washer-Dryer
    "DW": CATALOG_DISHWASHER,    # Dishwasher (new)
    "OV": CATALOG_OVEN,          # Oven
    "FR": CATALOG_FRIDGE,        # Refrigerator
    "DW": CATALOG_DISHWASHER,    # Dishwasher
    "AC": CATALOG_AIR_CON,       # Air Conditioner
    "HO": CATALOG_HOOD,          # Range Hood
    "PT": CATALOG_PURIFIER,      # Air Purifier
}
```

#### **Error Message Examples**
- **Remote Control Disabled**: "Remote control is currently disabled on this appliance"
- **Program Restrictions**: "This setting is not supported by the currently selected program"
- **Food Probe Required**: "Food probe must be inserted to use this temperature control"
- **Door Open**: "Cannot start cycle while appliance door is open"
- **Appliance Busy**: "Appliance is currently running a cycle"

#### **Logging Improvements**
- **Connection Events**: Detailed logging of connection establishment and failures
- **API Interactions**: Comprehensive logging of API requests and responses
- **Error Recovery**: Logging of automatic error recovery attempts
- **Performance Metrics**: Response time tracking for API operations

## 🐛 **Bug Fixes**

- Fixed connectivity detection issues in test environments
- Resolved async mocking problems in coordinator tests
- Improved error handling for malformed API responses
- Fixed catalog loading performance issues

## 📚 **Documentation Updates**

- Updated appliance type mappings documentation
- Added dishwasher integration guide
- Enhanced troubleshooting section with new error messages
- Improved catalog structure documentation

---

**Full Changelog**: [Compare v3.2.1...v3.2.2](https://github.com/lucian303/ha-electrolux/compare/v3.2.1...v3.2.2)

**Installation**: Update through HACS or manual installation following the [README](README.md) instructions.