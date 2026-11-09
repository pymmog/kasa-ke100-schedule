"""Apply validated schedule specs to a room."""

from __future__ import annotations

import json
from typing import Any

from ke100_schedule.display import format_minutes
from ke100_schedule.hub import HubLike, control_child, fetch_schedule_rules, get_sc_schedule_info
from ke100_schedule.segments import SEGMENTS_BY_MODE, ScheduleMode
from ke100_schedule.spec import Request, validate_spec


def find_child_by_alias(hub: HubLike, room: str):
    matches = [c for c in hub.children if c.alias == room]
    if not matches:
        names = [c.alias for c in hub.children]
        raise SystemExit(f"Room {room!r} not found. Children: {names}")
    return matches[0]


def summarize_rules(rule_list: list[dict[str, Any]]) -> list[tuple[int, int, Any]]:
    return [
        (
            r["start_min"],
            r["end_min"],
            (r.get("desired_states") or {}).get("target_temp_float"),
        )
        for r in sorted(rule_list, key=lambda x: x["start_min"])
    ]


async def dry_run_or_apply(
    hub: HubLike,
    child_id: str,
    requests: list[Request],
    *,
    apply: bool,
) -> list[Any]:
    results: list[Any] = []
    for method, params in requests:
        print(f"\n>>> control_child device_id={child_id} method={method}")
        print(json.dumps(params, ensure_ascii=False, indent=2))
        if apply:
            result = await control_child(hub, child_id, method, params)
            print("RESULT:", result)
            results.append(result)
    if not apply:
        print("\nDRY-RUN – nothing sent. Re-run with --apply to send.")
    return results


async def write_schedule(
    hub: HubLike,
    spec: dict[str, Any],
    *,
    apply: bool,
) -> list[Request]:
    requests = validate_spec(spec)
    print(f"VALIDATION: OK – {len(requests)} request(s)")

    child = find_child_by_alias(hub, spec["room"])
    info = await get_sc_schedule_info(hub, child.device_id)
    print("CURRENT info:", info)

    mode: ScheduleMode = spec["mode"]  # type: ignore[assignment]
    try:
        existing = await fetch_schedule_rules(hub, child.device_id, mode)
        print(f"CURRENT stored {mode} segments: {[s['id'] for s in existing]}")
        for segment in existing:
            rules = summarize_rules(segment.get("rule_list") or [])
            print(f"  {segment['id']}", rules)
    except Exception as exc:
        print(f"CURRENT stored segments for target mode: n/a – {exc}")

    await dry_run_or_apply(hub, child.device_id, requests, apply=apply)
    return requests


def format_before_after(
    before: list[dict[str, Any]],
    after_segments: dict[str, list[list[Any]]],
    mode: ScheduleMode,
) -> str:
    """Readable per-segment before/after for agent dry-runs."""
    lines: list[str] = []
    before_by_id = {s["id"]: s for s in before}
    for seg in SEGMENTS_BY_MODE[mode]:
        seg_id = f"{mode}:{seg}"
        lines.append(f"=== {seg} ===")
        if seg_id in before_by_id:
            lines.append("Before:")
            for rule in sorted(
                before_by_id[seg_id].get("rule_list") or [],
                key=lambda r: r["start_min"],
            ):
                lines.append(
                    f"  {format_minutes(rule['start_min'])}-"
                    f"{format_minutes(rule['end_min'])}"
                )
        else:
            lines.append("Before: (no stored segment)")
        lines.append("After (spec):")
        for block in after_segments.get(seg, []):
            lines.append(f"  {block[0]}-{block[1]}  {block[2]}")
    return "\n".join(lines)
