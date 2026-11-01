# Release Notes v3.8.4

## 🛠 Fixes

- __fix(#309): mutually exclusive tDEconomy switches__ by @TTLucian The three tDEconomy switches (Eco/Quick/Night) on tumble dryers always failed with "Command not accepted: Capability disabled" because the full `userSelections` payload carried conflicting values (multiple switches on simultaneously). Now when writing one switch on, the others are forced off in both the payload and HA's state. (#310)

- __fix(#308): provide the native_ climate temperature API__ by @thecode (Shay Levy) Home Assistant 2026.11 renames climate temperature members to `native_*`. The integration now implements `native_temperature_unit`, `native_current_temperature`, etc., with backward-compatible aliases for HA < 2026.11. Eliminates deprecation warnings on newer HA versions.

- __fix(#287): mirror water usage sensor state_class in WD catalog__ by @TTLucian The WD (washer-dryer) catalog's `waterUsage` entry was not updated alongside the WM catalog. Added `device_class=WATER`, `unit=LITERS`, and `state_class=TOTAL_INCREASING` for consistency. (#304)

## 🔧 Internal / chores

- Aligned pre-commit ruff rev with uv.lock (v0.17.2).
- Bumped ruff to 0.17.2 in the tooling group.
- Bumped Home Assistant to latest patch.
- Bumped github-actions-dependencies group.

## ⬆️ Upgrade notes

- This version requires Home Assistant 2026.10+.
- `electrolux-group-developer-sdk>=0.7.0` is required; Home Assistant installs it automatically from the integration manifest on update.

## ⚠️ Special note

Many features and appliance types supported by this integration have __not been tested__ on physical appliances in the wild. Since I do not own most of the supported appliance types and models, development and testing often rely on diagnostic data, API capabilities, and reported appliance behaviour rather than direct testing on physical appliances.

I'm therefore __counting on the community__ to help validate these features. If you encounter anything unexpected, incorrect, missing, or broken, please report it with __as much detail as possible__, ideally including __diagnostics__ and relevant __debug logs__.

Even seemingly small issues or unusual appliance behaviour can be valuable, as they help improve compatibility and prevent incorrect assumptions and guesswork from becoming permanent parts of the integration.

If you own an appliance type that hasn't been tested, your feedback is especially valuable. See [README.md](https://github.com/TTLucian/ha-electrolux/blob/main/README.md) for more information.

## 🌟 Credits

BIG thank-yous to all contributors and to all supporters!

Special thanks to **@thecode (Shay Levy)** for contributing the native climate temperature API migration (PR #308), ensuring compatibility with Home Assistant 2026.11.

Without you, this project would not have been possible.