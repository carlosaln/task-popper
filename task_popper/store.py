from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Task

PAGE_SIZE = 10


def resolve_store_path(cwd: Optional[Path] = None) -> Path:
    """Resolve task store path.

    Resolution order:
      1. If a .task-popper/ directory exists in cwd (or any parent), use it
         (future: per-project task lists)
      2. Fall back to ~/.task-popper/tasks.json
    """
    # Future: walk up from cwd looking for .task-popper/
    # For now, always use global store
    home_store = Path.home() / ".task-popper" / "tasks.json"
    return home_store


class TaskStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or resolve_store_path()
        self._tasks: list[Task] = []
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self._tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
            except (json.JSONDecodeError, KeyError):
                self._tasks = []
        else:
            self._tasks = []

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"tasks": [t.to_dict() for t in self._tasks]}
        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------ #
    # Query                                                                #
    # ------------------------------------------------------------------ #

    def get_sorted(self, include_completed: bool = False) -> list[Task]:
        """Return tasks sorted by criticality score, excluding completed by default."""
        tasks = self._tasks if include_completed else [t for t in self._tasks if not t.completed]
        return sorted(tasks, key=lambda t: t.criticality_score())

    def get_page(self, page: int, include_completed: bool = False) -> list[Task]:
        tasks = self.get_sorted(include_completed)
        start = page * PAGE_SIZE
        return tasks[start : start + PAGE_SIZE]

    def page_count(self, include_completed: bool = False) -> int:
        tasks = self.get_sorted(include_completed)
        if not tasks:
            return 1
        return (len(tasks) + PAGE_SIZE - 1) // PAGE_SIZE

    def get_by_priority(self, include_completed: bool = False) -> list[Task]:
        """Return tasks sorted by priority_order only (no due date influence)."""
        tasks = self._tasks if include_completed else [t for t in self._tasks if not t.completed]
        return sorted(tasks, key=lambda t: t.priority_order)

    def get_priority_page(self, page: int, include_completed: bool = False) -> list[Task]:
        tasks = self.get_by_priority(include_completed)
        start = page * PAGE_SIZE
        return tasks[start : start + PAGE_SIZE]

    def total_active(self) -> int:
        return sum(1 for t in self._tasks if not t.completed)

    # ------------------------------------------------------------------ #
    # Mutations                                                            #
    # ------------------------------------------------------------------ #

    def add(self, task: Task) -> None:
        # Assign next priority_order
        active = self.get_sorted()
        task.priority_order = len(active)
        self._tasks.append(task)
        self.save()

    def update(self, task: Task) -> None:
        for i, t in enumerate(self._tasks):
            if t.id == task.id:
                self._tasks[i] = task
                break
        self.save()

    def delete(self, task_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.id != task_id]
        self._renumber()
        self.save()

    def complete(self, task_id: str) -> None:
        task = next((t for t in self._tasks if t.id == task_id), None)
        if task is None:
            return
        now = datetime.now(timezone.utc)
        task.completed = True
        task.completed_at = now.isoformat()
        # Remove from active list and archive
        self._tasks = [t for t in self._tasks if t.id != task_id]
        self._renumber()
        self.save()
        self._archive_task(task, now)

    def complete_chunk(self, task_id: str, chunk_minutes: int) -> bool:
        """Record partial progress on a chunked task.

        Returns True if the task is now fully complete, False if work remains.
        """
        task = next((t for t in self._tasks if t.id == task_id), None)
        if task is None:
            return False
        task.time_spent += chunk_minutes
        if task.duration is not None and task.time_spent >= task.duration:
            self.complete(task_id)
            return True
        self.save()
        return False

    def move_up(self, task_id: str) -> int:
        """Swap task with the one above it in priority order. Returns new index."""
        tasks = self.get_by_priority()
        idx = next((i for i, t in enumerate(tasks) if t.id == task_id), None)
        if idx is None or idx == 0:
            return idx or 0
        # Swap priority_orders
        tasks[idx].priority_order, tasks[idx - 1].priority_order = (
            tasks[idx - 1].priority_order,
            tasks[idx].priority_order,
        )
        self.update(tasks[idx])
        self.update(tasks[idx - 1])
        return idx - 1

    def move_down(self, task_id: str) -> int:
        """Swap task with the one below it in priority order. Returns new index."""
        tasks = self.get_by_priority()
        idx = next((i for i, t in enumerate(tasks) if t.id == task_id), None)
        if idx is None or idx >= len(tasks) - 1:
            return idx or 0
        tasks[idx].priority_order, tasks[idx + 1].priority_order = (
            tasks[idx + 1].priority_order,
            tasks[idx].priority_order,
        )
        self.update(tasks[idx])
        self.update(tasks[idx + 1])
        return idx + 1

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _archive_task(self, task: Task, completed_at: datetime) -> None:
        """Append a completed task to the weekly archive file."""
        year = completed_at.year
        week = completed_at.isocalendar()[1]
        archive_dir = self.path.parent / "archive" / str(year)
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"week-{week:02d}.json"
        if archive_path.exists():
            try:
                data = json.loads(archive_path.read_text(encoding="utf-8"))
                tasks = data.get("tasks", [])
            except (json.JSONDecodeError, KeyError):
                tasks = []
        else:
            tasks = []
        tasks.append(task.to_dict())
        archive_path.write_text(
            json.dumps({"tasks": tasks}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _renumber(self) -> None:
        """Re-assign contiguous priority_orders after deletion."""
        active = sorted(
            (t for t in self._tasks if not t.completed),
            key=lambda t: t.priority_order,
        )
        for i, task in enumerate(active):
            task.priority_order = i
