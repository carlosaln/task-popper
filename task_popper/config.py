from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path

ACTIVE_CONFIG_PATH = Path.home() / ".task-popper" / "schedule.json"
DEFAULT_CONFIG_PATH = Path.home() / ".task-popper" / "schedule_default.json"


def _parse_time(s: str) -> time:
    """Parse a 'HH:MM' string into a datetime.time object."""
    h, m = s.split(":")
    return time(int(h), int(m))


@dataclass
class TimeBlock:
    start: time
    end: time
    label: str = ""


_DAY_NAMES = {
    "mon": 0, "monday": 0,
    "tue": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}

_DAY_ABBREVS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_preferred_days(text: str) -> list[int]:
    """Parse a day spec string into a sorted list of weekday ints (0=Mon…6=Sun).

    Accepts: "weekdays", "weekends", "all", blank, or comma-separated day names
    e.g. "mon,wed,fri" or "sat,sun".
    """
    t = text.strip().lower()
    if not t or t == "all":
        return []
    if t == "weekdays":
        return [0, 1, 2, 3, 4]
    if t == "weekends":
        return [5, 6]
    days: list[int] = []
    for part in t.split(","):
        part = part.strip()
        if part in _DAY_NAMES:
            d = _DAY_NAMES[part]
            if d not in days:
                days.append(d)
    return sorted(days)


def fmt_preferred_days(days: list[int]) -> str:
    """Format a list of weekday ints back to a human-readable string."""
    if not days:
        return "any day"
    if days == [0, 1, 2, 3, 4]:
        return "weekdays"
    if days == [5, 6]:
        return "weekends"
    return ",".join(_DAY_ABBREVS[d] for d in sorted(days))


@dataclass
class TagPreference:
    tag: str                              # the tag name (without #)
    preferred_burn_mode: str = "normal"   # "normal" or "low_burn"
    preferred_times: list[TimeBlock] = field(default_factory=list)
    preferred_days: list[int] = field(default_factory=list)  # 0=Mon…6=Sun, empty=any


@dataclass
class ScheduleConfig:
    work_start: time = field(default_factory=lambda: time(7, 0))
    work_end: time = field(default_factory=lambda: time(18, 0))
    extended_end: time | None = None          # None = no extended day
    break_percent: int = 15                   # % of task duration for breaks
    short_task_threshold: int = 15            # minutes; tasks ≤ this are bunched
    min_chunk_duration: int = 30             # minimum work session for partial chunks of long tasks
    max_chunk_duration: int = 120            # max continuous work minutes (caps both bunches and long-task chunks)
    low_priority_threshold: float = 0.6      # top N% are normal, rest are low-priority
    blocked: list[TimeBlock] = field(default_factory=list)
    low_burn: list[TimeBlock] = field(default_factory=list)
    tag_preferences: list[TagPreference] = field(default_factory=list)


def _config_to_dict(config: ScheduleConfig) -> dict:
    return {
        "work_start": config.work_start.strftime("%H:%M"),
        "work_end": config.work_end.strftime("%H:%M"),
        "extended_end": config.extended_end.strftime("%H:%M") if config.extended_end else None,
        "break_percent": config.break_percent,
        "short_task_threshold": config.short_task_threshold,
        "min_chunk_duration": config.min_chunk_duration,
        "max_chunk_duration": config.max_chunk_duration,
        "low_priority_threshold": config.low_priority_threshold,
        "blocked": [
            {"start": b.start.strftime("%H:%M"), "end": b.end.strftime("%H:%M"), "label": b.label}
            for b in config.blocked
        ],
        "low_burn": [
            {"start": lb.start.strftime("%H:%M"), "end": lb.end.strftime("%H:%M"), "label": lb.label}
            for lb in config.low_burn
        ],
        "tag_preferences": [
            {
                "tag": tp.tag,
                "preferred_burn_mode": tp.preferred_burn_mode,
                "preferred_days": tp.preferred_days,
                "preferred_times": [
                    {"start": pt.start.strftime("%H:%M"), "end": pt.end.strftime("%H:%M"), "label": pt.label}
                    for pt in tp.preferred_times
                ],
            }
            for tp in config.tag_preferences
        ],
    }


def save_schedule_config(config: ScheduleConfig, path: Path | None = None) -> None:
    """Save a ScheduleConfig to the given path (defaults to the active config path)."""
    if path is None:
        path = ACTIVE_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(_config_to_dict(config), f, indent=2)


def load_schedule_config(path: Path | None = None) -> ScheduleConfig:
    """Load schedule config from ~/.task-popper/schedule.json, falling back to defaults."""
    if path is None:
        path = ACTIVE_CONFIG_PATH

    if not path.exists():
        return ScheduleConfig()

    with path.open() as f:
        data = json.load(f)

    extended_end_raw = data.get("extended_end")
    blocked = [
        TimeBlock(
            start=_parse_time(b["start"]),
            end=_parse_time(b["end"]),
            label=b.get("label", ""),
        )
        for b in data.get("blocked", [])
    ]
    low_burn = [
        TimeBlock(
            start=_parse_time(lb["start"]),
            end=_parse_time(lb["end"]),
            label=lb.get("label", ""),
        )
        for lb in data.get("low_burn", [])
    ]

    tag_preferences = [
        TagPreference(
            tag=tp["tag"],
            preferred_burn_mode=tp.get("preferred_burn_mode", "normal"),
            preferred_days=tp.get("preferred_days", []),
            preferred_times=[
                TimeBlock(start=_parse_time(pt["start"]), end=_parse_time(pt["end"]), label=pt.get("label", ""))
                for pt in tp.get("preferred_times", [])
            ],
        )
        for tp in data.get("tag_preferences", [])
    ]

    return ScheduleConfig(
        work_start=_parse_time(data.get("work_start", "07:00")),
        work_end=_parse_time(data.get("work_end", "18:00")),
        extended_end=_parse_time(extended_end_raw) if extended_end_raw else None,
        break_percent=int(data.get("break_percent", 15)),
        short_task_threshold=int(data.get("short_task_threshold", 15)),
        min_chunk_duration=int(data.get("min_chunk_duration", 30)),
        # Migrate: old configs may have max_bunch_duration instead of max_chunk_duration
        max_chunk_duration=int(data.get("max_chunk_duration", data.get("max_bunch_duration", 120))),
        low_priority_threshold=float(data.get("low_priority_threshold", 0.6)),
        blocked=blocked,
        low_burn=low_burn,
        tag_preferences=tag_preferences,
    )
