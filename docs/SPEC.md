# Schedule spec format

Files passed to `ke100-schedule write`. JSON object:

| Field | Required | Description |
|-------|----------|-------------|
| `room` | yes | Child alias on the KH100 (see `ke100-schedule list`) |
| `mode` | yes | `everyday`, `weekday_sat_sun`, or `single_day` |
| `enable` | no | Default `true`; sent in `set_sc_schedule_info` |
| `segments` | yes | Map of segment name → list of time blocks |

## Blocks

Each block is `[start, end, target]`:

- **start / end** — `HH:MM` 24-hour, **inclusive** end minute
- **target** — number (°C, 5–30, 0.5 steps) or `"frost"`

Rules:

1. Blocks must be contiguous: first block starts at `00:00`, each next block starts at previous end + 1 minute.
2. Last block must end at `23:59` (minute index 1439).
3. `segments` keys must match the chosen mode exactly.

## Modes and keys

See [README.md](../README.md#schedule-spec) and [examples/](../examples/).

## Write order on device

1. `set_sc_schedule_info` with `{ enable, mode }`
2. For each segment: `edit_sc_schedule_rule` with `id` `"<mode>:<segment>"` and full `rule_list`

The CLI builds `rule_list` with `target_temp_float = °C × 10` automatically.
