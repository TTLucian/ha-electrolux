# Release Notes v3.8.7

## 🛠 Fixes

- __fix(wm): preserve program-specific washer selections__ by @TTLucian Washer option writes now keep the complete `userSelections` payload while handling disabled spin-speed values using the active program's advertised default when that value is valid. Recent successful writes are protected from stale REST snapshots for a bounded period, and that protection is cleared when the appliance changes programs. (#349)

- __fix(wm): expose unadvertised washer values as read-only__ by @wit3 Washer properties that appear in reported state but are absent from the appliance's capabilities are exposed as read-only entities instead of unsupported controls. When `startTime` is not advertised, it appears as a duration sensor and hides negative "not set" values; when advertised, it remains a writable number. (#339, #348)

- __fix(sensor): preserve appliance type and capability hash values__ by @wit3 The diagnostic sensors now show these identifiers exactly as reported, without title-casing the appliance type or altering the case of the capability hash. (#340)

- __fix(translations): distinguish care and maintenance entities__ by @wit3 Maintenance occurrence and threshold entities now include their item index in the translated name, so repeated entities can be told apart. Entity IDs and unique IDs are unchanged. (#341)

- __fix(translations): distinguish shared program-select names__ by @wit3 Select entities with the same leaf name under different sources now receive distinct translated names where needed. Entity IDs and unique IDs are unchanged. (#347)

- __fix(log): reduce severity of recovered SSE stream drops__ by @IG-ABHINAV Known transport-level SSE disconnects that the SDK reconnects from are logged as warnings rather than errors. Other SSE errors, including HTTP, authentication, and JSON decoding failures, retain their severity. (#346)

## 🔧 Internal / compatibility

- __fix(init): remove the redundant config-entry update listener__ by @peetervalk Reconfigure and reauthentication continue to reload through their config-flow path without registering a second listener. This removes a Home Assistant 2026.11 warning and avoids relying on the listener behavior scheduled to stop working in Home Assistant 2026.12. (#345)

- __fix(coordinator): refresh only diagnostic sensors after REST probes__ by @TTLucian API health checks and successful API calls now refresh cloud diagnostic sensors without waking every appliance entity. Diagnostic attributes remain current on each probe. (#352)

## ⬆️ Upgrade notes

- This version requires Home Assistant 2026.11+.
- `electrolux-group-developer-sdk>=0.7.0` is required; Home Assistant installs it automatically from the integration manifest on update.

## ⚠️ Special note

Many features and appliance types supported by this integration have __not been tested__ on physical appliances in the wild. Since I do not own most of the supported appliance types and models, development and testing often rely on diagnostic data, API capabilities, and reported appliance behaviour rather than direct testing on physical appliances.

I'm therefore __counting on the community__ to help validate these features. If you encounter anything unexpected, incorrect, missing, or broken, please report it with __as much detail as possible__, ideally including __diagnostics__ and relevant __debug logs__.

Even seemingly small issues or unusual appliance behaviour can be valuable, as they help improve compatibility and prevent incorrect assumptions and guesswork from becoming permanent parts of the integration.

If you own an appliance type that hasn't been tested, your feedback is especially valuable. See [README.md](https://github.com/TTLucian/ha-electrolux/blob/main/README.md) for more information.

## 🌟 Credits

BIG thank-yous to all contributors and to all supporters!

Special thanks to @wit3 for the washer compatibility, diagnostics, and translation improvements; @IG-ABHINAV for the SSE logging improvement; and @peetervalk for the Home Assistant compatibility fix.

Without you, this project would not have been possible.
