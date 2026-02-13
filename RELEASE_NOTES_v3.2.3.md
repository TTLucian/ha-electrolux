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