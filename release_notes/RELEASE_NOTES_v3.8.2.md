# Release Notes v3.8.2

**A patch release that removes a change introduced in v3.8.1.** If you are on 3.8.1, update: the version you are running can silently change what your washing machine does.

## ⚠️ Removed — read this first

v3.8.1 added a guard that dropped any `userSelections` value the API marks `"disabled": true` from outgoing commands, on the reasoning that the alternative was a `406` failing the whole write. That reasoning was tested on hardware and is **worse than the 406 it avoided.**

Measured on a washing machine with a night cycle set:

```
18:42:12  night cycle ON from HA            -> accepted
18:42:14  appliance now reports analogSpinSpeed = DISABLED
18:44:05  any other option write            -> payload omits analogSpinSpeed
          appliance falls to 0_RPM, display shows - - -
```

The appliance does not fall back to the program default. It falls to **"no spin"** — so the laundry comes out unspun, with no error in Home Assistant, no error in the log, and nothing on the appliance but a blank spin display.

This path is reachable from Home Assistant alone: enable night cycle (which works), then change any other option. No appliance-panel interaction is required.

The guard was added with the risk documented in the commit and the notes, and shipped anyway behind a log line. That was the wrong call — a log line is not a mitigation, and a loud `406` is the lesser fault. **The reported value is carried again, so the command is rejected instead of silently changing the machine's behaviour.**

## 🛠 Fixes

- __fix(#257): stop omitting a reported value the API marks disabled__ The v3.8.1 change described above, reverted. Option writes that would otherwise carry `analogSpinSpeed: DISABLED` are now rejected by the cloud rather than silently altering the spin setting.

- __fix(coordinator): guard `analogSpinSpeed` against stale polls (#257)__ Also found on hardware in the same run, and independent of the guard above. The 10-second follow-up poll re-proposed a superseded spin speed on **six of seven** option writes, leaving HA displaying the opposite of what the appliance was doing.

  This one compounds rather than merely misdisplays: every command is built from the reported state, so a stale spin speed — or a stale `preWashPhase` — propagates into the *next* write and silently undoes the previous one. `analogSpinSpeed` is now in the ordering guard. Unlike a fast-toggling property it holds its value between selections, so the bounded delay the guard introduces costs nothing.

## ⬆️ Upgrade notes

- __Washing machine owners__: if you enabled a night cycle on 3.8.1, **re-select your program on the appliance** to restore your spin setting. The omission could have left it at "no spin".

- __Washing machine owners__: night cycle continues to work — that part of #257 was confirmed on hardware and is unchanged by this release.

- __If you change other options while a night cycle is set__: you will now get a `406 COMMAND_VALIDATION_ERROR` / `"Value disabled"` rather than a write that quietly changes the spin speed. That is deliberate. The proper fix — substituting a real spin speed instead of dropping the key — is not in this release because it has not been verified on hardware; it is tracked in #257.

## ⚠️ Special note
Many features and appliance types supported by this integration have __not been tested__ on physical appliances in the wild. Since I do not own most of the supported appliance types and models, development and testing often rely on diagnostic data, API capabilities, and reported appliance behaviour rather than direct testing on physical appliances.

I'm therefore __counting on the community__ to help validate these features. If you encounter anything unexpected, incorrect, missing, or broken, please report it with __as much detail as possible__, ideally including __diagnostics__ and relevant __debug logs__.

Even seemingly small issues or unusual appliance behaviour can be valuable, as they help improve compatibility and prevent incorrect assumptions and guesswork from becoming permanent parts of the integration.

If you own an appliance type that hasn't been tested, your feedback is especially valuable. See [README.md](https://github.com/TTLucian/ha-electrolux/blob/main/README.md) for more information.

## 🌟 Credits
BIG thank-yous to all contributors and to all supporters!

Thank you to @McKay111, who tested v3.8.1 on hardware specifically to check whether a fix I had shipped actually worked. It did not, he showed exactly how it failed, and he caught a second defect in the same run that no test had found. Reporting a fix as unproven is far more useful than reporting that it works.

Thank you to everyone who has shared appliance diagnostics and opened issues along the way. Those files are the raw material for this project, and it cannot verify capabilities it has never seen reported.

Without you, this project would not have been possible.