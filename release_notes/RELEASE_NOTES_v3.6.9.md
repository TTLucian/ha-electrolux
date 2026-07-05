# Release Notes v3.6.9

- Verified and expanded Dehumidifier support against a real `DH` diagnostic: corrected DH modes and fan speeds, fixed fallback humidity range, added missing DH entities.
- Improved startup recovery when Electrolux does not return capabilities immediately: the integration now retries capability fetches in the background and reloads automatically when the missing data becomes available.
- Fixed stale states after SSE reconnects: appliance states are now resynced on every real SSE reconnection, with debounce protection to avoid hammering the API.
- Improved reported-state fallback handling so some values can still be shown read-only when newer models stop advertising a writable capability.
- Expanded diagnostics and cleanup: added useful purifier diagnostics, removed several internal constant/noise entities, and tightened metadata for dishwasher, washer, dryer, oven, and dehumidifier entities.
- Many other fixes and improvements that I cannot remember...

NOTE: I can't verify if everything is working corectly for all appliance types, please open issues if any problems appear. Thank you!