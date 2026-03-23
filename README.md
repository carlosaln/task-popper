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

Tasks are displayed 10 per page, numbered 0–9. Move tasks up and down the list to express their priority — higher position means more important. Criticality is calculated from that expressed priority plus due date (when set).

Each task has a **bold title** and an optional description in a lighter font.

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `j` / `k` | Move cursor down/up |
| `↑` / `↓` | Move cursor up/down (alternate) |
| `J` | Move selected task up (higher priority) |
| `K` | Move selected task down (lower priority) |
| `shift+enter` | Toggle task complete |
| `s` | Edit task |
| `n` | New task |
| `dd` | Delete task (vim-style double-tap) |
| `ctrl+d` | Page down |
| `ctrl+u` | Page up |
| `0–9` | Jump to task by number on current page |
| `q` | Quit |

## Storage

Tasks are stored in `~/.task-popper/tasks.json`. The store is path-configurable, with future support planned for per-directory task lists (detected via a local `.task-popper/` directory).

## Task Model

| Field | Description |
|---|---|
| `title` | Required |
| `description` | Optional |
| `due_date` | `YYYY-MM-DD` format; shown inline as "due today", "overdue 2d", "due Mar 25", etc. |
| `priority_order` | Position in list (lower = higher priority) |
| `completed` | Toggled via `shift+enter` |

The model is designed with room for future properties: checklists (sub-tasks), dependencies, tags, and more.
