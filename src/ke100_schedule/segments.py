"""Schedule mode and day-segment definitions."""

from typing import Literal

ScheduleMode = Literal["everyday", "weekday_sat_sun", "single_day"]

SEGMENTS_BY_MODE: dict[ScheduleMode, list[str]] = {
    "everyday": ["everyday"],
    "weekday_sat_sun": ["weekday", "saturday", "sunday"],
    "single_day": [
        "sunday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
    ],
}

DAY_ORDER = [
    "sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
]
