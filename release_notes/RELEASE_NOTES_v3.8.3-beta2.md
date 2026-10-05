# Release Notes v3.8.3-beta2

**A prerelease.** Install only if you are willing to report what it does to your
appliance. It ships unverified against real hardware by definition, and the
maintainer does not own most supported appliance types.

Cut from `feat/v3.8.3-beta1`, **not** from `main`. This file lives on `main` so the
contents are discoverable from the default branch; the release itself is the tag
`v3.8.3-beta2`, which points at the beta branch and nothing here.

## Why this prerelease exists

`v3.8.3-beta1` was published 2026-10-01 from a tree that had since diverged from
`main`. Anyone on the beta channel was therefore silently missing four merged
PRs — including the dehumidifier power fix. `v3.8.3-beta2` is the same beta
channel rebuilt on current `main`.

| PR | What beta users gain |
|---|---|
| __fix(#277, #279): dehumidifier power switch__ | `executeCommand` is never present in reported state — it is a command, not state. The phantom filter exempted only `access == "write"`, so on models where the cloud reports the capability as `readwrite` (`Husky`, `DH`) the entity was dropped and power control stopped working. A catalog entry declaring a `state_mapping` whose target is reported is now treated as evidence the capability is real. **No entity is removed, renamed or hidden.** |
| __fix(#276): hob entity quality__ | The hood filter indicator becomes a diagnostic binary sensor instead of a switch that did nothing. Existing entities are renamed; **nothing is removed or hidden**. |
| #280, #281 | Tooling and documentation only. No behaviour change. |

The scope of the power fix is set by the catalogs, not by a hardcoded name. Only
the dehumidifier catalog declares the mapping, so only dehumidifiers are
affected. Air conditioners are deliberately excluded: their `climate` entity
already lists `HVACMode.OFF` and powers the unit off with
`_send_command("executeCommand", "OFF")`, so a second power switch would
duplicate a control they already have.

## ⚠️ Breaking — still beta-only

**`Auto Door Opener` is read-only (#232).** It was a switch that accepted presses
and did nothing: the key is appliance-level, the cloud accepts the write and then
discards it. It is now a diagnostic binary sensor.

**This is why the tracking PR (#269) must not be merged.** Merging it flips
`userSelections/autoDoorOpener` from `readwrite`/`SwitchDeviceClass.SWITCH` to
`read`/`BinarySensorDeviceClass.DOOR` for every stable user, whose existing
`switch.…auto_door_opener` goes unavailable. That trade is the point of a beta
channel; it is not appropriate to ship to everyone in a patch release.

## Opt-in, off by default

**Spin speed substitution (#257).** Off by default — with it off, behaviour is
identical to 3.8.2.

- **Off:** the reported `DISABLED` value is carried and the cloud rejects the
  command with a loud `406`. Same as 3.8.2.
- **On:** a writable spin speed is substituted so the command is accepted.

Settings → Devices & Services → Electrolux → Configure → **Spin speed
substitution (experimental)**.

## What is still unverified

**#257 has never been confirmed on real hardware.** That is the sole reason
[#269](https://github.com/TTLucian/ha-electrolux/pull/269) remains a draft. The
substitute is chosen for determinism, not correctness, so a wrong pick changes
the appliance's spin speed. Needed from a tester: enable it, set a night cycle,
change an unrelated option, then report whether the command succeeded and **what
spin speed the panel shows afterwards**.

The #277 power fix was verified against 732 switch entities from real collected
diagnostics, and the single sample that exercises it is the reporter's own
dehumidifier — which has not been re-tested by them since.

Known limits: a no-op value (`0_RPM`, `0`, `OFF`) is never substituted, since
that would reproduce the exact no-spin outcome this fixes. If nothing usable
remains, the reported value is carried rather than dropped — dropping it was
3.8.1 behaviour that left laundry unspun.

## Known issue, still open

If you enabled a night cycle on **3.8.1**, re-select your program on the
appliance. That version could have left the spin setting at "no spin".

## Build

`2071 passed, 2 skipped` · coverage **95.49%** against a 90% floor · ruff and
mypy clean · CI green.