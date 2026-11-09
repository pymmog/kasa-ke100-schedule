---
name: ke100-schedule
description: Safely read and write Tapo KE100 Smart Control heating schedules via a KH100 hub using the ke100-schedule CLI and python-kasa. Use for schedule inspection, dry-runs, approved applies, and spec building.
---

# ke100-schedule skill

## When to use

- User wants to view or change KE100 **Smart Control** (not legacy) schedules behind a KH100 hub.
- User provides room alias, times, and target temperatures.

## Prerequisites

- Credentials via `KASA_HOST`, `KASA_USERNAME`, `KASA_PASSWORD` or `~/.config/ke100-schedule/config.toml` (see `config.example.toml`).
- Package installed: `pip install git+https://github.com/pymmog/kasa-ke100-schedule.git` (or editable from a clone).

## Commands

| Action | Command |
|--------|---------|
| List children | `ke100-schedule list` |
| Read all / one room | `ke100-schedule read` / `ke100-schedule read --room "Living Room"` |
| Dry-run write | `ke100-schedule write examples/everyday.json` |
| Apply write | `ke100-schedule write SPEC.json --apply` |
| Expand warm blocks | `ke100-schedule expand-warm examples/warm_blocks_input.json` |

## Workflow (mandatory)

1. `ke100-schedule list` — hub reachable.
2. `ke100-schedule read --room "<alias>"` — capture `mode` and all segments.
3. Build `SPEC.json` with `"room"`, same `mode`, full `segments` for that mode. Preserve untouched blocks exactly.
4. `ke100-schedule write SPEC.json` — show before/after; **no `--apply` yet**.
5. After explicit human yes → `ke100-schedule write SPEC.json --apply` once.
6. `ke100-schedule read --room "<alias>"` — verify every segment.

## Stop conditions

- Missing credentials, hub not found, `error_code` from device, validation failure, or verify mismatch → report and stop (max 3 attempts per task).
- Never expose passwords; never edit credential files unless the user asks you to create their local config.

## Spec shape

```json
{
  "room": "Living Room",
  "enable": true,
  "mode": "everyday",
  "segments": {
    "everyday": [["00:00", "06:29", 16.0], ["06:30", "23:59", 20.0]]
  }
}
```

Block format: `["HH:MM", "HH:MM", temperature_celsius | "frost"]`. Last block must end at `23:59`.

Modes and segment keys: see `docs/PROTOCOL.md` and `examples/`.

## References

- `AGENTS.md` — full agent rules
- `docs/PROTOCOL.md` — hub method details
