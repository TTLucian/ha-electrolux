# Release Notes v3.8.1

**A patch release for a regression.** v3.7.9 and v3.8.0 both ship a change that can reset the program selected on a dishwasher or washer. This release removes it. If you are on either of those versions, this is worth updating for.

## ⚠️ Regression fixed — read this first

Since v3.7.9, a write to a `userSelections` key that no program lists — `autoDoorOpener` on a dishwasher is the reported case — was sent **without** `programUID`. On appliances that treat `userSelections` as a full replacement, the appliance took that object as a selection with no program parameters: the program kept its name but lost its settings.

Measured on a dishwasher (PNC `911434933_00`) in `READY_TO_START`:

```
timeToEnd                 : 16200  -> 780
userSelections/ecoScore   :     7  -> 1
miscellaneousState/ecoMode:  True -> False
programUID                :   ECO -> ECO   (unchanged)
```

Confirmed on the appliance display: **4:30 before the write, 0:13 after**. Re-selecting the program restored `timeToEnd` 16200 / `ecoScore` 7. The same toggle from the Electrolux app left everything intact, so the cause was the write shape, not the command being rejected.

`programUID` is now bundled into every `userSelections` write again, at all eight call sites across the switch, number, select and text platforms, on both the legacy and DAM paths. This also restores compliance with the rule in `.github/copilot-instructions.md`: *"`programUID` MUST always be included when writing any `userSelections` sub-property."*

**If you have already used a `userSelections` option on an affected appliance**, re-select the program on the appliance afterwards to restore its duration and options.

## 🛠 Fixes

- __fix(entity): always bundle `programUID` in `userSelections` writes (#232)__ by @McKay111 — the regression above. The original #232 report was a silent no-op: the write succeeded and the value reverted. That is unavoidable until the write shape the Electrolux app uses is known, but it is no longer destructive, and it is no longer silent — every such write now logs at `WARNING` naming the key and the appliance, so a user who toggles it is told rather than left watching a switch flip back.

- __fix(entity): never send a trigger default the API marks disabled (#257)__ by @McKay111 Turning on a washer's night cycle failed with `406 COMMAND_VALIDATION_ERROR` / `"Value disabled"`. The capability trigger for `nightCycle` writes `analogSpinSpeed: "DISABLED"` — and `DISABLED` is itself a value that the `analogSpinSpeed` capability marks `"disabled": true`, so applying the trigger built a payload the cloud refused. A trigger default that the target capability marks disabled is now skipped, and the current reported value is kept. __TESTING NEEDED__

- __fix(entity): omit a reported value the API marks disabled (#257)__ The companion guard for the case the reporter raised but could not reproduce: `_build_full_user_selections()` copied every reported `userSelections` value verbatim, so a reported `analogSpinSpeed: DISABLED` would be carried by *any* option write and hit the same 406. Since the payload is a full replacement, one bad sibling value took down the key the user actually changed. Logged at `WARNING`, because omission can itself let the appliance reset that field to its default.

- __fix(coordinator): guard `userSelections/programUID` against stale polls (#233)__ Found while confirming the SSE-vs-REST ordering guard. A stale REST snapshot had its `timeToEnd` correctly rejected while `programUID` from the same snapshot went through, leaving the program select showing the wrong program until the next poll. `programUID` is safe to include in the ordered set precisely because it changes only on an explicit selection, so it cannot churn the history.

## ✅ Confirmed on hardware

Both coordinator fixes from v3.8.0 have now been verified on real appliances by @McKay111, and the `TESTING NEEDED` marker on the v3.8.0 #233 entry is superseded.

- **#233 (SSE vs REST ordering).** The guard fired on a real stale poll carrying a 60-minute-held predecessor, and on a washer `PAUSE`/`RESUME` in the opposite direction. The strongest evidence: a dishwasher `timeToEnd` where SSE said 780, the poll said 16200, and the appliance display said 0:13 — the guard kept the right value. The phantom `Running` that ended a cycle twice on 3.7.8 did not recur.
- **#230 (orphaned post-transition poll).** The fast door sequence that produced two polls 400 ms apart now produces one. The cancel was observed landing mid-flight, with no second completion and no phantom `Paused`.
- **One layer remains unexercised:** the cooperative re-check before applying (`Discarding superseded state-refresh`) has not been seen firing, because in the common path the `await` absorbs the cancel first. It is covered by unit tests only.

## 🔧 Internal / chores

- `ruff check`, `ruff format` and `mypy` now cover `tests/` as well as the component. `tests/` had accumulated 28 unformatted files and a mypy error that went unnoticed since July, because CI only ever looked at `custom_components/electrolux`. Applying the format is verified semantics-preserving — every reformatted file compares equal under `ast.dump()`.

## ⬆️ Upgrade notes

- __Dishwasher and washer owners on 3.7.9 or 3.8.0__: update for the program-reset regression described above, and re-select the program on any appliance where you have used a `userSelections` option.

- __Washing machine owners__: `switch.*_night_cycle` and similar options should now write successfully instead of failing with a 406. Worth confirming on your machine, as this is not yet hardware-verified.

- __Appliance-level options on dishwashers and washers__ (e.g. `autoDoorOpener`): these remain a no-op — the command succeeds and the value reverts, with a `WARNING` in the log. This part of #232 is unresolved; the shape the Electrolux app sends is not yet known. The previous alternative damaged the selected program, so an announced no-op is the safer trade until that is understood. If you would rather the option were not exposed at all, say so in an issue and it can be made read-only.

## ⚠️ Special note
Many features and appliance types supported by this integration have __not been tested__ on physical appliances in the wild. Since I do not own most of the supported appliance types and models, development and testing often rely on diagnostic data, API capabilities, and reported appliance behaviour rather than direct testing on physical appliances.

I'm therefore __counting on the community__ to help validate these features. If you encounter anything unexpected, incorrect, missing, or broken, please report it with __as much detail as possible__, ideally including __diagnostics__ and relevant __debug logs__.

Even seemingly small issues or unusual appliance behaviour can be valuable, as they help improve compatibility and prevent incorrect assumptions and guesswork from becoming permanent parts of the integration.

If you own an appliance type that hasn't been tested, your feedback is especially valuable. See [README.md](https://github.com/TTLucian/ha-electrolux/blob/main/README.md) for more information.

## 🌟 Credits
BIG thank-yous to all contributors and to all supporters!

Huge thanks to @McKay111. Every fix in this release came from his reports, and what made them trustworthy was the method: config-entry diagnostics, recorder timelines, and log excerpts captured at the moment of the fault. He re-tested v3.8.0 and found that a fix shipped in it had made things worse — the program-reset regression above — then measured it on the appliance display rather than in Home Assistant, and ruled out his own automations as a confound. He also found the `programUID` gap while confirming something that had already worked. That is a rare and very welcome kind of reporting.

Thank you to everyone who has shared appliance diagnostics and opened issues along the way. Those files are the raw material for this project, and it cannot verify capabilities it has never seen reported.

Without you, this project would not have been possible.
