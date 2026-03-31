# Ticket Board

## Backlog
<!-- New tickets go here. Format: - [ ] #ID TYPE: Title -->

- [ ] #009 chore: Add comprehensive test suite for core modules
      Added: 2026-03-30 | Priority: low
      Notes: Cover TaskStore mutations, criticality scoring, scheduler edge cases, and parsing functions. Use pytest + Textual's headless testing framework.

- [ ] #010 chore: Implement proper error handling in store.py and widgets.py
      Added: 2026-03-30 | Priority: low
      Notes: Add try/except blocks for JSON parsing failures, invalid date formats, and file I/O errors. Provide user-friendly error messages instead of tracebacks.

- [ ] #011 chore: Consolidate configuration constants into config.py
      Added: 2026-03-30 | Priority: low
      Notes: Move PAGE_SIZE, default durations, and scheduler parameters from multiple files into a centralized Config dataclass loaded at startup.

- [ ] #012 feature: Complete per-directory store resolution in store.py
      Added: 2026-03-30 | Priority: low
      Notes: Implement the commented plan to walk up from cwd looking for .task-popper/ directory, enabling project-specific task lists.

- [ ] #013 docs: Document the rationale for manual _refresh_view() vs reactive
      Added: 2026-03-30 | Priority: low
      Notes: Explain in architecture.md why full rebuilds are used instead of Textual's reactive system, including performance trade-offs and simplicity benefits.

## In Progress
<!-- Move here when actively working on it -->

## Done
<!-- Move here when complete. Change [ ] to [x] -->

- [x] #008 feature: Task "finish by" time — same-day scheduling deadline (due_time)
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29
      Notes: Add due_time: str | None ("HH:MM") to Task. Scheduler pre-pass (EDF order)
             places timed tasks before their deadline, pulling from both normal and
             low-priority pools. Expired constraints are silently ignored — task falls
             back to general scheduling. Editable in EditTaskModal ("Finish by (today)"
             field). Displayed in TaskRow and ScheduleRow when active.

- [x] #001 feature: Tag-based scheduling preferences (preferred days/times per tag)
      Added: 2026-03-29 | Priority: critical | Done: 2026-03-29 | Commit: 259e8b5
      Notes: TagPreference dataclass in config.py (tag, preferred_burn_mode, preferred_times).
             Scheduler routes low_burn-tagged tasks to low-burn intervals; time-preference
             filter defers tasks to matching intervals with fallback. TagPreferencesModal
             added to ScheduleConfigScreen (key: p).

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

Next ID: 014
