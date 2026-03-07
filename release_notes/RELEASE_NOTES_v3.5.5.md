# Release Notes v3.5.5

## Bug Fixes

### Integer command values sent as floats causing HTTP 500 errors

**Affected appliances:** Tumble dryers (antiCreaseValue, dryingTime), air purifiers (Fanspeed), and any appliance with integer-stepped number controls.

**Root cause — two separate problems in `format_command_for_appliance`:**

**Problem 1 — `"type": "number"` with integer step (regression):**

A fix was previously added to `number.py` to convert whole-number floats (e.g. `120.0`) to integers (e.g. `120`) before sending them to the API. The Electrolux API for certain appliances (notably TD tumble dryers) returns HTTP 500 when it receives `120.0` instead of `120` for capabilities like `antiCreaseValue`.

That fix was silently undone by a later refactor that introduced `format_command_for_appliance`. This new function converted every numeric value to `float` before sending — converting `120` back to `120.0` immediately after `number.py` had converted it. The bug reappeared unnoticed because the original fix was still present in `number.py`, so it looked correct in code review but was rendered completely ineffective at runtime.

**Problem 2 — `"type": "int"` not handled at all:**

The Electrolux API uses `"type": "int"` (distinct from `"type": "number"`) for capabilities like `Fanspeed` on air purifiers. This type was not included in the numeric type check inside `format_command_for_appliance`, so it fell through to the unknown-type fallback which returned the value unchanged. This happened to work correctly because `Fanspeed` values were already integers, but it was fragile and would fail if a float was ever passed in.

**Fix:**

Both issues are fixed inside `format_command_for_appliance`, which is the single place all command values pass through before being sent to the API:

- `"type": "int"` is now explicitly handled: always returns `int`, never `float`
- `"type": "number"` with a whole-number step now returns `int` for whole-number values
- `"type": "number"` with a fractional step (e.g. `step: 0.5`) still returns `float` as required

**Further hardening (follow-up):**

After confirming across all appliance samples that no fractional step values exist in practice, the fix was tightened further:

- The `step_has_fraction` guard was removed. Previously, a whole-number value with a fractional step (e.g. `2.0` with `step=0.5`) would still be sent as `2.0`. The API rejects floats universally, so this case now also returns `int(2)`.
- `"type": "temperature"` was added explicitly to the numeric cap_type tuple. Previously it was only caught when the attribute name contained the word `temperature`. This is now defence-in-depth.
- The `if cap_type == "int"` special case was collapsed into the general whole-number check — both codepaths are now the same single branch.
- Two additional tests added: one for the `"type": "temperature"` tuple path, one asserting whole numbers always return int regardless of step type.

**Regression prevention:** Five new tests total assert the _concrete Python type_ (`isinstance(result, int)`) not just the numeric value, so `120 == 120.0` equality cannot mask a future float regression.

**Affected controls (non-exhaustive):**

| Appliance | Capability | Type | Step |
|-----------|-----------|------|------|
| Tumble dryers (TD) | antiCreaseValue | number | 30 |
| Tumble dryers (TD) | dryingTime | number | 10 |
| Washer-dryers (WD) | antiCreaseValue | number | 30 |
| Washers (WM) | various spin/temp | number | 1–10 |
| Air purifiers | Fanspeed | int | 1 |
| Dishwashers (DW) | stopTime | number | 600 |
| Ovens (OV) | stopTime | number | 60 |
