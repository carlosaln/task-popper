# Task Popper

A terminal task manager that ranks tasks by criticality — a composite of due date and expressed priority.

## Install

```
uv sync
```

## Run

```
uv run task-popper
```

## Usage

Tasks are displayed in a scrollable list, ranked by criticality (expressed priority blended with due date urgency). Move tasks up and down to set their priority — higher position means more important.

Each task has a **bold title** and an optional description in a lighter font. Tags (`#hashtag`), due dates, durations, and start dates are shown inline.

## Keyboard Shortcuts

### Main screen

| Key | Action |
|---|---|
| `j` / `k` | Move cursor down/up |
| `n` | New task |
| `s` | Edit selected task |
| `x` | Toggle task complete |
| `dd` | Delete task (vim-style double-tap) |
| `p` | Open Priority screen |
| `t` | Open Today schedule |
| `f` | Filter by tag (`ff` clears filter) |
| `ctrl+d` / `ctrl+u` | Page down/up |
| `0–9` | Jump to task by number |
| `q` | Quit |

### Priority screen (`p`)

All tasks in one scrollable list sorted by pure priority (no due-date influence). Use `J`/`K` to reorder.

| Key | Action |
|---|---|
| `j` / `k` | Navigate |
| `J` / `K` | Move selected task down/up in priority |
| `f` / `ff` | Filter by tag / clear filter |
| `p` / `esc` | Return to main screen |

### Today schedule (`t`)

A daily timeline built from your task list. Tasks are chunked, interleaved, and placed into time slots based on the schedule config. Past slots are grayed out.

| Key | Action |
|---|---|
| `j` / `k` | Navigate slots |
| `x` | Complete task (or expand a quick-task group) |
| `r` | Reschedule from now |
| `c` | Open schedule config |
| `t` / `esc` | Return to main screen |

### Schedule config (`c` from Today)

Timeline-based day editor. Navigate 15-minute slots and mark them normal, low-burn, or blocked.

| Key | Action |
|---|---|
| `j` / `k` | Move 15 min |
| `J` / `K` | Move 1 hour |
| `n` | Mark normal |
| `b` | Mark blocked |
| `l` | Mark low-burn |
| `o` | Edit day settings (hours, break %, chunk sizes) |
| `p` | Edit tag preferences |
| `ctrl+s` | Save config |
| `S` | Save as default |
| `R` | Reset to default |
| `esc` | Cancel |

## Task fields

| Field | Description |
|---|---|
| `title` | Required. Duration suffix parsed from last word (e.g. `2h30m`, `45m`). |
| `description` | Optional second line. |
| `tags` | `#hashtag` tokens extracted from title (e.g. `Fix login #work 1h`). |
| `due_date` | Date or datetime: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`. Parsed from natural language in the edit modal (`tomorrow`, `next friday`, `today by 8pm`, `friday by noon`). |
| `start_date` | Not-before constraint: task won't be scheduled before this date/time. Same format and parsing as `due_date`. |
| `due_time` | Same-day pin time: `4pm`, `16:00`, `noon`, etc. The scheduler places this task starting exactly at that time, regardless of priority. Ignored (task returns to general pool) once the time has passed. |
| `duration` | Estimated minutes, parsed from title suffix. Required for scheduling. |
| `priority_order` | Position in the priority list (lower = higher priority). |
| `completed` | Toggled via `x`. Completed tasks are archived weekly. |

## Scheduling

The Today view builds a daily timeline using `build_schedule()`:

- **Chunking** — tasks longer than `max_chunk_duration` (default 120 min) are split across the day and interleaved with other tasks. Chunks always appear in order.
- **Short-task bunching** — tasks ≤ `short_task_threshold` (default 15 min) are grouped into bunches of up to `max_chunk_duration`.
- **Breaks** — sized from the *accumulated* work since the last break (not just the most recent task), so a 2-hour block gets an appropriate break rather than one sized for the last 15-minute task.
- **Low-burn intervals** — periods of lower intensity (e.g. evenings). Lower-priority tasks are routed here first.
- **Blocked periods** — marked unavailable; shown in the timeline but never filled with tasks.
- **Start dates** — tasks with a future `start_date` are excluded from today's schedule.
- **Pin times** — tasks with `due_time` set are placed starting exactly at that time via a pre-pass. If the time has passed and the task is still incomplete, it falls back to normal scheduling.

### Tag-based scheduling preferences

Tags can have per-tag scheduling rules configured in the **Tag Prefs** modal (`p` in the config screen):

| Field | Description |
|---|---|
| **Tag** | Tag name without `#` |
| **Days** | `weekdays`, `weekends`, `all`, or comma-separated names like `mon,wed,fri` |
| **Times** | Optional preferred time window: `HH:MM-HH:MM` (e.g. `18:00-22:00`). Blank = any time. |
| **Burn mode** | `normal` or `low_burn` — routes the task to the matching interval type |

Multiple rules per tag are supported, which lets you express things like *"personal tasks on weekday evenings or any time on weekends"*:

```
#personal  weekdays  18:00-22:00  burn=normal
#personal  weekends  any time     burn=normal
```

Tasks deferred by day/time preferences fall back to any open slot if no matching interval exists.

## Storage

- **Tasks** — `~/.task-popper/tasks.json`
- **Schedule config** — `~/.task-popper/schedule.json`
- **Completed task archive** — `~/.task-popper/archive/<year>/week-<NN>.json`
