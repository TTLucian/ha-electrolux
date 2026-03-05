# Release Notes v3.5.0

### Bug Fix: Post-Cycle Deferred Update Not Triggered When timeToEnd Jumps to Zero

The integration schedules a deferred API poll when a cycle ends, to compensate for Electrolux
not always pushing a final state update via SSE. The trigger watched for `timeToEnd` passing
through the window `(0, 1]` seconds.

Appliances that report `timeToEnd` in 60-second intervals (e.g. dishwashers) skip that window
entirely — the value jumps from `60` directly to `0`. The deferred poll was never scheduled for
these appliances, so post-cycle state (door state, program state, etc.) could remain stale.

Fixed by also scheduling the deferred poll when `timeToEnd` jumps from any value `> 1` directly
to `0`.