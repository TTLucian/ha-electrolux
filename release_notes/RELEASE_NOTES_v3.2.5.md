# Release Notes v3.2.5

## 🚀 Electrolux Integration: "API-First Validation" Update

### 🎯 Major Architectural Change: Optimistic Command Sending (TEMPORARY)

**Previous Behavior:** Integration blocked commands client-side if `remoteControl` property appeared disabled, even when the API might accept them.

**New Behavior:** Commands are sent **optimistically** directly to the Electrolux API without client-side remote control validation. The API is now the authoritative validator.

#### Why This Change?

Different appliances have different remote control states that only the API can accurately validate:
- **`ENABLED`** - Standard remote control (most appliances)
- **`NOT_SAFETY_RELEVANT_ENABLED`** - Ovens with safety acknowledgment (commands accepted)
- **`persistentRemoteControl: DISABLED`** - Legacy dryers (API rejects, not visible to integration)
- **`TEMPORARY_LOCKED`** - Requires physical button press on appliance

The integration cannot know all appliance-specific rules. The API has complete knowledge and returns clear error messages when commands are genuinely rejected.

### 🔧 Command Validation Changes

#### Removed Client-Side Remote Control Blocking

**Modified Files:**
- [`number.py`](custom_components/electrolux/number.py) - Number entities (temperature, duration, etc.)
- [`select.py`](custom_components/electrolux/select.py) - Select entities (programs, settings)
- [`button.py`](custom_components/electrolux/button.py) - Button entities (START, STOP, etc.)
- [`switch.py`](custom_components/electrolux/switch.py) - Switch entities (buzzer, anti-crease, etc.)
- [`text.py`](custom_components/electrolux/text.py) - Text entities (custom input)

**What Changed:**
- ✅ Removed all `is_remote_control_enabled()` checks before sending commands
- ✅ Removed direct `remoteControl` property validation
- ✅ Commands now sent directly to API for validation
- ✅ API provides authoritative rejection with detailed error messages

**Benefits:**
- 🎯 Works with appliances that have `NOT_SAFETY_RELEVANT_ENABLED` (ovens)
- 🎯 Proper handling of complex remote control states
- 🎯 Clear error messages directly from API
- 🎯 Matches official Electrolux app behavior

### 📊 Enhanced Error Logging

**Major Improvement:** All command failure log entries now include HTTP status codes and complete API JSON responses.

#### What's Logged Now

**Before:**
```
Command failed for targetTemperatureC: command validation error - <exception>
```

**After:**
```
Command failed for targetTemperatureC: HTTP 406 | API Response: {"error": "COMMAND_VALIDATION_ERROR", "message": "Command validation failed", "detail": "Remote control disabled"} | <exception>
```

#### Logged Information

All command failures now include:
- **HTTP Status Code**: `| HTTP 406`, `| HTTP 403`, `| HTTP 429`, etc.
- **API JSON Response**: Complete raw API error response including:
  - `error` - Error code from API
  - `message` - Error message from API
  - `detail` - Specific rejection reason from API

**Modified File:** [`util.py`](custom_components/electrolux/util.py) (lines 605-876)

**Benefits:**
- 🔍 Better debugging - see exactly what API returned
- 🔍 Clear rejection reasons (remote control, door open, probe not inserted, etc.)
- 🔍 HTTP status codes identify error category immediately
- 🔍 Complete API response helps diagnose edge cases

### 🧪 Testing Scripts Enhanced

#### Updated `script_test_commands.py`

Enhanced the command testing script to match integration behavior:

**New Features:**
- ✅ **Optimistic Sending**: Commands sent without client-side validation
- ✅ **Complete API Responses**: Shows full raw JSON from API (success and errors)
- ✅ **Clear Messaging**: Indicates commands sent "optimistically" for API validation
- ✅ **Improved Error Display**: Better extraction and formatting of API error details

**Example Output:**
```
📤 Sending command optimistically to appliance 944188772:
   Command: {"cavityLight": true}
   (Commands are sent directly to API - API will validate remote control status)

✅ Command executed successfully!
📨 Raw API Response:
{
  "commandId": "abc123",
  "status": "accepted"
}
```

**Error Example:**
```
❌ Command rejected by API!
📨 Raw API Response:
{
  "error": "COMMAND_VALIDATION_ERROR",
  "message": "Command validation failed",
  "detail": "Remote control disabled"
}

💡 Tip: API validates remote control status, appliance state, and command support.
```

#### Updated Documentation

**Modified Files:**
- [`scripts/TESTING_SCRIPTS_README.md`](scripts/TESTING_SCRIPTS_README.md)

**Documentation Updates:**
- 📖 Explains optimistic command sending approach
- 📖 Documents API validation of remote control states
- 📖 Enhanced troubleshooting section with HTTP error codes
- 📖 Updated example sessions to show new output format
- 📖 Added details about remote control validation types

### 🧪 Test Suite Updates

