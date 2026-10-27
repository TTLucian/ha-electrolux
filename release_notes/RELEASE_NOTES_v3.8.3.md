# Release Notes v3.8.3

## 🛠 Fixes

- __fix(#232): omit programUID for appliance-level userSelections writes__ by @TTLucian Appliance-level keys like `autoDoorOpener` were bundled with `programUID` in the write payload, causing the cloud to silently ignore the write. Now appliance-level keys are written bare, without `programUID`. (#298)

- __fix(#297): skip out-of-range number sentinels in userSelections payload__ by @TTLucian `_build_full_user_selections` copied `dryingTime: 65535` (not-applicable sentinel) into the payload, causing the cloud to reject the entire command with 406 "Number out of range". Sentinel values outside the capability's min/max range are now skipped. (#299)

- __fix(#267): treat cross-attribute ne triggers as advisory__ by @TTLucian The trigger `analogSpinSpeed != DISABLED -> nightCycle = False` fired on spin-only writes and optimistically showed night cycle as off, but the appliance didn't honour it. Cross-attribute `ne` triggers are now advisory — applied in the payload but not optimistically, so HA waits for SSE to confirm. (#300)

- __fix(#266): add connectivityState to SSE_ORDERED_PROPERTIES__ by @TTLucian A stale REST poll could put back a `disconnected` that SSE had already replaced with `connected`, blanking every entity on the appliance for minutes. `connectivityState` is now guarded. (#303)

- __fix(switch): keep power control for command capabilities (#277, #279)__ by @TTLucian Power control was dropped on models where the cloud reports the capability as `readwrite` instead of `write`. A catalog entry declaring a `state_mapping` whose target is reported is now treated as evidence the capability is real.

- __fix(hb): entity quality for induction hobs (#276)__ by @TTLucian The hood filter indicator becomes a diagnostic binary sensor instead of a switch that did nothing. Existing entities are renamed; nothing is removed or hidden.

- __fix: update device class imports for HA 2026.10 .const migration__ by @TTLucian Migrated voluptuous schemas to probatio for HA 2026.10 compatibility.

- __fix: remove unused type: ignore after HA 2026.10.2 bump__ by @TTLucian Cleaned up unused type ignore comments after the framework bump.

## ✨ Features

- __feat(models): water usage sensor state_class for Energy dashboard (#287)__ by @TTLucian Added `state_class: total_increasing` to the washing machine water usage sensor so it is selectable in the Energy dashboard. Also added `duration` device_class to hood filter timers that were missing it. (#301, #302)

## 🔧 Internal / chores

- HA 2026.10 compatibility migration (probatio schemas, .const imports).
- Adopted shared tooling standard across repositories.
- Hardened workflows, dependabot, and coverage gate.
- Aligned pre-commit with CI, added drift guards.
- Removed dead files and stale editor type diagnostics.
- Migrated from black to ruff format.
- Updated pre-commit tool revs to match uv.lock.

## ⬆️ Upgrade notes

- This version requires Home Assistant 2026.10+.
- `electrolux-group-developer-sdk>=0.7.0` is required; Home Assistant installs it automatically from the integration manifest.

## ⚠️ Special note

Many features and appliance types supported by this integration have __not been tested__ on physical appliances in the wild. Since I do not own most of the supported appliance types and models, development and testing often rely on diagnostic data, API capabilities, and reported appliance behaviour rather than direct testing on physical appliances.

I'm therefore __counting on the community__ to help validate these features. If you encounter anything unexpected, incorrect, missing, or broken, please report it with __as much detail as possible__, ideally including __diagnostics__ and relevant __debug logs__.

Even seemingly small issues or unusual appliance behaviour can be valuable, as they help improve compatibility and prevent incorrect assumptions and guesswork from becoming permanent parts of the integration.

If you own an appliance type that hasn't been tested, your feedback is especially valuable. See [README.md](https://github.com/TTLucian/ha-electrolux/blob/main/README.md) for more information.

## 🌟 Credits

BIG thank-yous to all contributors and to all supporters!

Without you, this project would not have been possible.