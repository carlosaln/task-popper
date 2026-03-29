# Ticket Board

## Backlog
<!-- New tickets go here. Format: - [ ] #ID TYPE: Title -->

## In Progress
<!-- Move here when actively working on it -->

## Done
<!-- Move here when complete. Change [ ] to [x] -->

- [x] #001 feature: Tag-based scheduling preferences (preferred days/times per tag)
      Added: 2026-03-29 | Priority: critical | Done: 2026-03-29 | Commit: (pending)
      Notes: Each tag can have a preferred_burn_mode (normal/low_burn) and optional
             preferred_times (list of TimeBlock). Burn mode routing re-sorts budgets
             before scheduling passes. Time-preference filter defers tasks to matching
             intervals with fallback to remaining slots. TagPreferencesModal added to
             ScheduleConfigScreen (key: p) for viewing/editing tag preferences.

- [x] #002 feature: Prioritization view should be a single continuous unpaged list
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 54df941
      Notes: PriorityScreen now shows all tasks in one scrollable list. Removed
             pagination (ctrl+d/u), cursor navigates the full flat list.

- [x] #003 feature: Support time component on due dates (e.g. "today by 8PM")
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 5e90d44
      Notes: Extended parse_due_date to return str | None (ISO string). Parses
             "today by 8pm", "friday by noon", "2026-04-01T14:30" etc.
             _format_due updated to display time when present.

- [x] #004 feature: Add start date/time field to tasks (not-before constraint)
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 5e90d44
      Notes: Added start_date field to Task. Scheduler filters out tasks whose
             start_date is in the future. EditTaskModal has a new "Start date" field.

- [x] #005 bug: Break duration calculated from last task in block, not total block duration
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 8524465
      Notes: Breaks are now sized from cumulative accumulated work since the last break,
             not just the most recent task/chunk duration.

- [x] #006 bug: Chunked task parts sometimes appear out of order in the schedule
      Added: 2026-03-29 | Priority: low | Done: 2026-03-29 | Commit: 8524465
      Notes: Post-processing pass re-numbers chunk_index in start-time order after
             all chunks are placed and sorted.

- [x] #007 bug: Navigation breaks after completing a task in the Today view
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 54df941
      Notes: After completing a task in an expanded group, auto-collapses if no
             non-completed tasks remain, or advances cursor to next incomplete task.

---

## How to read a ticket line

```
- [ ] #001 bug: Cursor jumps to top after deleting a task
      Added: 2026-03-29 | Priority: high
      Notes: Happens when the deleted task is the last in the list.
```

- **ID**: Auto-incrementing `#NNN`. Never reuse IDs.
- **TYPE**: `bug`, `feature`, `chore`, `docs`
- **Priority**: `low`, `medium`, `high`, `critical`
- **Notes**: Optional indented lines below the ticket line for context.

Next ID: 008
