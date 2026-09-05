# Release Notes v3.7.8

## 🛠 Fixes

- __fix(button): SO START gating must follow the cavity state machine (#206)__ by @TTLucian On structured ovens (SO), the START/STOPRESET button gating was based on the root-level appliance state, which on some samples only exposes ALARM/OFF/RUNNING. But the cavity's own state machine (`upperOven/applianceState`) is the full plain-oven vocabulary (incl. READY_TO_START, PAUSED, DELAYED_START, END_OF_CYCLE) — verified on SO-944005079_00 (issue #206). Executable commands are now evaluated against that scoped cavity machine, so START correctly appears whenever the cavity is ready, and STOPRESET while it is running/paused/delayed.

## ✨ Features

- __feat(models): retain last-known advertised temperature readings across state polls (#205)__ by @TTLucian Compartment temperatures (e.g. `freezer/sensorTemperatureC`, fridge, extraCavity, iceMaker) are no longer wiped by a full state poll. The Electrolux cloud omits these live readings from poll responses and only pushes them as discrete SSE events, so previously every poll evicted the last pushed value until the next event. Advertised read-temperature capabilities are now retained across polls. Explicitly nulled values are still honored — e.g. the oven's food-probe display temperature correctly blanks when the probe is unplugged (v3.4.0 behavior preserved). __TESTING NEEDED__

- __feat(sdk): bump electrolux-group-developer-sdk to 0.7.0 + integrate livestream closing callbacks (#207)__ by @IvanAlekseev The SSE stream now reports disconnections in real time via the SDK's `do_on_livestream_closing_list` callbacks, so connectivity status flips on the actual socket close rather than waiting for the next reconnect event. Planned renewals (6h rotation, restarts) are correctly ignored as drops.

## 🔧 Internal / chores

- Bumped `electrolux-group-developer-sdk` to `>=0.7.0` in the manifest, `pyproject.toml`, and `requirements_test.txt`; lockfile updated to 0.7.0 (#207).

- SSE disconnect handling reworked: the disconnect grace-period timer is preserved across rapid SDK backoff retries, the drop counter is not inflated during an existing grace window, a pending disconnect debounce is cancelled on valid incoming data, and a stale transition is guarded once the stream returns to streaming (#207).

## ⬆️ Upgrade notes

- This version requires `electrolux-group-developer-sdk>=0.7.0`; Home Assistant installs it automatically from the integration manifest on update.

## ⚠️ Special note
Many features and appliance types supported by this integration have __not been tested__ on physical appliances in the wild. Since I do not own most of the supported appliance types and models, development and testing often rely on diagnostic data, API capabilities, and reported appliance behaviour rather than direct testing on physical appliances.

I'm therefore __counting on the community__ to help validate these features. If you encounter anything unexpected, incorrect, missing, or broken, please report it with __as much detail as possible__, ideally including __diagnostics__ and relevant __debug logs__.

Even seemingly small issues or unusual appliance behaviour can be valuable, as they help improve compatibility and prevent incorrect assumptions and guesswork from becoming permanent parts of the integration.

If you own an appliance type that hasn't been tested, your feedback is especially valuable. See [README.md](https://github.com/TTLucian/ha-electrolux/blob/main/README.md) for more information.

## 🌟 Credits
BIG thank-yous to all contributors and to all supporters!

Without you, this project would not have been possible.