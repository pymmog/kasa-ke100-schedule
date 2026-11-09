# Agent guide: KE100 Smart Control schedules

This repository is a **community tool** for reading and writing Tapo KE100 heating schedules through a KH100 hub. It is **not** affiliated with TP-Link. Use only the documented `control_child` schedule methods.

## Safe change recipe

1. **Reachability** — Confirm the hub answers (e.g. `ke100-schedule list`). Do not proceed if discovery fails; report the error and stop (no blind retries).
2. **Read current state** — `ke100-schedule read --room "<alias>"`. **Keep the room’s existing `mode`** unless the human explicitly asks to change it.
3. **Build the spec** — Edit only what the human requested. Unchanged time blocks must match the read output exactly (times and temperatures). Use `ke100-schedule expand-warm` when the human gives warm blocks only; fill gaps with the agreed default temperature (end = minute before the next start).
4. **Dry-run** — `ke100-schedule write SPEC.json` (no `--apply`). Show a readable before/after per day/segment.
5. **Human approval** — Apply **only** after the human explicitly approves **that exact** dry-run output.
6. **Apply once** — `ke100-schedule write SPEC.json --apply`. Run once; do not loop or auto-retry on errors.
7. **Verify** — Read back and confirm every segment’s `rule_list` matches the spec. Report any mismatch and stop.

## Hard rules

- **One room per apply** unless the human names several rooms (then one spec/apply per room, still with approval each time).
- **Never** call hub methods other than `get_sc_schedule_info`, `get_sc_schedule_rules`, `set_sc_schedule_info`, and `edit_sc_schedule_rule` for schedule work.
- **Never** hand-craft `control_child` payloads outside `ke100_schedule.spec.validate_spec` / the CLI.
- **Never** read, print, copy, or commit credential files or `KASA_PASSWORD`. Do not log passwords.
- **On error:** stop, report clearly, no blind retries. **Three failures** on the same task → stop and ask the human.
- **No personal data** in commits (real IPs, emails, device IDs). Use placeholders from `examples/` and `config.example.toml`.

## Protocol invariants

- Write order: `set_sc_schedule_info` first, then one `edit_sc_schedule_rule` per segment.
- Paging: `get_sc_schedule_rules` with increasing `start_index` until `sum`.
- `end_min` is inclusive; full day `00:00`–`23:59`; `target_temp_float = °C × 10`; temps 5–30 °C or frost.

See `docs/PROTOCOL.md` and `skills/ke100-schedule/SKILL.md`.
