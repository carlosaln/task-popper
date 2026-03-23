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


@dataclass
class ScheduleConfig:
    work_start: time = field(default_factory=lambda: time(7, 0))
    work_end: time = field(default_factory=lambda: time(18, 0))
    extended_end: time | None = None          # None = no extended day
    break_percent: int = 15                   # % of task duration for breaks
    short_task_threshold: int = 15            # minutes; tasks ≤ this are bunched
    max_bunch_duration: int = 120            # max minutes for a single short-task bunch
    low_priority_threshold: float = 0.6      # top N% are normal, rest are low-priority
    blocked: list[TimeBlock] = field(default_factory=list)
    low_burn: list[TimeBlock] = field(default_factory=list)


def _config_to_dict(config: ScheduleConfig) -> dict:
    return {
        "work_start": config.work_start.strftime("%H:%M"),
        "work_end": config.work_end.strftime("%H:%M"),
        "extended_end": config.extended_end.strftime("%H:%M") if config.extended_end else None,
        "break_percent": config.break_percent,
        "short_task_threshold": config.short_task_threshold,
        "max_bunch_duration": config.max_bunch_duration,
        "low_priority_threshold": config.low_priority_threshold,
        "blocked": [
            {"start": b.start.strftime("%H:%M"), "end": b.end.strftime("%H:%M"), "label": b.label}
            for b in config.blocked
        ],
        "low_burn": [
            {"start": lb.start.strftime("%H:%M"), "end": lb.end.strftime("%H:%M"), "label": lb.label}
            for lb in config.low_burn
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

    return ScheduleConfig(
        work_start=_parse_time(data.get("work_start", "07:00")),
        work_end=_parse_time(data.get("work_end", "18:00")),
        extended_end=_parse_time(extended_end_raw) if extended_end_raw else None,
        break_percent=int(data.get("break_percent", 15)),
        short_task_threshold=int(data.get("short_task_threshold", 15)),
        max_bunch_duration=int(data.get("max_bunch_duration", 120)),
        low_priority_threshold=float(data.get("low_priority_threshold", 0.6)),
        blocked=blocked,
        low_burn=low_burn,
    )
