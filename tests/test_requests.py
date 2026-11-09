"""Request generation and mocked hub behaviour."""

from __future__ import annotations

from typing import Any

import pytest

from ke100_schedule.hub import control_child, fetch_schedule_rules
from ke100_schedule.spec import load_spec, validate_spec

EXAMPLE = load_spec("examples/everyday.json")

FAKE_CHILD_ID = "0000000000000000000000000000000000000001"


class MockHub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.children: list[Any] = []

    async def _query_helper(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((method, params))
        if method != "control_child":
            raise RuntimeError(method)
        rq = params["requestData"]
        m = rq["method"]
        p = rq.get("params")
        if m == "get_sc_schedule_rules":
            return {
                "control_child": {
                    "responseData": {
                        "error_code": 0,
                        "result": {
                            "schedule_mode": p["schedule_mode"],
                            "start_index": p["start_index"],
                            "sum": 1,
                            "schedule_list": [
                                {
                                    "id": f"{p['schedule_mode']}:everyday",
                                    "rule_list": [
                                        {
                                            "start_min": 0,
                                            "end_min": 1439,
                                            "desired_states": {"target_temp_float": 180},
                                        }
                                    ],
                                }
                            ]
                            if p["start_index"] == 0
                            else [],
                        },
                    }
                }
            }
        return {
            "control_child": {
                "responseData": {"error_code": 0, "result": {"ok": True}},
            }
        }

    async def update(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass


@pytest.mark.asyncio
async def test_control_child_error_code() -> None:
    hub = MockHub()

    async def fail_helper(method: str, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "control_child": {
                "responseData": {"error_code": -1008, "result": None},
            }
        }

    hub._query_helper = fail_helper  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="-1008"):
        await control_child(hub, FAKE_CHILD_ID, "get_sc_schedule_info")


@pytest.mark.asyncio
async def test_paging_stops_at_sum() -> None:
    hub = MockHub()
    pages = await fetch_schedule_rules(hub, FAKE_CHILD_ID, "everyday")
    assert len(pages) == 1
    assert hub.calls[0][1]["requestData"]["params"]["start_index"] == 0


def test_request_payload_shape() -> None:
    reqs = validate_spec(EXAMPLE)
    assert len(reqs) == 2
    edit = reqs[1][1]
    assert edit["schedule_mode"] == "everyday"
    assert edit["id"] == "everyday:everyday"
    rule = edit["rule_list"][0]
    assert rule["start_min"] == 0
    assert rule["end_min"] == 6 * 60 + 29
    assert rule["desired_states"]["target_temp_float"] == 160
