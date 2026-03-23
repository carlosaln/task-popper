# Data Model

## Task fields

| Field | Type | Description |
|---|---|---|
| `id` | `str` | UUID4, generated on creation |
| `title` | `str` | Required. Displayed bold. |
| `description` | `str` | Optional. Displayed dim below title. Default `""`. |
| `priority_order` | `int` | Lower = higher priority. Reflects the user's manual ordering. |
| `due_date` | `str \| None` | ISO 8601 date: `"YYYY-MM-DD"`. `None` when unset. |
| `completed` | `bool` | `False` by default. Toggled by `shift+enter`. |
| `completed_at` | `str \| None` | ISO 8601 datetime when completed, `None` otherwise. |
| `created_at` | `str` | ISO 8601 datetime (UTC) at creation. |

Fields reserved for future use (commented out in `models.py`):
- `parent_id: str | None` — for sub-tasks / checklists
- `dependencies: list[str]` — task IDs this task depends on
- `tags: list[str]` — free-form labels

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

## Due date parsing

Parsing from natural language is done only in `widgets.py` via `parse_due_date(text) -> date | None`. The model and store always receive and store pre-validated `YYYY-MM-DD` strings.

Parser resolution order:
1. `date.fromisoformat()` — handles `YYYY-MM-DD` directly
2. `_pre_parse()` — custom handler for `next <weekday>` and `this <weekday>` (patterns `dateparser` misses)
3. `dateparser.parse()` — handles everything else (`tomorrow`, `in 3 days`, `march 25`, etc.)
