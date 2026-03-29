# Problem: Completing a schedule chunk completes the entire task

## Current behavior

In the schedule view (`ScheduleScreen`), long tasks are dynamically chunked by the scheduler. For example, an 8h task might appear as multiple slots: `[1/4] ~2h`, `[2/4] ~2h`, etc.

When you press `x` on any chunk, `action_complete_task()` calls `self.store.complete(slot.task.id)`, which:

1. Sets `task.completed = True`
2. Removes the task from the active list entirely
3. Archives it

Since all chunks reference the same `Task` object (same `task.id`), completing chunk 1 completes the whole task. The remaining chunks become stale — they still appear in the current schedule view (the slots were already built), but the underlying task is gone. On the next reschedule or app restart, the task disappears completely.

There is no concept of "partial completion" or "remaining duration." The `Task.duration` field is static and never decremented when a chunk is completed.

## Expected behavior

Completing a chunk should:

1. Subtract the chunk's duration from the task's remaining time (e.g., 8h -> 6h after a 2h chunk)
2. Keep the task active with the reduced duration
3. Remove only that chunk from the schedule view
4. Auto-complete the task only when remaining duration hits zero (last chunk completed)

## Relevant code

- **Scheduler** (`scheduler.py`): `TaskBudget` tracks `remaining` minutes during scheduling, but this is ephemeral — it's not persisted. `ScheduleSlot` has `chunk_index` and `total_chunks` but no chunk duration.
- **Schedule screen** (`screens.py:431-455`): `action_complete_task()` calls `store.complete()` on the full task regardless of which chunk was selected.
- **Store** (`store.py:111-122`): `complete()` is all-or-nothing — marks done, removes from active list, archives.
- **Model** (`models.py`): `Task.duration` is an `int | None` (total minutes). No field for time spent or remaining time.

## Design considerations

- The chunk duration isn't stored on the `ScheduleSlot` explicitly, but it can be derived from `slot.end - slot.start` (minus break time).
- Need to decide: should we modify `Task.duration` in place (subtract completed chunk time), or add a separate `time_spent` / `time_remaining` field?
- Modifying `duration` directly is simpler but loses the original estimate. A `time_spent` field preserves the estimate and lets you show progress like `2h / 8h`.
