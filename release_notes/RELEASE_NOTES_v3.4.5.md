# Release Notes v3.4.5

## Bug Fix: Missing Entities When Capabilities API Fails

### Problem

Some appliances reported only a handful of entities (e.g. connectivity sensor, manual sync button, and child lock) despite having a rich reported state with many properties such as `applianceState`, `doorState`, `cyclePhase`, `timeToEnd`, `waterHardness`, and more.

This happened when the Electrolux capabilities API failed during setup — visible in the diagnostics download as:

```json
"capabilities_error": "Operation failed: get appliance capabilities for <appliance_id>"
```

### Root Cause

When the capabilities API call fails the integration enters **fallback mode** (capabilities list is empty). Previously, fallback mode only created **writable** entities (controls like selects, numbers, switches) from the built-in appliance catalog. Read-only sensors were only created if the corresponding key was already present in the appliance's reported state at the exact moment of setup.

If the appliance was idle or off during setup, most sensor keys were absent from the reported state, so those entities were never created and the device appeared nearly empty in Home Assistant.

### Fix

In fallback mode the integration now creates **all** catalog entities for the detected appliance type (WM, OV, RF, WD, DW, AC, …), not just writable ones. The catalog is already filtered per appliance type, so this does not create irrelevant entities from other appliance categories.

Read-only sensors that were previously missing — such as wash cycle phase, door state, appliance state, time remaining, water hardness — will now appear correctly even when the capabilities API is unavailable.

**Affected users:** Anyone whose diagnostics show a `capabilities_error` and whose appliance has fewer entities than expected.

### After Upgrading

If you previously had a minimal entity set due to this issue:

1. Restart Home Assistant after updating.
2. The missing entities will be created automatically.
3. If entities still appear missing, press the **Manual Sync** button on the appliance device card to force a full reload.

---

## Bug Fix: Log Spam When Refresh Token Becomes Invalid

### Problem

When a refresh token becomes invalid (e.g. after a password change, or when the same account is used in two Home Assistant instances), the integration logged the following errors **every 10 seconds indefinitely**:

```
ERROR [TOKEN-REFRESH] PERMANENT AUTH ERROR detected: ...
WARNING [TOKEN-REFRESH] Triggering reauth callback due to permanent auth error
WARNING Token refresh failed: ... Creating HA issue.
ERROR [appliance_client] Unexpected SSE error: Token expired and refresh failed
```

The HA notification and repair issue was correctly created, but the retry loop never stopped — filling the log with hundreds of identical error lines per hour until the user re-entered their credentials.

### Root Cause

After detecting a permanent 401 auth error, the token manager called the reauth callback once and returned `False`, but did not set any flag to prevent further retry attempts. Because `_consecutive_failures` was reset to 0, the exponential backoff timer was also reset, so the next retry happened immediately. The SSE reconnection loop (which retries every ~10 seconds) repeatedly triggered new token refresh attempts.

### Fix

Added a `_permanent_auth_failure` latch to the token manager:

- Once a 401/invalid-grant error is detected, the latch is set and **all further refresh attempts return immediately** without hitting the API.
- The reauth callback and HA notification are triggered exactly once.
- The latch is cleared only when new valid credentials are loaded (either via the reauth flow or after a successful token refresh).

This reduces the noise from hundreds of error lines to a single notification and HA repair issue until the user resolves the authentication problem.

---

## Files Changed

- `custom_components/electrolux/models.py` — fallback mode now creates all type-specific catalog entities instead of only writable ones.
- `custom_components/electrolux/token_manager.py` — `_permanent_auth_failure` latch prevents infinite retry loop on 401 errors.
