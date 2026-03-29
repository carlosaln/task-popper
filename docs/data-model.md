# Data Model

## Task fields

| Field | Type | Description |
|---|---|---|
| `id` | `str` | UUID4, generated on creation |
| `title` | `str` | Required. Displayed bold. |
| `description` | `str` | Optional. Displayed dim below title. Default `""`. |
| `priority_order` | `int` | Lower = higher priority. Reflects the user's manual ordering. |
| `due_date` | `str \| None` | ISO 8601 date: `"YYYY-MM-DD"`. `None` when unset. |
| `duration` | `int \| None` | Estimated duration in minutes. Parsed from title suffix (e.g. `2h30m`). `None` when unset. |
| `due_time` | `str \| None` | Same-day "finish by" time: `"HH:MM"`. Scheduler pre-places this task before the deadline. Ignored (but not cleared) once the time has passed. |
| `tags` | `list[str]` | Free-form labels extracted from `#hashtags` in the title. |
| `completed` | `bool` | `False` by default. Toggled by `shift+enter`. |
| `completed_at` | `str \| None` | ISO 8601 datetime when completed, `None` otherwise. |
| `created_at` | `str` | ISO 8601 datetime (UTC) at creation. |

Fields reserved for future use (commented out in `models.py`):
- `parent_id: str | None` — for sub-tasks / checklists
- `dependencies: list[str]` — task IDs this task depends on

## Serialization

`to_dict()` / `from_dict()` handle JSON round-trips. `from_dict()` uses `.get()` with defaults for all optional fields so older JSON files load cleanly when new fields are added.

The JSON file structure:
```json
{
  "tasks": [
    {
      "id": "...",
      "title": "Fix login bug",
      "description": "OAuth redirect loop",
      "priority_order": 0,
      "due_date": "2026-03-25",
      "duration": 120,
      "tags": ["work", "urgent"],
      "completed": false,
      "completed_at": null,
      "created_at": "2026-03-22T10:00:00+00:00"
    }
  ]
}
```

## Criticality scoring

`Task.criticality_score() -> float` — lower score = displayed higher in the list.

Current formula:
```
score = priority_order + due_score

due_score = days_until_due * 0.5   (clamped to ±365)
          = 0.0                     (if no due_date)
```

- `priority_order` is the primary driver. Each position step = 1.0.
- `due_score` shifts tasks with upcoming due dates earlier in the list.
- A task due in 2 days has `due_score = 1.0`, equivalent to one priority step.
- Overdue tasks have negative `due_score`, making them more critical.
- The 0.5 weight means due dates influence but don't override manual priority.

The score is recomputed on every sort — no caching, no stored scores.

## Priority order management

`priority_order` is a contiguous integer assigned by `TaskStore`:
- `add()` appends new tasks at `len(active_tasks)` — lowest priority.
- `move_up()` / `move_down()` swap `priority_order` values between adjacent tasks.
- `delete()` calls `_renumber()` to restore contiguity.
- Completed tasks are excluded from the active list and do not affect `priority_order` of active tasks.

## Task chunking (schedule interleaving)

Tasks longer than `max_chunk_duration` (default 120 minutes) are dynamically split into chunks for scheduling. This prevents a single long task from monopolizing the entire day.

**Dynamic sizing:** Chunks are sized to fit the available gap, not pre-sliced into fixed sizes. A 90-minute gap between a blocked period and end-of-day gets a 90-minute work session, not wasted because 120 minutes won't fit. Chunk sizes are:
- Capped at `max_chunk_duration` (default 120 min)
- Floored at `min_chunk_duration` (default 30 min) — unless the remaining work is smaller, in which case it places the remainder to finish the task

**Interleaving:** The scheduler uses a `TaskBudget` that tracks remaining work per task. After placing a chunk, the task's effective criticality is penalized:

```
effective_criticality = base_criticality + chunks_placed * SPREAD_FACTOR
```

`SPREAD_FACTOR` is 1.0 (one priority-order step per chunk). This means:

- Chunk 1 of a task keeps its original criticality
- Chunk 2 has the same effective criticality as the next-priority task
- Chunk 3 matches the task two priority positions below
- ...and so on

This naturally handles edge cases:
- **Similar-criticality tasks:** chunks interleave evenly with other tasks
- **Dominant task (much higher criticality):** all chunks still schedule first, because even penalized chunks remain more critical than everything else
- **Short tasks (≤ short_task_threshold):** never chunked; grouped into bunches instead, also capped at `max_chunk_duration`

The `max_chunk_duration` config value serves double duty: it caps both individual long-task chunks and short-task bunch groups. Both represent "maximum continuous work time before a context switch."

Chunked tasks display as `Task title [2/8] ~1h22m of 15h` in the schedule view.

## Duration parsing

`parse_duration(title)` in `widgets.py` extracts duration from the last word of the title. Recognized formats: `30m`, `3h`, `1h30m`, `2h15m`. Duration is stored in minutes on the `Task.duration` field. Tasks without duration are not scheduleable.

## Due date parsing

Parsing from natural language is done only in `widgets.py` via `parse_due_date(text) -> date | None`. The model and store always receive and store pre-validated `YYYY-MM-DD` strings.

Parser resolution order:
1. `date.fromisoformat()` — handles `YYYY-MM-DD` directly
2. `_pre_parse()` — custom handler for `next <weekday>` and `this <weekday>` (patterns `dateparser` misses)
3. `dateparser.parse()` — handles everything else (`tomorrow`, `in 3 days`, `march 25`, etc.)
