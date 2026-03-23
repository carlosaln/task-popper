from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from .config import ScheduleConfig, TimeBlock
from .models import Task


@dataclass
class ScheduleSlot:
    start: datetime
    end: datetime
    slot_type: str          # "task" | "break" | "blocked" | "gap"
    task: Task | None = None
    group: list[Task] = field(default_factory=list)   # for short-task bunches
    label: str = ""


# ---------------------------------------------------------------------------
# Internal interval helpers
# ---------------------------------------------------------------------------

def _to_dt(t: time, today: date) -> datetime:
    return datetime.combine(today, t)


def _subtract_blocked(
    intervals: list[tuple[datetime, datetime, str]],
    blocked: list[TimeBlock],
    today: date,
) -> list[tuple[datetime, datetime, str]]:
    """Punch blocked periods out of a list of (start, end, tag) intervals."""
    result: list[tuple[datetime, datetime, str]] = []
    for iv_start, iv_end, tag in intervals:
        pieces = [(iv_start, iv_end)]
        for blk in blocked:
            blk_start = _to_dt(blk.start, today)
            blk_end = _to_dt(blk.end, today)
            new_pieces = []
            for ps, pe in pieces:
                if blk_end <= ps or blk_start >= pe:
                    # No overlap
                    new_pieces.append((ps, pe))
                else:
                    if ps < blk_start:
                        new_pieces.append((ps, blk_start))
                    if blk_end < pe:
                        new_pieces.append((blk_end, pe))
            pieces = new_pieces
        for ps, pe in pieces:
            if ps < pe:
                result.append((ps, pe, tag))
    return result


def _tag_intervals(
    work_start: datetime,
    day_end: datetime,
    work_end: datetime,
    low_burn_blocks: list[TimeBlock],
    today: date,
) -> list[tuple[datetime, datetime, str]]:
    """
    Build the raw (pre-blocked) set of scheduleable intervals tagged normal/low_burn.

    - work_start → work_end: normal
    - work_end → day_end: low_burn by default (if day_end > work_end)
    - Any explicit low_burn blocks within work_start → work_end are split out as low_burn
    """
    # Start with the full day window as normal
    intervals: list[tuple[datetime, datetime, str]] = [(work_start, day_end, "normal")]

    # Tag explicit low_burn ranges only — no implicit low-burn for extended periods
    low_burn_ranges = list(low_burn_blocks)

    for lb in low_burn_ranges:
        lb_start = _to_dt(lb.start, today)
        lb_end = _to_dt(lb.end, today)
        # Clamp to the day window
        lb_start = max(lb_start, work_start)
        lb_end = min(lb_end, day_end)
        if lb_start >= lb_end:
            continue
        new_intervals = []
        for iv_s, iv_e, tag in intervals:
            # Overlap between [iv_s, iv_e) and [lb_start, lb_end)
            if lb_end <= iv_s or lb_start >= iv_e:
                new_intervals.append((iv_s, iv_e, tag))
                continue
            if iv_s < lb_start:
                new_intervals.append((iv_s, lb_start, tag))
            new_intervals.append((max(iv_s, lb_start), min(iv_e, lb_end), "low_burn"))
            if lb_end < iv_e:
                new_intervals.append((lb_end, iv_e, tag))
        intervals = new_intervals

    return [(s, e, t) for s, e, t in intervals if s < e]


# ---------------------------------------------------------------------------
# Core placement helpers
# ---------------------------------------------------------------------------

def _round_up_5(dt: datetime) -> datetime:
    """Round datetime up to the nearest 5-minute boundary."""
    excess = dt.minute % 5
    if excess == 0 and dt.second == 0:
        return dt
    add = (5 - excess) % 5 or 5
    return (dt + timedelta(minutes=add)).replace(second=0, microsecond=0)


def _break_duration(task_duration_mins: int, percent: int) -> int:
    return max(1, math.ceil(task_duration_mins * percent / 100))


