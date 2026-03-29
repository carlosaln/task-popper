# Ticket Board

## Backlog
<!-- New tickets go here. Format: - [ ] #ID TYPE: Title -->

- [ ] #001 feature: Tag-based scheduling preferences (preferred days/times per tag)
      Added: 2026-03-29 | Priority: critical
      Notes: Each tag should have configurable preferred time slots (e.g. personal →
             evenings/weekends) and optionally a preferred burn mode (normal/low-burn).
             Applies to the Today/schedule view. Energy level is out of scope for now.

- [ ] #002 feature: Prioritization view should be a single continuous unpaged list
      Added: 2026-03-29 | Priority: high
      Notes: When pressing `p` to enter prioritization view, show all tasks in one
             scrollable list (no pagination) so tasks can be freely reordered.

- [ ] #007 bug: Navigation breaks after completing a task in the Today view
      Added: 2026-03-29 | Priority: high
      Notes: After marking a task complete (within a group of quick tasks), up/down
             navigation stops working. Workaround is to reschedule or exit+re-enter
             the Today view. Should restore focus/navigation automatically after
             completion without requiring a full reschedule.

## In Progress
<!-- Move here when actively working on it -->

## Done
<!-- Move here when complete. Change [ ] to [x] -->

- [x] #003 feature: Support time component on due dates (e.g. "today by 8PM")
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 5e90d44
      Notes: Extended parse_due_date to return str | None (ISO string). Parses
             "today by 8pm", "friday by noon", "2026-04-01T14:30" etc.
             _format_due updated to display time when present. due_date field
             now stores YYYY-MM-DDTHH:MM when a time is given.

- [x] #004 feature: Add start date/time field to tasks (not-before constraint)
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 5e90d44
      Notes: Added start_date field to Task (YYYY-MM-DD or YYYY-MM-DDTHH:MM).
             Scheduler filters out tasks whose start_date is in the future.
             EditTaskModal has a new "Start date (not before)" input field.
             Modal result expanded from 5-tuple to 6-tuple.

- [x] #005 bug: Break duration calculated from last task in block, not total block duration
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 8524465
      Notes: Breaks are now sized from cumulative accumulated work since the last break,
             not just the most recent task/chunk duration.

- [x] #006 bug: Chunked task parts sometimes appear out of order in the schedule
      Added: 2026-03-29 | Priority: low | Done: 2026-03-29 | Commit: 8524465
      Notes: Post-processing pass re-numbers chunk_index in start-time order after
             all chunks are placed and sorted.

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
