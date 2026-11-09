"""Read schedules from the hub."""

from __future__ import annotations

from typing import Any

from ke100_schedule.hub import HubLike, fetch_schedule_rules, get_sc_schedule_info


async def read_room_schedule(
    hub: HubLike,
    child_id: str,
    alias: str,
) -> dict[str, Any]:
    info = await get_sc_schedule_info(hub, child_id)
    mode = info.get("mode")
    schedule_list: list[dict[str, Any]] = []
    if mode in ("everyday", "weekday_sat_sun", "single_day"):
        schedule_list = await fetch_schedule_rules(hub, child_id, mode)  # type: ignore[arg-type]
    return {
        "alias": alias,
        "device_id": child_id,
        "info": info,
        "schedule_list": schedule_list,
    }


async def read_all_children(hub: HubLike) -> dict[str, dict[str, Any]]:
    dump: dict[str, dict[str, Any]] = {}
    for child in hub.children:
        try:
            dump[child.alias] = await read_room_schedule(hub, child.device_id, child.alias)
        except Exception as exc:
            dump[child.alias] = {
                "alias": child.alias,
                "device_id": child.device_id,
                "error": str(exc),
            }
    return dump
