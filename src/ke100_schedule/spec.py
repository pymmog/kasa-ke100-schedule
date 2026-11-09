"""Validate schedule JSON specs and build hub request payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ke100_schedule.segments import SEGMENTS_BY_MODE, ScheduleMode

Request = tuple[str, dict[str, Any]]

Block = tuple[str, str, float | str]  # start HH:MM, end HH:MM, temp or "frost"


def parse_time_minutes(label: str) -> int:
    hour_str, min_str = label.split(":")
    hour, minute = int(hour_str), int(min_str)
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError(f"Invalid time: {label}")
    return hour * 60 + minute


def format_time_minutes(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def desired_states_for_temp(temp: float | str) -> dict[str, Any]:
    if temp == "frost":
        return {"frost_protection_on": True, "temp_unit": "celsius"}
    value = float(temp)
    if not 5 <= value <= 30:
        raise ValueError(f"Temperature {value} out of range 5..30 °C")
    return {
        "target_temp": int(value),
        "target_temp_float": int(round(value * 10)),
        "frost_protection_on": False,
        "temp_unit": "celsius",
    }


def build_rule_list(blocks: list[Block], segment: str) -> list[dict[str, Any]]:
    rule_list: list[dict[str, Any]] = []
    prev_end = -1
    for start_s, end_s, temp in blocks:
        start_min = parse_time_minutes(start_s)
        end_min = parse_time_minutes(end_s)
        if start_min != prev_end + 1:
            raise ValueError(
                f"{segment}: gap or overlap before {start_s} (previous end minute {prev_end})"
            )
        if end_min < start_min:
            raise ValueError(f"{segment}: end before start {start_s}-{end_s}")
        prev_end = end_min
        rule_list.append(
            {
                "start_min": start_min,
                "end_min": end_min,
                "desired_states": desired_states_for_temp(temp),
            }
        )
    if prev_end != 1439:
        raise ValueError(f"{segment}: schedule must end at 23:59 (ends at minute {prev_end})")
    return rule_list


def validate_spec(spec: dict[str, Any]) -> list[Request]:
    mode = spec.get("mode")
    if mode not in SEGMENTS_BY_MODE:
        raise ValueError(f"mode must be one of {list(SEGMENTS_BY_MODE)}")
    mode_typed: ScheduleMode = mode  # type: ignore[assignment]

    expected = set(SEGMENTS_BY_MODE[mode_typed])
    segments = spec.get("segments")
    if not isinstance(segments, dict):
        raise ValueError("segments must be an object")
    if set(segments.keys()) != expected:
        raise ValueError(f"segments must be exactly {SEGMENTS_BY_MODE[mode_typed]}")

    enable = bool(spec.get("enable", True))
    requests: list[Request] = [
        ("set_sc_schedule_info", {"enable": enable, "mode": mode_typed}),
    ]
    for seg in SEGMENTS_BY_MODE[mode_typed]:
        raw_blocks = segments[seg]
        if not isinstance(raw_blocks, list):
            raise ValueError(f"{seg}: blocks must be a list")
        blocks: list[Block] = []
        for row in raw_blocks:
            if not isinstance(row, (list, tuple)) or len(row) != 3:
                raise ValueError(f"{seg}: each block is [start, end, temp]")
            blocks.append((str(row[0]), str(row[1]), row[2]))  # type: ignore[arg-type]
        rule_list = build_rule_list(blocks, seg)
        requests.append(
            (
                "edit_sc_schedule_rule",
                {
                    "schedule_mode": mode_typed,
                    "id": f"{mode_typed}:{seg}",
                    "rule_list": rule_list,
                },
            )
        )
    return requests


def load_spec(path: Path | str) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def rule_list_to_blocks(rule_list: list[dict[str, Any]]) -> list[list[Any]]:
    """Convert device rule_list to spec-style blocks for display or merging."""
    blocks: list[list[Any]] = []
    for rule in sorted(rule_list, key=lambda r: r["start_min"]):
        ds = rule.get("desired_states") or {}
        if ds.get("frost_protection_on"):
            temp: float | str = "frost"
        else:
            tf = ds.get("target_temp_float")
            temp = (tf / 10.0) if tf is not None else float(ds.get("target_temp", 0))
        blocks.append(
            [
                format_time_minutes(rule["start_min"]),
                format_time_minutes(rule["end_min"]),
                temp,
            ]
        )
    return blocks
