# Logging Improvements Analysis

## Current Issues

1. **Token renewal using INFO instead of DEBUG** - Spams logs with [AUTH-DEBUG] messages
2. **Inconsistent categorization** - Some warnings should be errors, some info should be debug
3. **Missing context** - Some logs lack appliance_id, state info, or timing
4. **Not verbose enough for debugging** - Token renewal needs more breadcrumbs

## Categorization Rules

### ERROR
- Authentication failures that prevent operation
- Critical failures (can't persist tokens, API unreachable)
- Data integrity issues
- Unexpected exceptions

### WARNING  
- Recoverable issues (retry will be attempted)
- Deprecated/unexpected behavior
- Configuration issues
- Temporary failures
- Token refresh cooldown (user should know it's backing off)

### INFO
- Integration lifecycle (setup complete, reload, shutdown)
- Device state changes (online/offline, program change)
- Successful authentication/token refresh completion
- User-initiated actions (commands sent)

### DEBUG
- Token renewal detailed flow (proactive check, HTTP calls, validation)
- API request/response details
- Entity creation/registration
- SSE stream events
- Internal state transitions
- Time conversions, value mappings

## Implementation Plan

1. Change [AUTH-DEBUG] from INFO → DEBUG (it's for developers, not users)
2. Keep auth SUCCESS/FAILURE at INFO level
3. Add more DEBUG breadcrumbs in token flow
4. Add context (appliance_id, timestamps) to key logs
5. Ensure all exceptions use _LOGGER.exception() for full stack traces
