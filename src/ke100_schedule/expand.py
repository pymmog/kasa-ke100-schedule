"""Expand 'warm blocks only' into a full-day contiguous spec segment."""

from __future__ import annotations

from ke100_schedule.spec import Block, format_time_minutes, parse_time_minutes


def expand_warm_blocks(
    warm_blocks: list[tuple[str, str, float]],
    default_temp: float,
) -> list[Block]:
    """
    Given only heated intervals (start, end inclusive in HH:MM), fill gaps with default_temp.

    End times for warm blocks are the last minute of warmth (inclusive), matching full spec rules.
    Gaps run from (previous_end + 1) through (next_start - 1) at default_temp.
    """
    if not warm_blocks:
        raise ValueError("warm_blocks must not be empty")

    sorted_blocks = sorted(warm_blocks, key=lambda b: parse_time_minutes(b[0]))
    full: list[Block] = []
    cursor = 0  # next minute that must be covered (0 = day start)

    for start_s, end_s, temp in sorted_blocks:
        start = parse_time_minutes(start_s)
        end = parse_time_minutes(end_s)
        if end < start:
            raise ValueError(f"end before start: {start_s}-{end_s}")
        if start > cursor:
            gap_end = start - 1
            if gap_end >= cursor:
                full.append(
                    (
                        format_time_minutes(cursor),
                        format_time_minutes(gap_end),
                        default_temp,
                    )
                )
            cursor = start
        if start != cursor:
            raise ValueError(f"overlap or gap at {start_s} (expected start minute {cursor})")
        full.append((start_s, end_s, temp))
        cursor = end + 1

    if cursor <= 1439:
        full.append((format_time_minutes(cursor), "23:59", default_temp))
    elif cursor != 1440:
        raise ValueError("warm blocks extend past end of day")

    return full
