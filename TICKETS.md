# Ticket Board

## Backlog
<!-- New tickets go here. Format: - [ ] #ID TYPE: Title -->

- [ ] #001 feature: Tag-based scheduling preferences (preferred days/times per tag)
      Added: 2026-03-29 | Priority: critical
      Notes: Each tag should have configurable preferred time slots (e.g. personal →
             evenings/weekends) and optionally a preferred burn mode (normal/low-burn).
             Applies to the Today/schedule view. Energy level is out of scope for now.

- [ ] #003 feature: Support time component on due dates (e.g. "today by 8PM")
      Added: 2026-03-29 | Priority: high
      Notes: Due dates currently store YYYY-MM-DD only. Extend to YYYY-MM-DD HH:MM so
             tasks with a due time get scheduled before that deadline in the Today view.

- [ ] #004 feature: Add start date/time field to tasks (not-before constraint)
      Added: 2026-03-29 | Priority: high
      Notes: Tasks with a start date/time should not be scheduled before that point.
             Supports both date-only (don't start until tomorrow) and datetime
             (don't start until 2PM today) granularity.


## In Progress
<!-- Move here when actively working on it -->

## Done
<!-- Move here when complete. Change [ ] to [x] -->

- [x] #002 feature: Prioritization view should be a single continuous unpaged list
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 54df941
      Notes: When pressing `p` to enter prioritization view, show all tasks in one
             scrollable list (no pagination) so tasks can be freely reordered.

- [x] #007 bug: Navigation breaks after completing a task in the Today view
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 54df941
      Notes: After marking a task complete (within a group of quick tasks), up/down
             navigation stops working. Workaround is to reschedule or exit+re-enter
             the Today view. Should restore focus/navigation automatically after
             completion without requiring a full reschedule.

- [x] #005 bug: Break duration calculated from last task in block, not total block duration
      Added: 2026-03-29 | Priority: high | Done: 2026-03-29 | Commit: 8524465
      Notes: Breaks should be sized based on the cumulative work block (e.g. 2h block →
             appropriate break), not on the duration of the final task before the break.
             e.g. 3×30min + 2×15min = ~2h block should get a full block-length break,
             not a break sized for a 15min task.

- [x] #006 bug: Chunked task parts sometimes appear out of order in the schedule
      Added: 2026-03-29 | Priority: low | Done: 2026-03-29 | Commit: 8524465
      Notes: e.g. [2/4] appears before [1/4] in the Today view. Chunks should always
             be scheduled in ascending order.

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
