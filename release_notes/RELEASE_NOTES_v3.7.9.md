# Release Notes v3.7.9

A large release focused on coordinator state correctness, a rewritten dishwasher catalog, and corrected appliance catalogs verified against real diagnostics.

## 🛠 Fixes

- __fix(coordinator): never let a REST snapshot roll back fresher SSE state (#233 / #251)__ by @McKay111 A delayed `STATE_CHANGE_REFRESH_DELAY` poll re-applied a REST snapshot that was already stale, producing a real `Off → Running → Off` sequence in the recorder timeline 10s after a dishwasher cycle ended. The stale value survived because `PAUSED`/`RUNNING` count as active for the stale-`timeToEnd` watchdog. REST snapshots are now narrowed by value so an older snapshot can never overwrite fresher SSE state, across all five apply sites.

- __fix(coordinator): a superseded state-refresh must never apply (#230 / #247)__ by @McKay111 A phantom `Paused` state lasting 25–33 minutes after a mid-cycle door opening. `_schedule_state_refresh` cancelled the in-flight task and stored its replacement, but the cancelled task's done-callback fired one loop iteration later and popped the *replacement* out of the registry — leaving it uncancellable, and it later applied a REST snapshot captured before the fresher SSE it had overwritten.

- __fix(auth): distinguish 403 FORBIDDEN_RESOURCE from account auth failures (#212)__ by @IvanAlekseev `AUTH_STATUS_CODES = (401, 403)` treated any `403` as an account-auth failure, so a `FORBIDDEN_RESOURCE` during polling ("Resource is not owned by client or appliance is not registered") walked into `_consecutive_auth_failures` → `ConfigEntryAuthFailed` → repair issue, forcing a re-auth for perfectly valid credentials. The exemption lives in `is_auth_error()` itself, so polling, the SSE-silence probe, the SSE failure handlers and `handle_authentication_error` all inherit the fix.

- __fix: DW maintenance keys, unknown state while offline, programUID only for program-scoped keys (#217, #218, #231, #232 / #245)__ The DW maintenance entities were never created because the catalog used the capabilities-document form (`maint1_occured`/`maint1_threshold`) while appliances report under `applianceCareAndMaintenance0/1/occured` and `/1/threshold`. Five appliance-level selects (endOfCycleSound, defaultExtraRinse, autoDosing/adTankA- and adTankBConfiguration, userSelections/extraRinseNumber) were permanently unknown and un-settable because `_is_supported_by_program()` could not find a program listing them. Switches now return `None` (not `False`) from `is_on` when offline and the value is unknown — automations testing `is_state(switch.x, off)` will stop matching while the appliance is offline. Appliance-level keys no longer bundle `programUID` into write payloads.

- __fix(rvc): take Gordias fan speeds and water pump rate from the appliance (#228 / #246)__ by @ChristmasSocks0824 `fan_speed_list` was a hardcoded `["energySaving", "max"]` pair taken from a Cybele sample, but a Gordias declares four values (quiet, energySaving, standard, powerful) — the vacuum card offered two modes that do not exist and hid two that do, and selecting "max" would be rejected by the appliance. The list is now built from the live `vacuumMode` capability, preserving declared order, with fallback for Cybele. `waterPumpRate` was catalogued read-only (a sensor you could only look at) and is now a usable control.

- __fix(hd): correct hood catalog against HD-942051563_00 diagnostics (issue #211 / #214)__ `lightColorTemperature` is a 0–100 percentage scale on this hood, not 2700–6500 K, so the bogus `TEMPERATURE` device class and `K` unit were removed. `hoodAutoSwitchOffEvent` is a boolean capability, not an `active`/`inactive` string. `lightIntensity` no longer carries a `POWER_FACTOR` device class. `soundVolume` is not advertised on this hood, so it became a reported-only sensor instead of a failing writable number. Filter timers switched to `minutes` (values `180000`/`918000` are almost certainly minutes, not hours). Added `hoodFilterCharcIndication` and `hoodFilterGreaseIndication`, which the device reports but the catalog omitted.

- __fix(catalog): drop the unverified AC power/energy consumption keys (#229 / #248)__ The AC catalog advertised `powerConsumption` and `energyConsumption` as real capabilities. They do not exist: neither key appears in any of the 54 collected diagnostics, neither appears anywhere in `electrolux-group-developer-sdk` 0.7.0, and the four AC/Bogong samples report no such capability. Per `AGENTS.md`, capability names must be verified against live device data rather than guessed — an invented key in a catalog marked "Full (AC + Bogong verified)" misrepresents what the project has observed.

- __fix(ov): suppress the microwave power control the oven never advertises (#252, #253)__ A plain oven reports `targetMicrowavePower` in reported state as `65535` — the unsigned 16-bit not-applicable sentinel — without ever declaring the capability. The catalog created a NUMBER entity from that, and because the number platform derives its range from the capability, the result was a slider with `min == max == 0` that could never move. The entity is now suppressed at creation time, so an oven without a microwave no longer gets the control at all. The previous #193 behaviour is unchanged: an appliance that advertises the capability but disables every `MICROWAVE_*` program still gets the entity, disabled by default. __TESTING NEEDED__

## ✨ Features

- __feat(dw): expose maintenance indicators (#223)__ by @monsivar Dishwasher care-and-maintenance entities are now surfaced, so wash-filter and descaler status are visible and resettable instead of being catalogued but unreachable.

- __feat(dw): expose dishwasher alert codes (#222 / #240)__ by @monsivar Dishwasher alert codes are exposed as sensors, so a fault is readable without digging through diagnostics. The same change adds the two alert names to the Nynorsk `nn.json` translation file.

- __feat(dw): verify model fixture and program order (#224)__ by @monsivar Dishwasher model fixtures and program ordering are verified against collected data, including the Norwegian Bokmål strings that were previously stranded in a removed `no.json`.

- __feat(so): expose microwave power, OTA3 and message-queue diagnostics (#236)__ Verified against all four SO steam-oven diagnostics in samples. `upperOven/targetMicrowavePower` is a readwrite wattage control (advertised on the microwave-combi models, present in reported state on all four). `oTA3CurrentVersion`/`oTA3TargetVersion`/`oTA3State`/`oTA3LastResult` are reported-state-only firmware-update diagnostics, disabled by default. Message-queue sync diagnostics were added. __TESTING NEEDED__

- __Improve dishwasher score presentation (#225)__ by @monsivar Dishwasher score entities are presented more clearly on the UI.

- __Improve dishwasher status metadata (#241)__ by @monsivar Dishwasher status entities carry richer metadata for a clearer UI.

- __fix(translations): localize entity names via HA catalogs and add missing keys__ Entity display names were hard-coded in English via `_attr_name`, so the integration ignored the user's Home Assistant language setting. Names now resolve through `translation_key` + `platform_translations` with an English fallback, and missing translation keys were added — including the cloud diagnostic sensors (API, Live Stream).

- __Add Norwegian Bokmål (nb) translation file (#219)__ by @monsivar Norwegian Bokmål locale to match the Home Assistant language code.

## 🔧 Internal / chores

- Dishwasher entities and internals reorganized (#227) by @monsivar, following the catalog path corrections in #245.

- Dishwasher command button icons fixed (#220) by @monsivar.

- Improved execute-command button names (#238, #239) by @monsivar — co-authored with the maintainer.

- Dishwasher status metadata improved (#241) by @monsivar — co-authored with the maintainer.

- `alerts.extra_state_attributes` annotated as `dict[str, Any]` for stricter typing (#242).

- `ElectroluxEntity`/`Button` and the test helper accept an optional `icon` (#237).

- Vacuum `capability_attributes` narrowed before use (#249).

- Tracked `pyrightconfig.json` so Pylance parses the project's Python version (#250).

- Python dependency group bumped with 2 updates (#213, #235, #244) by Dependabot.

## ⬆️ Upgrade notes

- __Dishwasher owners__: the care-and-maintenance and alert entities now appear. If you relied on `is_state(switch.x, off)` in automations, note that a switch with an unknown value now reports `None` rather than `False` while the appliance is offline, so those conditions will no longer match during an outage.

- __Vacuum (Gordias) owners__: the fan speed list is now read from your appliance. If you had selected a speed the device does not support, re-pick one from the list after upgrading.

- __Hood owners__: `lightColorTemperature` is a percentage on models that do not advertise a Kelvin range, and the device class/unit changed accordingly. Automations or dashboards referencing a temperature unit for that entity may need updating.

- __Owners of an oven with no microwave__: the `number.target_microwave_power_*` entity is no longer created. Home Assistant does not remove registry rows for entities an integration stops providing, so the stale entry must be deleted once from the entity settings — it will not come back.

## ⚠️ Special note
Many features and appliance types supported by this integration have __not been tested__ on physical appliances in the wild. Since I do not own most of the supported appliance types and models, development and testing often rely on diagnostic data, API capabilities, and reported appliance behaviour rather than direct testing on physical appliances.

I'm therefore __counting on the community__ to help validate these features. If you encounter anything unexpected, incorrect, missing, or broken, please report it with __as much detail as possible__, ideally including __diagnostics__ and relevant __debug logs__.

Even seemingly small issues or unusual appliance behaviour can be valuable, as they help improve compatibility and prevent incorrect assumptions and guesswork from becoming permanent parts of the integration.

If you own an appliance type that hasn't been tested, your feedback is especially valuable. See [README.md](https://github.com/TTLucian/ha-electrolux/blob/main/README.md) for more information.

## 🌟 Credits
BIG thank-yous to all contributors and to all supporters!

Huge and heartfelt thanks to @monsivar, who authored the bulk of the dishwasher work in this release — the maintenance indicators (#223), alert-code support via #240, the verified model fixture and program order (#224), the score presentation (#225), the command button icons (#220), the entity and internals reorganization (#227), the status metadata (#241), and the Norwegian Bokmål translation (#219). That is a sustained body of work across every dishwasher change here.

Thank you to @McKay111 for the two coordinator state-rollback reports with recorder timelines, to @ChristmasSocks0824 for the Gordias diagnostics, and to @IvanAlekseev for the auth fix — each of you turned a vague symptom into a verifiable root cause, which is what made those fixes possible. Thanks also to Dependabot for the three dependency bumps.

And a general thank-you to everyone who has shared appliance diagnostics and opened issues along the way. Those files are the raw material for this entire release — several catalog corrections here were only possible because a reporter attached the evidence rather than describing the symptom — and the project simply cannot verify capabilities it has never seen reported.

Without you, this project would not have been possible.

