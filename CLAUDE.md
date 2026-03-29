# Task Popper — Claude Context

A terminal-based task manager built with Python + Textual. Focus: usability first, performance second.

## References

- [docs/architecture.md](docs/architecture.md) — module layout, data flow, key design decisions
- [docs/data-model.md](docs/data-model.md) — Task fields, serialization, criticality scoring
- [docs/keybindings.md](docs/keybindings.md) — all keyboard shortcuts and how they're implemented
- [docs/future.md](docs/future.md) — planned features, reserved fields, extension points

## Tooling

- **Python 3.12+**, managed with **uv** — always use `uv add`, `uv run`, `uv sync`. Never use pip.
- Entry point: `uv run task-popper`
- Run ad-hoc scripts: `uv run python -c "..."`
- The package is installed in editable mode via `tool.uv.package = true` + hatchling.

## Testing

No test suite yet. Use headless Textual tests for logic verification:

```python
async with app.run_test(headless=True) as pilot:
    await pilot.press("j")
    await pilot.pause(0.1)
    assert app.cursor_index == 1
```

`TaskStore` can be pointed at a temp file for isolation:

```python
store = TaskStore(pathlib.Path(tmpdir) / "tasks.json")
```

## Ticket tracking

We use `TICKETS.md` at the project root as a file-based ticket board (no GitHub issues).
- Read `TICKETS.md` at the start of any ticket-related conversation.
- When adding a ticket, use the next available `#NNN` ID and increment the counter.
- When completing a ticket, move it to Done, mark `[x]`, and add the commit hash if applicable.
- Create a new branch for each ticket: `ticket/NNN-short-description` (e.g. `ticket/003-fix-cursor-jump`).
- See [docs/how-to-do-tickets.md](docs/how-to-do-tickets.md) for full format details.

## Key conventions

- Widget instance data uses `self.data` (not `self.task`) — Textual has an internal `.task` property on widgets.
- All mutations go through `TaskStore` methods, which auto-save on every call.
- `_refresh_view()` is the single method that rebuilds the task list UI from store state. Call it after any mutation.
- Modal results are 3-tuples `(title: str, desc: str, due: str)` — due is `""` when not set, `YYYY-MM-DD` when set.
- Due dates are stored as `YYYY-MM-DD` ISO strings. Parsing from natural language happens only in the UI layer (`widgets.py`), never in the model or store.
