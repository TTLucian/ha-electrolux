# Release Notes - v3.2.3

## 🔄 **Token Management & Reliability Enhancements**

This release introduces comprehensive token management improvements, increased timeouts for better reliability, and enhanced user experience through improved configuration interfaces and error handling.

### ✅ **Authentication & Token Improvements**

#### 🔑 **Automatic Token Refresh & Persistence**
- **Persistent Token Storage**: Access and refresh tokens are now automatically saved to the config entry when refreshed
- **Expiration Tracking**: Token expiration timestamps are calculated and stored for proactive renewal
- **Enhanced Token Manager**: Custom token manager with expiration-aware refresh logic
- **Seamless Re-authentication**: Users no longer need manual intervention - tokens refresh automatically in the background
- **Token Validity Constants**: Added standardized 12-hour access token validity period

#### 🛡️ **Enhanced Security & Reliability**
- **Improved Error Handling**: Better detection and handling of authentication failures
- **Config Entry Updates**: Automatic updates to stored credentials when tokens are refreshed
- **Background Token Updates**: Token refresh happens transparently without disrupting appliance control

### ⚡ **Performance & Stability Improvements**

#### ⏱️ **Increased Timeouts for Better Reliability**
- **Appliance State Queries**: Increased timeout from 8s to 12s for initial appliance state retrieval during setup
- **Capability Queries**: Extended timeout from 8s to 12s for capability information retrieval during setup
- **Background Updates**: Extended timeout from 10s to 15s for real-time appliance state updates during normal operation
- **Network Resilience**: Better handling of variable network conditions and API response times

#### 🎯 **Simplified Entity Availability**
- **Streamlined Logic**: Simplified entity availability checks by removing redundant connection status checks
- **Consistent Behavior**: More predictable availability reporting across all appliance types

#### 🔧 **Technical Enhancements**
- **Josepy Compatibility Fix**: Resolved Python library compatibility issues for smoother operation
- **Enhanced Logging**: Better diagnostic information for offline appliance detection
- **Improved Error Diagnostics**: More detailed logging and error reporting for troubleshooting

### 🎨 **User Experience Enhancements**

#### 📝 **Improved Configuration Interface**
- **Clearer Instructions**: Updated configuration descriptions with step-by-step token generation guidance
- **Better Security Messaging**: Enhanced warnings about token security and regeneration requirements
- **Simplified Field Labels**: Removed confusing "(restart required)" labels from configuration fields
- **Pre-populated Re-auth Forms**: Re-authentication forms now show current values for easier updates

#### 🔧 **Configuration Flow Improvements**
- **Enhanced Options Flow**: Better validation and error handling in configuration options
- **User-Friendly Messages**: More actionable error messages and guidance

### 📊 **Technical Details**

#### 🔧 **Configuration Changes**
- Added `token_expires_at` field to config entry data for expiration tracking
- Introduced `ACCESS_TOKEN_VALIDITY_SECONDS` constant (43200 seconds = 12 hours)
- Updated timeout constants for improved performance:
  - `APPLIANCE_STATE_TIMEOUT`: 8.0s → 12.0s (initial appliance state retrieval)
  - `APPLIANCE_CAPABILITY_TIMEOUT`: 8.0s → 12.0s (capability information retrieval)
  - `UPDATE_TIMEOUT`: 10.0s → 15.0s (real-time background updates)

#### 🔄 **API Integration Enhancements**
- Enhanced token refresh callback system with expiration information
- Improved error handling for authentication failures
- Better integration with Home Assistant's config entry system
- Automatic token persistence on refresh

#### 🏗️ **Architecture Improvements**
- More robust coordinator initialization with token refresh setup
- Enhanced entity availability logic for consistent behavior
- Improved async operation handling and error recovery
- Better test coverage and mocking for reliable testing

#### 🧪 **Testing Improvements**
- Enhanced test fixtures and mocking for better test reliability
- Improved test coverage for token management functionality
- More robust async test handling

## 🔒 **Security Notes**

- **Token Security**: All tokens are stored securely in Home Assistant's encrypted config storage
- **Automatic Rotation**: Old tokens are automatically replaced with fresh ones during refresh
- **No Manual Intervention**: Users are guided through re-authentication only when absolutely necessary
- **Secure Token Generation**: Clear guidance on generating fresh tokens from the official portal

## 🐛 **Bug Fixes & Improvements**

- **Entity Availability**: Fixed inconsistent availability reporting by simplifying logic
- **Timeout Issues**: Resolved timeout-related failures in slower network conditions
- **Token Persistence**: Fixed issues where refreshed tokens weren't properly saved
- **Configuration Flow**: Improved re-authentication flow with pre-populated values
- **Library Compatibility**: Fixed josepy compatibility issues for smoother operation

## 📈 **Compatibility**

- **Home Assistant**: Compatible with Home Assistant 2024.10.0+
- **Python**: Requires Python 3.12+
- **API**: Uses Electrolux Group Developer SDK >=0.2.0
- **Dependencies**: Improved dependency management and compatibility

---

**Upgrade Notes**: This release includes automatic improvements that require no user action. Existing installations will benefit from enhanced reliability, automatic token management, and improved performance immediately after update. The increased timeouts provide better stability in various network conditions.</content>
<parameter name="filePath">d:\Lucian\Documents\Github\ha-electrolux\RELEASE_NOTES_v3.2.3.md



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
**Installation**: Update through HACS or manual installation following the [README](README.md) instructions.