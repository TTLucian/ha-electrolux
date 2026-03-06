# Release Notes v3.5.2

### Confirmed: Electrolux cloud does not push a final SSE update when a cycle ends

Real-device log analysis on a dishwasher completing an ECO cycle confirmed the following sequence:

| Time | SSE event |
|------|-----------|
| 05:28:03 | `timeToEnd` 120 → 60 s |
| 05:29:04 | `applianceState` → `END_OF_CYCLE` |
| 05:29:04 | `timeToEnd` 60 → 0 |
| 05:29:04 | `cyclePhase` → `UNAVAILABLE` |
| 05:29:08 | `applianceState` → `OFF` |
| — | *(no further SSE updates)* |
| 05:30:14 | Deferred API poll fires (70 s after cycle end) |

The deferred poll at `05:30:14` detected that `timeToEnd` was absent from the SSE stream entirely
in its final form, confirming that **the Electrolux cloud API stops pushing SSE updates once the
appliance reports `OFF`**. Without the compensating poll, sensors like `doorState`, `cyclePhase`,
and `rinseAidLevel` would remain stale until the next scheduled 6-hour refresh.

---

### Fix: Deferred end-of-cycle poll trigger threshold corrected for minute-granularity appliances

**Confirmed API quirk:** The Electrolux cloud reports `timeToEnd` in seconds, but minute-granularity
appliances (e.g. dishwashers) count down in whole minutes. `timeToEnd` steps as `120 → 60 → 0` —
it never passes through the `(0, 1]` range that the previous trigger relied on.

The old skip-detection workaround fired on every normal `60 → 0` transition, misclassifying it as
an anomaly when it was in fact the appliance's natural last step.

**Fix:** The trigger threshold has been raised from `1 s` to `60 s`. The deferred poll now fires
correctly at the last-minute mark (`timeToEnd = 60`), which is the final non-zero SSE value for
these appliances. Skip detection is preserved for the genuinely abnormal case where `timeToEnd`
jumps from `> 60 s` directly to `0` without stopping at `60`.