def _fit_tasks(
    tasks: list[Task],
    cursor: datetime,
    iv_end: datetime,
    break_percent: int,
    short_threshold: int,
    max_bunch: int = 120,
) -> tuple[list[ScheduleSlot], list[Task], datetime]:
    """
    Place tasks into [cursor, iv_end) respecting criticality order.

    Short tasks (duration ≤ short_threshold) that appear consecutively in
    criticality order are bunched back-to-back with a single break after
    the group.  A bunch is capped at max_bunch minutes; once hit, a break
    is emitted and a new bunch can start.  Regular tasks get their own break.

    Returns (slots_placed, remaining_tasks, new_cursor).
    """
    slots: list[ScheduleSlot] = []
    remaining = list(tasks)
    idx = 0

    while idx < len(remaining):
        task = remaining[idx]
        is_short = task.duration <= short_threshold  # type: ignore[operator]

        if is_short:
            # Accumulate consecutive short tasks into a bunch (capped at max_bunch)
            group: list[Task] = []
            group_duration = 0
            skipped: list[int] = []
            j = idx
            while j < len(remaining):
                t = remaining[j]
                if t.duration > short_threshold:  # type: ignore[operator]
                    break  # Hit a regular task — stop bunching
                candidate_end = cursor + timedelta(minutes=group_duration + t.duration)  # type: ignore[arg-type]
                would_exceed_cap = group_duration + t.duration > max_bunch and group  # type: ignore[operator]
                if candidate_end <= iv_end and not would_exceed_cap:
                    group.append(t)
                    group_duration += t.duration  # type: ignore[operator]
                else:
                    skipped.append(j)
                j += 1

            if group:
                group_end = cursor + timedelta(minutes=group_duration)
                slots.append(ScheduleSlot(
                    start=cursor, end=group_end, slot_type="task", group=group,
                ))
                cursor = group_end
                brk = _break_duration(group_duration, break_percent)
                brk_end = cursor + timedelta(minutes=brk)
                if brk_end <= iv_end:
                    slots.append(ScheduleSlot(start=cursor, end=brk_end, slot_type="break"))
                    cursor = brk_end
                # Remove placed tasks from remaining (in reverse to preserve indices)
                placed_set = set(id(t) for t in group)
                remaining = [t for t in remaining if id(t) not in placed_set]
                # Don't advance idx — it now points at the next task after removal
                continue
            else:
                # No short tasks fit — skip past this run of shorts
                idx = j
                continue
        else:
            # Regular task
            task_end = cursor + timedelta(minutes=task.duration)  # type: ignore[arg-type]
            if task_end > iv_end:
                # Doesn't fit — try next task
                idx += 1
                continue
            slots.append(ScheduleSlot(
                start=cursor, end=task_end, slot_type="task", task=task,
            ))
            cursor = task_end
            brk = _break_duration(task.duration, break_percent)  # type: ignore[arg-type]
            brk_end = cursor + timedelta(minutes=brk)
            if brk_end <= iv_end:
                slots.append(ScheduleSlot(start=cursor, end=brk_end, slot_type="break"))
                cursor = brk_end
            remaining.pop(idx)
            # Don't advance idx — next task shifted into this position
            continue

    return slots, remaining, cursor


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_schedule(
    tasks: list[Task],
    config: ScheduleConfig,
    from_time: datetime | None = None,
) -> tuple[list[ScheduleSlot], list[Task]]:
    """
    Schedule tasks for today.

    Args:
      from_time: If set, only place tasks into intervals at or after this time.
                 Earlier intervals are left empty (become gaps).

    Returns:
      - A sorted list of ScheduleSlots covering the full day window
        (tasks, breaks, blocked periods, and gaps).
      - A list of tasks that could not be scheduled.
    """
    today = date.today()

    work_start_dt = _to_dt(config.work_start, today)
    work_end_dt = _to_dt(config.work_end, today)
    day_end_dt = _to_dt(config.extended_end, today) if config.extended_end else work_end_dt

    # Build tagged intervals (before blocking)
    intervals = _tag_intervals(
        work_start_dt, day_end_dt, work_end_dt, config.low_burn, today
    )
    # Subtract blocked periods
    intervals = _subtract_blocked(intervals, config.blocked, today)
    # Sort by start
    intervals.sort(key=lambda x: x[0])

    # If from_time is set, trim scheduleable intervals to only those from that point onward
    if from_time is not None:
        start_cursor = _round_up_5(from_time)
        scheduleable_intervals = []
        for iv_s, iv_e, tag in intervals:
            if iv_e <= start_cursor:
                continue  # entirely in the past — skip for task placement
            if iv_s < start_cursor:
                iv_s = start_cursor
            scheduleable_intervals.append((iv_s, iv_e, tag))
    else:
        scheduleable_intervals = list(intervals)

    # Filter and sort scheduleable tasks
    scheduleable = [t for t in tasks if not t.completed and t.duration is not None]
    unscheduleable = [t for t in tasks if not t.completed and t.duration is None]
    scheduleable.sort(key=lambda t: t.criticality_score())

    # Partition into normal vs low-priority (both already in criticality order)
    n = len(scheduleable)
    cutoff = max(1, math.ceil(n * config.low_priority_threshold))
    normal_tasks = scheduleable[:cutoff]
    low_priority_tasks = scheduleable[cutoff:]

    placed_slots: list[ScheduleSlot] = []

    def _free_sub_intervals(
        iv_s: datetime, iv_e: datetime
    ) -> list[tuple[datetime, datetime]]:
        """Return free sub-intervals within [iv_s, iv_e) after accounting for placed_slots."""
        used = sorted(
            [(s.start, s.end) for s in placed_slots if s.start >= iv_s and s.end <= iv_e],
            key=lambda x: x[0],
        )
        free: list[tuple[datetime, datetime]] = []
        cursor = iv_s
        for us, ue in used:
            if cursor < us:
                free.append((cursor, us))
            cursor = max(cursor, ue)
        if cursor < iv_e:
            free.append((cursor, iv_e))
        return free

    # --- Pass 1: fill normal intervals with normal-priority tasks ---
    for iv_s, iv_e, tag in scheduleable_intervals:
        if tag != "normal":
            continue
        new_slots, normal_tasks, _ = _fit_tasks(
            normal_tasks, iv_s, iv_e,
            config.break_percent, config.short_task_threshold, config.max_bunch_duration,
        )
        placed_slots.extend(new_slots)

    # --- Pass 2: fill leftover normal-interval capacity with low-priority tasks ---
    for iv_s, iv_e, tag in scheduleable_intervals:
        if tag != "normal":
            continue
        for free_s, free_e in _free_sub_intervals(iv_s, iv_e):
            new_slots, low_priority_tasks, _ = _fit_tasks(
                low_priority_tasks, free_s, free_e,
                config.break_percent, config.short_task_threshold, config.max_bunch_duration,
            )
            placed_slots.extend(new_slots)

    # --- Pass 3: fill low-burn intervals ---
    # First: overflow normal-priority tasks that didn't fit in normal intervals.
    for iv_s, iv_e, tag in scheduleable_intervals:
        if tag != "low_burn":
            continue
        new_slots, normal_tasks, _ = _fit_tasks(
            normal_tasks, iv_s, iv_e,
            config.break_percent, config.short_task_threshold, config.max_bunch_duration,
        )
        placed_slots.extend(new_slots)

    # Then: remaining low-priority tasks in leftover low-burn capacity.
    for iv_s, iv_e, tag in scheduleable_intervals:
        if tag != "low_burn":
            continue
        for free_s, free_e in _free_sub_intervals(iv_s, iv_e):
            new_slots, low_priority_tasks, _ = _fit_tasks(
                low_priority_tasks, free_s, free_e,
                config.break_percent, config.short_task_threshold, config.max_bunch_duration,
            )
            placed_slots.extend(new_slots)

    overflow = normal_tasks + low_priority_tasks

    # --- Assemble full timeline: add blocked periods and gaps ---
    all_slots = list(placed_slots)

    for blk in config.blocked:
        blk_s = _to_dt(blk.start, today)
        blk_e = _to_dt(blk.end, today)
        if blk_s < day_end_dt and blk_e > work_start_dt:
            all_slots.append(
                ScheduleSlot(
                    start=max(blk_s, work_start_dt),
                    end=min(blk_e, day_end_dt),
                    slot_type="blocked",
                    label=blk.label or "blocked",
                )
            )

    all_slots.sort(key=lambda s: s.start)

    # Fill gaps between slots
    final: list[ScheduleSlot] = []
    if intervals:
        day_window_start = intervals[0][0]
        day_window_end = intervals[-1][1]

        # Also account for blocked periods in determining the full window
        if config.blocked:
            earliest_blk = min(_to_dt(b.start, today) for b in config.blocked)
            latest_blk = max(_to_dt(b.end, today) for b in config.blocked)
            day_window_start = min(day_window_start, max(earliest_blk, work_start_dt))
            day_window_end = max(day_window_end, min(latest_blk, day_end_dt))

        cursor = day_window_start
        for slot in all_slots:
            if slot.start > cursor:
                final.append(
                    ScheduleSlot(start=cursor, end=slot.start, slot_type="gap")
                )
            final.append(slot)
            cursor = max(cursor, slot.end)
        if cursor < day_window_end:
            final.append(ScheduleSlot(start=cursor, end=day_window_end, slot_type="gap"))
    else:
        final = all_slots

    return final, overflow + unscheduleable
