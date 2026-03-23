# Architecture

## File layout

```
task_popper/
├── __init__.py       — empty
├── __main__.py       — entry point; calls TaskPopperApp().run()
├── models.py         — Task dataclass + criticality scoring
├── store.py          — TaskStore: JSON persistence, sorting, mutations
├── widgets.py        — TaskRow, PriorityRow, EditTaskModal, date parsing/formatting utilities
├── screens.py        — PriorityScreen: full-screen priority reordering view
└── app.py            — TaskPopperApp: layout, keybindings, actions, view refresh
```

## Layers

```
app.py  (UI + input handling)
   │  calls
   ▼
store.py  (in-memory list + JSON file)
   │  uses
   ▼
models.py  (Task dataclass, criticality_score())

widgets.py  (pure UI components, no store access)
```

`app.py` owns all state: `current_page`, `cursor_index`, and a reference to `TaskStore`. Widgets are stateless — they receive data at construction and are fully rebuilt by `_refresh_view()` on every state change.

## UI layout (Textual widget tree)

```
TaskPopperApp
├── Static#app-header        — title bar
├── StatusBar#status-bar     — "Page 1/3 • 5 tasks"
├── Vertical#task-container  — holds TaskRow widgets (rebuilt on every refresh)
│   └── TaskRow × n          — one per task on current page (0–9)
└── Static#footer-hints      — static key hint bar
```

`EditTaskModal` is pushed as a `ModalScreen` over the main screen and dismissed with a 3-tuple result.

`PriorityScreen` is pushed as a full `Screen` via `push_screen`. It shares the same `TaskStore` instance as the main app. On dismiss, the main app's `_refresh_view()` is called so the main list re-sorts by `criticality_score()` with the updated `priority_order` values.

## State management

All UI state lives on `TaskPopperApp` as plain instance attributes (not reactive watchers):

| Attribute | Type | Description |
|---|---|---|
| `current_page` | `int` | Zero-based page index |
| `cursor_index` | `int` | Zero-based position within the current page |
| `store` | `TaskStore` | Single store instance for the app's lifetime |
| `_awaiting_second_d` | `bool` | State machine for `dd` delete |
| `_last_d_time` | `float` | `time.monotonic()` of last `d` press |

Mutations follow this pattern everywhere:
1. Call a `TaskStore` method (auto-saves to disk)
2. Optionally update `current_page` / `cursor_index`
3. Call `self._refresh_view()`

## View refresh

`_refresh_view()` does a full rebuild of `#task-container` children on every call:
- Clears all children
- Fetches the current page from the store
- Mounts fresh `TaskRow` instances
- Updates the status bar

This is intentionally simple. With ≤10 rows per page, the cost is negligible.

## Storage path resolution

`resolve_store_path()` in `store.py` currently always returns `~/.task-popper/tasks.json`. It is designed to later support per-directory lists by walking up from cwd looking for a `.task-popper/` directory (see `docs/future.md`).
