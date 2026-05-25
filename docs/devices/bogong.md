# Bogong AC (Westinghouse WSD27HWAI)

## Hardware

| Property | Value |
|----------|-------|
| Model | Westinghouse WSD27HWAI |
| Firmware | `VM211_A_04.43.06_BOGONG` |
| Data model | `1.0.1` |
| API type | DAM (cloud command API) |
| Verified units | 3 (`956007025415068981045767`, `956007025415070231045767`, `956007025436004181045767`) |

## Entities

### Climate

| Entity | Notes |
|--------|-------|
| `climate.<name>` | Supports off/auto/cool/heat/dry/fan_only. Power via `executeCommand ON/OFF`. |

### Select

| Entity | Options | Notes |
|--------|---------|-------|
| `select.<name>_mode` | Auto, Cool, Heat, Dry, Fanonly | `autoClean` reported as `unknown` — disabled value, not user-selectable |
| `select.<name>_fan_speed_setting` | Auto, Quiet, Low, Middle, High | Non-auto speeds rejected by API when mode=Auto |
| `select.<name>_temperature_unit` | Celsius, Fahrenheit | Changes AC display unit |

### Number

| Entity | Range | Notes |
|--------|-------|-------|
| `number.<name>_target_temperature_c` | 16–30°C | Fully functional |
| `number.<name>_target_temperature_f` | — | **Known issue**: stuck at 16°F, not synced with `_c` entity |

### Switch

| Entity | SSE | Notes |
|--------|-----|-------|
| `switch.<name>_display_light` | ✅ real-time | LED display on/off |
| `switch.<name>_vertical_swing` | ⚠️ poll-only | Works via HA/Home+; remote IR doesn't round-trip to cloud |
| `switch.<name>_horizontal_swing` | ⚠️ poll-only | Same as vertical |
| `switch.<name>_turbo_function` | ⚠️ poll-only | Same |
| `switch.<name>_energy_saving_mode` | ⚠️ poll-only | ECO button on remote = local IR only |
| `switch.<name>_clean_air_mode` | ⚠️ poll-only | Ioniser |
| `switch.<name>_sleep_mode` | ⚠️ poll-only | Actual sleep comfort mode (separate from timer) |
| `switch.<name>_flap_position_avoid_user` | ⚠️ poll-only | "Diffuse" in Home+ app |
| `switch.<name>_auto_clean_trigger` | ⚠️ poll-only | Self-clean; also sets `mode=autoClean` |

### Sensor

| Entity | Notes |
|--------|-------|
| `sensor.<name>_ambient_temperature_c` | Real-time SSE |
| `sensor.<name>_appliance_state` | Real-time SSE |
| `sensor.<name>_compressor_state` | Poll |
| `sensor.<name>_fan_speed_state` | Actual fan speed (vs setting) |
| `sensor.<name>_scheduler_mode` | Timer state (poll-only) |
| `sensor.<name>_scheduler_session` | Timer session details |
| `sensor.<name>_network_interface_rssi` | Wi-Fi signal strength |

## SSE Behaviour

Properties the Electrolux cloud pushes in real-time via SSE:

- `mode`
- `fanSpeedSetting`
- `targetTemperatureC`
- `displayLight`
- `applianceState` (triggers full state refresh)
- `ambientTemperatureC`

Properties that are **cloud-aware but SSE-silent** (updated on full poll only):

- `verticalSwing`, `horizontalSwing`
- `turboFunction`
- `energySavingMode`
- `sleepMode`
- `cleanAirMode`
- `flapPositionAvoidUser`
- `schedulerMode`, `schedulerSession`

Full poll interval: 6 hours (SSE health check). A full state refresh is also triggered on `applianceState` SSE events.

## Remote vs Cloud Behaviour

The physical remote controls some features purely via IR without reporting to the cloud:

- Swing (vertical) — remote toggles louvers locally; cloud state unchanged until next Home+ or HA command
- Turbo, ECO, self-clean — same pattern

Commands sent via **Home+ app** or **HA** always round-trip through cloud → SSE or poll picks up the change.

## Known Issues

| Issue | Details |
|-------|---------|
| `autoClean` shows `unknown` | Device enters self-clean mode (`mode=autoClean`) which is `disabled` in capability. HA shows `unknown` instead of a read-only label. |
| `target_temperature_f` stuck at 16°F | `number.<name>_target_temperature_f` not synced with `_c`. Shows default/min value. |
| Poll-only switches | Swing/turbo/eco/sleep/cleanAir not updated via SSE — state only refreshes on 6h poll or `applianceState` event. |
| Fan speed rejected in Auto mode | Sending non-Auto fan speed when mode=Auto returns `COMMAND_VALIDATION_ERROR`. Expected API behaviour. |

## Test Results

Tested 2026-05-16 against unit `956007025415068981045767` (office).

### Remote → HA (SSE)

| Action | SSE fired | HA updated |
|--------|-----------|------------|
| Mode change (heat/cool/etc.) | ✅ | ✅ |
| Fan speed change | ✅ | ✅ |
| Target temperature change | ✅ | ✅ |
| Display light toggle | ✅ | ✅ |
| Vertical swing | ❌ | ❌ (remote IR only) |
| Turbo on | ❌ | ❌ (remote IR only) |
| ECO on | ❌ | ❌ (remote IR only) |
| Power off | ✅ (`mode=OFF` — skipped correctly) | ✅ (no options pollution) |
| Self-clean | ✅ (`mode=autoClean`) | ⚠️ shows `unknown` |

### Home+ → HA

| Action | HA updated |
|--------|------------|
| Vertical swing on | ✅ (via full state refresh) |
| Horizontal swing on | ✅ (via full state refresh) |
| Turbo on | ✅ (via full state refresh) |
| ECO on | ⚠️ poll-only |
| Sleep on | ⚠️ poll-only |
| Clean air (ioniser) on | ⚠️ poll-only |
| Diffuse (flap) on | ⚠️ poll-only |

### HA → Appliance

| Command | Result |
|---------|--------|
| Mode: Cool/Heat/Dry/Fanonly/Auto | ✅ all accepted, AC responded |
| Fan speed: all 5 options | ✅ (Auto mode rejects non-Auto — correct) |
| Target temp: 18/24/30°C | ✅ AC display changed |
| Temperature unit: C/F | ✅ AC display switched |
| All switches on then off | ✅ AC responded to each |
| Power off (`hvac_mode: off`) | ✅ |
