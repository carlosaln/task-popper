# Planned Features & Extension Points

## Near-term

### Per-directory task lists
`resolve_store_path()` in `store.py` is stubbed for this. The planned behavior:
1. Walk up from `cwd` looking for a `.task-popper/` directory.
2. If found, use `.task-popper/tasks.json` there (project-local list).
3. Fall back to `~/.task-popper/tasks.json` (global list).

The `TaskStore` constructor already accepts an explicit `path` argument, so no other changes are needed once `resolve_store_path()` is implemented.

### View completed tasks
The store already supports `get_sorted(include_completed=True)` and `get_page(..., include_completed=True)`. Need a toggle in the UI (e.g. `c` to show/hide completed).

## Planned task properties

The `Task` dataclass has reserved (commented-out) fields:

### Sub-tasks / checklists
- `parent_id: str | None` — makes a task a child of another.
- Checklists = tasks with title only and no description, nested under a parent.
- Display: indented under the parent task row, with a checkbox indicator.
- Store: `TaskStore.get_children(parent_id)` to retrieve.

### Dependencies
- `dependencies: list[str]` — IDs of tasks that must complete before this one.
- Blocked tasks could be visually dimmed and excluded from criticality sort until unblocked.

### Tags
- `tags: list[str]` — free-form labels.
- Enable filtering the list by tag (e.g. `t` to filter by tag).

## UI improvements

- **Inline editing** — edit title directly in the list without opening a modal.
- **Search / filter** — `/` to open a search bar, filter tasks by title or tag.
- **Undo** — buffer of recent mutations to reverse with `u`.
- **Confirmation prompt** — optional confirm step before `dd` delete.
- **Due date quick-set** — set due date directly from the list without opening the full edit modal.

## Architecture considerations

- If the task list grows large (hundreds of tasks), consider lazy rendering and a fixed-height scroll viewport rather than full rebuild in `_refresh_view()`.
- `TaskStore` currently writes the full JSON file on every mutation. For large lists, a debounced or write-ahead approach would reduce I/O.
- The criticality score is recomputed on every sort call. If scoring becomes expensive (e.g., involves external lookups), consider caching with invalidation on mutation.
