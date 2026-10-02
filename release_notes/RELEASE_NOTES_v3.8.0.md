# Release Notes v3.8.0

A patch release carrying one hotfix. **v3.7.9 shipped an incomplete fix for #233; this release completes it.** The v3.7.9 notes stated that the phantom-state problem was fixed. On real appliance timings it was not.

## 🛠 Fixes

- __fix(coordinator): age an SSE value from when it was superseded, not delivered (#233)__ by @McKay111 Reported with recorder timelines on a dishwasher and a washing machine, then re-confirmed after v3.7.9 shipped. The #251 guard measures a value's age from when SSE *first delivered* it — but a dishwasher delivers `RUNNING` once at the start of a ~2h cycle, so by the time the post-transition poll ran, that entry had already been pruned on delivery age. `history[:-1]` was empty, `_superseded_by_sse` had nothing to compare against, and the poll's stale `RUNNING` was applied: the phantom the guard exists to prevent.

  A value is superseded by the entry that *replaced* it, so its age now runs from its successor's timestamp. Both halves move together — the prune and the supersession test use the same rule, deliberately kept in step:

  ```python
  # _prune_sse_history: drop the oldest entry only once its *successor* is outside the window
  while len(history) > 1 and history[1][0] < cutoff:
      history.pop(0)

  # _superseded_by_sse: history[i] is superseded while history[i+1] is inside the window
  ```

  Why the tests missed it: `_feed_history` spaced values 0.2s apart, so every entry was younger than the 15s authority window and the age paths were never exercised. It is now a `gap` parameter, and the regression tests use the field timings — a 2h cycle and a 3.5 min program setup. Two further tests pin the behaviour that must *not* change: a value SSE never delivered still applies (a dropped SSE event is still recovered by the next poll), and REST is authoritative again once the window has passed.

  __TESTING NEEDED__ — please confirm on hardware. With debug logging on, the line to watch is `REST snapshot for %s proposes superseded applianceState=READY_TO_START` about 10s after a start.

## ⬆️ Upgrade notes

- __If you are affected by #233__: the phantom state will persist after upgrading to v3.7.9 alone. Move to this release. Any `for:` guard or workaround automation added to cope with the phantom is no longer needed and can be removed.

- `test_history_is_pruned_by_age` now expects `["OFF", "READY_TO_START"]` rather than `["READY_TO_START"]`. That is the intended semantic change: `OFF` was superseded only moments ago, so it has not aged out.

## ⚠️ Special note
Many features and appliance types supported by this integration have __not been tested__ on physical appliances in the wild. Since I do not own most of the supported appliance types and models, development and testing often rely on diagnostic data, API capabilities, and reported appliance behaviour rather than direct testing on physical appliances.

I'm therefore __counting on the community__ to help validate these features. If you encounter anything unexpected, incorrect, missing, or broken, please report it with __as much detail as possible__, ideally including __diagnostics__ and relevant __debug logs__.

Even seemingly small issues or unusual appliance behaviour can be valuable, as they help improve compatibility and prevent incorrect assumptions and guesswork from becoming permanent parts of the integration.

If you own an appliance type that hasn't been tested, your feedback is especially valuable. See [README.md](https://github.com/TTLucian/ha-electrolux/blob/main/README.md) for more information.

## 🌟 Credits
BIG thank-yous to all contributors and to all supporters!

Huge thanks to @McKay111, who reported #233 and #230 with recorder timelines, came back after v3.7.9 to show the fix would not have worked, and worked out the actual root cause himself — including a reproduction that isolated the flaw in the test fixture, not just in the code. That is exactly the kind of reporting that turns a guess into a fix.

Thank you to everyone who shared appliance diagnostics and opened issues along the way. Those files are the raw material for this project, and it simply cannot verify capabilities it has never seen reported.

Without you, this project would not have been possible.