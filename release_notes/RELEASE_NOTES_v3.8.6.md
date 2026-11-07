# Release Notes v3.8.6

## 🛠 Fixes

- __fix(fuji): support Fuji air purifier controls (#335, #336)__ by @TTLucian Fuji models can be switched on and off through `executeCommand` when `Workmode` does not provide a `PowerOff` option. Fan control now uses the advertised `FanSpeed` command while continuing to read the reported `Fanspeed` state. Mode-trigger matching is case-insensitive.

- __fix(td): improve tumble-dryer capability handling (#329, #330)__ by @wit3 `endOfCycleSound` is presented as a CONFIG select, consistent with the shared catalog. Dryer keys the appliance does not advertise fall back to read-only behavior rather than creating unsupported controls.

- __fix(sensor): handle appliance-reported values correctly (#324, #326, #332)__ by @wit3 Nominal load-weight sensors ignore the `65535` not-applicable sentinel, a leftover water-tank debug warning was removed, and `applianceInfo` sensors now read from reported properties.

- __fix(translations): correct entity names and missing translations (#318, #319, #323, #327, #328, #331)__ by @MaxDev98 and @wit3 Corrected German and Italian names and added missing translations, including dryer entity names, the `dwywSelect` command select, and Dwyw step 2 sensor.

- __fix: support Home Assistant 2026.11 (#333, #334)__ by @TTLucian Updated `DeviceInfo` construction and the climate temperature API for Home Assistant 2026.11.

## 🔧 Internal / chores

- Improved DEBUG logging for number writes with live capability definitions, relevant trigger conditions, and current reported driver state (#337). This helps investigate cloud-rejected number commands.
- Updated tooling and framework dependencies.

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

Without you, this project would not have been possible.
