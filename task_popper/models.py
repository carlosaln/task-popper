from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Task:
    title: str
    id: str = field(default_factory=_new_id)
    description: str = ""
    priority_order: int = 0  # lower index = higher priority
    due_date: Optional[str] = (
        None  # ISO 8601 date or datetime string, e.g. "2025-12-31" or "2025-12-31T14:30"
    )
    start_date: Optional[str] = (
        None  # not-before constraint: "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM"
    )
    duration: Optional[int] = None  # duration in minutes, parsed from title suffix
    time_spent: int = 0  # minutes of work already completed (for chunked progress)
    due_time: Optional[str] = (
        None  # HH:MM — pinned start time for today's schedule; task starts exactly at this time
    )
    tags: list[str] = field(default_factory=list)
    completed: bool = False
    completed_at: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    # Reserved for future use:
    # parent_id: Optional[str] = None
    # dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority_order": self.priority_order,
            "due_date": self.due_date,
            "start_date": self.start_date,
            "duration": self.duration,
            "time_spent": self.time_spent,
            "due_time": self.due_time,
            "tags": self.tags,
            "completed": self.completed,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        return cls(
            id=data.get("id", _new_id()),
            title=data["title"],
            description=data.get("description", ""),
            priority_order=data.get("priority_order", 0),
            due_date=data.get("due_date"),
            start_date=data.get("start_date"),
            duration=data.get("duration"),
            time_spent=data.get("time_spent", 0),
            due_time=data.get("due_time"),
            tags=data.get("tags", []),
            completed=data.get("completed", False),
            completed_at=data.get("completed_at"),
            created_at=data.get("created_at", _now_iso()),
        )

    def criticality_score(self) -> float:
        """Lower score = higher criticality (more urgent/important).

        Currently only uses priority_order. When due_date is implemented,
        blend urgency (days until due) with expressed priority.
        """
        due_score = 0.0
        if self.due_date:
            try:
                due_dt = datetime.fromisoformat(self.due_date)
                # Treat date-only strings as naive local midnight
                if due_dt.tzinfo is None:
                    now = datetime.now()
                else:
                    now = datetime.now(timezone.utc)
                days_until = (due_dt - now).total_seconds() / 86400
                # Overdue tasks get a large negative bonus (more critical)
                # Tasks due soon get a smaller negative bonus
                # Cap at ±365 days for stability
                days_clamped = max(-365.0, min(365.0, days_until))
                due_score = days_clamped * 0.5  # weight relative to priority
            except ValueError:
                pass

        # priority_order: 0 = top of list = most critical
        return self.priority_order + due_score
