# Release Notes v3.6.10

- Fixed a live-update regression where entities like `timeToEnd` could stop changing even though SSE was connected.
- Added an SSE stall watchdog: when the stream is connected but no events arrive for too long while appliances are online, the integration now reconnects SSE automatically.
- Added a continuous SSE liveness monitor loop (60-second checks) with proper startup and shutdown lifecycle handling.
- Seeded SSE liveness timestamps on stream connect to avoid premature stall detection right after reconnect.
- Added focused debug logging around SSE event cadence, stall detection, and watchdog-triggered stream recovery.
- Added tests for SSE timestamp tracking and stalled-stream auto-restart logic.
- Hardened coordinator test task mocks to close scheduled coroutines and support keyword arguments, removing unawaited coroutine warnings in test runs.

# Status update:
Due to the recent GitHub Copilot usage price skyrocketing starting from 1st of July 2026, future updates and fixes for this integration will be released at a much slower pace.

In the past, I was able to fully develop major features of this integration with just a $10 Copilot subscription.
However, the latest updates alone required about $60, consuming all existing BuyMeACoffee donations (already fully spent) and additional personal funds. At the current pricing, maintaining the previous fast development cycle is no longer feasible.

The project remains active, but development will continue at a reduced, sustainable pace.