"""Spec validation and expand helper tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ke100_schedule.expand import expand_warm_blocks
from ke100_schedule.spec import build_rule_list, load_spec, validate_spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.mark.parametrize(
    "name",
    ["everyday.json", "weekday_sat_sun.json", "single_day.json"],
)
def test_example_specs_validate(name: str) -> None:
    spec = load_spec(EXAMPLES / name)
    reqs = validate_spec(spec)
    assert reqs[0][0] == "set_sc_schedule_info"
    assert all(r[0] == "edit_sc_schedule_rule" for r in reqs[1:])


def test_set_sc_schedule_info_first() -> None:
    spec = load_spec(EXAMPLES / "everyday.json")
    reqs = validate_spec(spec)
    method, params = reqs[0]
    assert method == "set_sc_schedule_info"
    assert params == {"enable": True, "mode": "everyday"}


def test_edit_rule_ids_and_mode() -> None:
    spec = load_spec(EXAMPLES / "weekday_sat_sun.json")
    reqs = validate_spec(spec)
    ids = [r[1]["id"] for r in reqs[1:]]
    assert ids == [
        "weekday_sat_sun:weekday",
        "weekday_sat_sun:saturday",
        "weekday_sat_sun:sunday",
    ]
    for _, params in reqs[1:]:
        assert params["schedule_mode"] == "weekday_sat_sun"


def test_target_temp_float() -> None:
    rules = build_rule_list([["00:00", "23:59", 21.5]], "everyday")
    ds = rules[0]["desired_states"]
    assert ds["target_temp_float"] == 215
    assert ds["frost_protection_on"] is False


def test_frost_protection() -> None:
    rules = build_rule_list([["00:00", "23:59", "frost"]], "everyday")
    assert rules[0]["desired_states"]["frost_protection_on"] is True


def test_gap_rejected() -> None:
    with pytest.raises(ValueError, match="gap"):
        build_rule_list(
            [["00:00", "10:00", 18.0], ["10:02", "23:59", 18.0]],
            "everyday",
        )


def test_must_end_2359() -> None:
    with pytest.raises(ValueError, match="23:59"):
        build_rule_list([["00:00", "23:58", 18.0]], "everyday")


def test_wrong_segments_for_mode() -> None:
    spec = json.loads((EXAMPLES / "everyday.json").read_text())
    spec["segments"] = {"weekday": [["00:00", "23:59", 18.0]]}
    with pytest.raises(ValueError, match="segments must be exactly"):
        validate_spec(spec)


def test_expand_warm_blocks() -> None:
    warm = [("06:30", "08:29", 21.0), ("17:00", "21:59", 21.5)]
    full = expand_warm_blocks(warm, 16.0)
    assert full[0] == ("00:00", "06:29", 16.0)
    assert full[1] == ("06:30", "08:29", 21.0)
    assert full[-1] == ("22:00", "23:59", 16.0)
    build_rule_list(full, "everyday")  # must cover full day


def test_temp_out_of_range() -> None:
    with pytest.raises(ValueError, match="5..30"):
        build_rule_list([["00:00", "23:59", 4.0]], "everyday")