**Modified Test Files:**
- [`tests/test_select.py`](tests/test_select.py)
- [`tests/test_switch.py`](tests/test_switch.py)
- [`tests/test_text.py`](tests/test_text.py)

**Test Changes:**
- ✅ Updated remote control tests to verify optimistic sending
- ✅ Tests now verify commands reach API (not blocked client-side)
- ✅ Mocked `execute_appliance_command` to verify API calls
- ✅ All 227 tests passing

**Previous Test Behavior:**
```python
# Expected HomeAssistantError when remote control disabled
with pytest.raises(HomeAssistantError, match="Remote control is disabled"):
    await entity.async_select_option("Option 1")
```

**New Test Behavior:**
```python
# Commands sent optimistically - API validates
entity.api.execute_appliance_command = AsyncMock(return_value=None)
await entity.async_select_option("Option 1")
# Verify command was sent to API (not blocked client-side)
entity.api.execute_appliance_command.assert_called_once()
```

### 🔄 API Error Handling (Already in Place)

The existing error handling in [`util.py`](custom_components/electrolux/util.py) already provides comprehensive user-friendly error messages:

**Error Code Mapping:**
- `REMOTE_CONTROL_DISABLED` → "Remote control is disabled for this appliance. Please enable it on the appliance's control panel."
- `COMMAND_VALIDATION_ERROR` → "Command not accepted by appliance. Check that the appliance supports this operation."
- `APPLIANCE_OFFLINE` → "Appliance is disconnected or not available. Check the appliance's network connection."
- `RATE_LIMIT_EXCEEDED` → "Too many commands sent. Please wait a moment and try again."

**HTTP Status Code Mapping:**
- `403` → Remote control disabled
- `406` → Command validation error (with detail parsing)
- `429` → Rate limit exceeded
- `503` → Appliance offline

**Smart Error Detail Parsing:**
- Detects "remote control" in error details and shows appropriate message
- Parses program restrictions, door open, probe not inserted, child lock, etc.
- Provides specific, actionable error messages to users

### 📦 What You Get

**User Benefits:**
- ✅ Commands work on ovens with `NOT_SAFETY_RELEVANT_ENABLED`
- ✅ Better error messages when API rejects commands
- ✅ Integration behavior matches official Electrolux app
- ✅ No false positives blocking valid commands

**Developer Benefits:**
- ✅ Enhanced logging for debugging command failures
- ✅ HTTP status codes and API responses in logs
- ✅ Testing scripts match integration behavior
- ✅ Clear documentation of optimistic sending approach

### 🛠️ Technical Implementation

#### Command Flow (New)

1. **User Action** → HA calls entity method (e.g., `async_select_option`)
2. **Connectivity Check** → Verify appliance is online (kept)
3. **Rate Limiting** → Prevent command spam (kept)
4. **State-Based Validation** → START only when READY_TO_START (kept)
5. **~~Remote Control Check~~** → **REMOVED** (was blocking valid commands)
6. **Send to API** → Command sent optimistically via `execute_appliance_command`
7. **API Validation** → API validates remote control, state, command support
8. **Error Handling** → Map API errors to user-friendly messages

#### Validation Layers

**Client-Side (Integration):**
- ✅ Appliance connectivity
- ✅ Rate limiting
- ✅ Appliance state requirements (START when READY_TO_START)
- ❌ Remote control status (removed - API handles this)

**Server-Side (API):**
- ✅ Remote control status (all variants)
- ✅ Command support validation
- ✅ Appliance state compatibility
- ✅ Program-specific restrictions
- ✅ Physical state (door, probe, child lock)

### 📋 Migration Notes

**For Users:**
- No action required - update will automatically enable optimistic sending
- You may see different error messages when commands are rejected (more accurate)
- Commands that were previously blocked may now work (if API accepts them)

**For Developers:**
- Review release notes for architectural understanding
- Check logs for enhanced HTTP status and API response information
- Testing scripts now match integration behavior

### 🐛 Bug Fixes

None - this is an architectural improvement release.

### ⚠️ Known Issues

None - all tests passing (227/227)

---

## 📊 Test Results

✅ **227 tests passing**  
✅ **No errors or warnings**  
✅ **Code formatted with Black**  
✅ **Type checking clean**

### Test Coverage

- Entity initialization ✅
- Token management ✅
- Coordinator functionality ✅
- Command sending (updated) ✅
- Error handling ✅
- All entity types (number, select, button, switch, text) ✅

---

## 🔍 For More Information

**Related Files:**
- Command sending: See `number.py`, `select.py`, `button.py`, `switch.py`, `text.py`
- Error handling: See `util.py` lines 469-876
- Testing scripts: See `scripts/script_test_commands.py`
- Documentation: See `scripts/TESTING_SCRIPTS_README.md`

**Testing:**
- Run `python scripts/script_test_commands.py` to test commands with your appliances
- Monitor Home Assistant logs for enhanced error information
- Check API responses in logs when commands are rejected

---

**Version:** 3.2.5  
**Release Date:** February 17, 2026  
**Breaking Changes:** None  
**Migration Required:** No
