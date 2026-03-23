# Keybindings

## Reference

## Main Screen

| Key | Action | Implementation |
|---|---|---|
| `j` | Cursor down | `BINDINGS` → `action_cursor_down` |
| `k` | Cursor up | `BINDINGS` → `action_cursor_up` |
| `↓` | Cursor down (alternate) | `BINDINGS` → `action_cursor_down` |
| `↑` | Cursor up (alternate) | `BINDINGS` → `action_cursor_up` |
| `p` | Open Priority Screen | `BINDINGS` → `action_priority_screen` |
| `x` | Toggle task complete | `BINDINGS` → `action_complete_task` |
| `s` | Edit selected task | `BINDINGS` → `action_edit_task` |
| `n` | New task | `BINDINGS` → `action_new_task` |
| `dd` | Delete selected task | `on_key` state machine |
| `ctrl+d` | Page down | `BINDINGS` → `action_page_down` |
| `ctrl+u` | Page up | `BINDINGS` → `action_page_up` |
| `0`–`9` | Jump to task at that index on current page | `on_key` handler |
| `q` | Quit | `BINDINGS` → built-in `quit` |

## Priority Screen

Opened with `p` from the main screen. Tasks are sorted by `priority_order` only — no due-date influence. Use J/K to set priority rankings, then press `p` or `escape` to return. The main list will re-sort by `criticality_score()` (blending the updated priorities with due dates).

| Key | Action | Implementation |
|---|---|---|
| `j` | Cursor down | `BINDINGS` → `action_cursor_down` |
| `k` | Cursor up | `BINDINGS` → `action_cursor_up` |
| `↓` | Cursor down (alternate) | `BINDINGS` → `action_cursor_down` |
| `↑` | Cursor up (alternate) | `BINDINGS` → `action_cursor_up` |
| `J` (`shift+j`) | Move selected task down (lower priority) | `BINDINGS` → `action_task_move_down` |
| `K` (`shift+k`) | Move selected task up (higher priority) | `BINDINGS` → `action_task_move_up` |
| `ctrl+d` | Page down | `BINDINGS` → `action_page_down` |
| `ctrl+u` | Page up | `BINDINGS` → `action_page_up` |
| `0`–`9` | Jump to task at that index on current page | `on_key` handler |
| `p` / `escape` | Return to main screen | `BINDINGS` → `action_go_back` |

## Schedule Screen (Today)

Opened with `t` from the main screen. Shows the full day schedule from configured start to end. Past time slots are grayed out. Tasks stay in their scheduled positions until the user explicitly reschedules with `r`.

| Key | Action | Implementation |
|---|---|---|
| `j` | Cursor down | `BINDINGS` → `action_cursor_down` |
| `k` | Cursor up | `BINDINGS` → `action_cursor_up` |
| `x` | Complete task / expand group | `BINDINGS` → `action_complete_task` |
| `r` | Reschedule (rebuild from scratch) | `BINDINGS` → `action_reschedule` |
| `c` | Configure schedule | `BINDINGS` → `action_configure` |
| `escape` | Collapse expanded group | `action_go_back` (when expanded) |
| `t` / `escape` | Return to main screen | `BINDINGS` → `action_go_back` |

## Implementation notes

**`dd` delete** — handled in `on_key` with a state machine (main screen only):
- First `d`: sets `_awaiting_second_d = True`, records `time.monotonic()` in `_last_d_time`.
- Second `d` within 500ms: calls `_do_delete()` and resets state.
- Any other key resets `_awaiting_second_d = False`.
- `event.stop()` is called on `d` to prevent it from affecting other bindings.

**`0`–`9` digit jump** — handled in `on_key` on both screens:
- Only fires if `len(event.key) == 1 and event.key.isdigit()`.
- Jumps cursor to that index only if the index is within the current page's task count.
- `event.stop()` prevents digits from reaching other handlers.

**Cursor wrap** — `action_cursor_up` wraps to the last item of the previous page; `action_cursor_down` wraps to the first item of the next page.

**Reorder + pagination** — `action_task_move_up/down` on the priority screen uses `divmod(new_global_idx, PAGE_SIZE)` to follow the task across page boundaries if the reorder moves it to a different page.

## Adding a new binding

1. Add to `BINDINGS` in `TaskPopperApp` in `app.py`.
2. Implement the corresponding `action_<name>` method.
3. Update the `#footer-hints` static string in `compose()`.
4. Update this file.

For multi-key sequences (like `dd`), add handling to `on_key` instead of `BINDINGS`.
