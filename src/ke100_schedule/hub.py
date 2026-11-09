"""KH100 hub connection and control_child helpers."""

from __future__ import annotations

from typing import Any, Protocol

from kasa import Credentials, Discover

from ke100_schedule.config import HubCredentials
from ke100_schedule.segments import ScheduleMode


class ChildLike(Protocol):
    device_id: str
    alias: str


class HubLike(Protocol):
    children: list[ChildLike]

    async def update(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def _query_helper(self, method: str, params: dict[str, Any]) -> dict[str, Any]: ...


async def connect(creds: HubCredentials) -> HubLike:
    device = await Discover.discover_single(
        creds.host,
        credentials=Credentials(creds.username, creds.password),
    )
    await device.update()
    return device  # type: ignore[return-value]


async def control_child(
    hub: HubLike,
    child_id: str,
    method: str,
    params: dict[str, Any] | None = None,
) -> Any:
    request_data: dict[str, Any] = {"method": method}
    if params is not None:
        request_data["params"] = params
    response = (
        await hub._query_helper(
            "control_child",
            {"device_id": child_id, "requestData": request_data},
        )
    )["control_child"]["responseData"]
    if response.get("error_code") != 0:
        raise RuntimeError(f"{method} {params}: error {response.get('error_code')}")
    return response.get("result")


async def get_sc_schedule_info(hub: HubLike, child_id: str) -> dict[str, Any]:
    result = await control_child(hub, child_id, "get_sc_schedule_info")
    assert isinstance(result, dict)
    return result


async def fetch_schedule_rules(
    hub: HubLike,
    child_id: str,
    mode: ScheduleMode,
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    start_index = 0
    while True:
        result = await control_child(
            hub,
            child_id,
            "get_sc_schedule_rules",
            {"schedule_mode": mode, "start_index": start_index},
        )
        batch = result.get("schedule_list") or []
        collected.extend(batch)
        start_index = len(collected)
        total = result.get("sum", 0)
        if start_index >= total or not batch:
            return collected
    return collected  # pragma: no cover
