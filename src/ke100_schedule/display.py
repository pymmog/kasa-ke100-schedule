"""Human-readable schedule formatting."""

from __future__ import annotations

from typing import Any


def format_minutes(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def format_desired_states(desired: dict[str, Any]) -> str:
    if desired.get("frost_protection_on"):
        return "frost protection"
    temp_float = desired.get("target_temp_float")
    if temp_float is not None:
        return f"{temp_float / 10:.1f} °C"
    target = desired.get("target_temp")
    return f"{target} °C" if target is not None else "?"


def format_rule_line(rule: dict[str, Any]) -> str:
    start = format_minutes(rule["start_min"])
    end = format_minutes(rule["end_min"])
    temp = format_desired_states(rule.get("desired_states") or {})
    return f"    {start}-{end}  {temp}"


def format_segment_rules(rule_list: list[dict[str, Any]]) -> list[str]:
    lines = []
    for rule in sorted(rule_list, key=lambda r: r["start_min"]):
        lines.append(format_rule_line(rule))
    return lines
