from __future__ import annotations

import time
from math import ceil

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Label, Static

from .models import Task
from .store import PAGE_SIZE, TaskStore
from .widgets import EditTaskModal, TagFilterModal, TaskRow, _format_duration

EMPTY_MSG = "[dim]No tasks. Press [bold]n[/bold] to create one.[/dim]"


class StatusBar(Static):
    """Page indicator and shortcut hints strip."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary-darken-2;
        color: $text;
        padding: 0 1;
    }
    """

    def update_status(self, page: int, total_pages: int, total_tasks: int, tag_filter: str | None = None) -> None:
        page_info = f"Page {page + 1}/{total_pages}  •  {total_tasks} task{'s' if total_tasks != 1 else ''}"
        if tag_filter:
            page_info += f"  •  filter: [bold cyan]#{tag_filter}[/bold cyan]"
        self.update(page_info)


class TaskPopperApp(App):
    TITLE = "Task Popper"

    CSS = """
    Screen {
        background: $background;
    }

    #app-header {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
        text-align: center;
        text-style: bold;
    }

    #task-container {
        height: 1fr;
        padding: 0;
    }

    #empty-state {
        height: 1fr;
        align: center middle;
    }

    TaskRow {
        height: auto;
    }

    #footer-hints {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
        text-align: left;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("x", "complete_task", "Complete", show=False),
        Binding("p", "priority_screen", "Priority", show=True),
        Binding("t", "schedule_screen", "Today", show=True),
        Binding("c", "configure_schedule", "Configure", show=True),
        Binding("s", "edit_task", "Edit", show=True),
        Binding("n", "new_task", "New", show=True),
        Binding("ctrl+d", "page_down", "PgDn", show=True),
        Binding("ctrl+u", "page_up", "PgUp", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    # Reactive state
    current_page: reactive[int] = reactive(0)
    cursor_index: reactive[int] = reactive(0)

    def __init__(self) -> None:
        super().__init__()
        self.store = TaskStore()
        self._last_d_time: float = 0.0
        self._awaiting_second_d: bool = False
        self._last_f_time: float = 0.0
        self._awaiting_second_f: bool = False
        self._active_tag_filter: str | None = None
        self._task_cache: list[Task] = []

    # ------------------------------------------------------------------ #
    # Composition                                                          #
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield Static("⚡ Task Popper", id="app-header")
        yield StatusBar(id="status-bar")
        yield Vertical(id="task-container")
        yield Static(
            " j/k navigate  •  p priority  •  t today  •  n new  •  s edit  •  x complete  •  f filter  •  ff clear filter  •  dd delete",
            id="footer-hints",
        )

    def on_mount(self) -> None:
        self._refresh_view()

    # ------------------------------------------------------------------ #
    # View refresh                                                         #
    # ------------------------------------------------------------------ #

    def _filtered_tasks(self) -> list[Task]:
        tasks = self.store.get_sorted()
        if self._active_tag_filter:
            tasks = [t for t in tasks if self._active_tag_filter in t.tags]
        return tasks

    def _filtered_page(self, page: int) -> list[Task]:
        all_tasks = self._filtered_tasks()
        start = page * PAGE_SIZE
        return all_tasks[start : start + PAGE_SIZE]

    def _refresh_view(self) -> None:
        container = self.query_one("#task-container", Vertical)
        container.remove_children()

        self._task_cache = self._filtered_tasks()
        total = len(self._task_cache)
        total_pages = max(1, ceil(total / PAGE_SIZE))

        # Clamp page and cursor
        if self.current_page >= total_pages:
            self.current_page = max(0, total_pages - 1)

        page_tasks = self._filtered_page(self.current_page)
        max_cursor = max(0, len(page_tasks) - 1)
        if self.cursor_index > max_cursor:
            self.cursor_index = max_cursor

        if not page_tasks:
            container.mount(Label(EMPTY_MSG, id="empty-state"))
        else:
            for i, task in enumerate(page_tasks):
                container.mount(TaskRow(task, i, selected=(i == self.cursor_index)))

        # Update status bar
        self.query_one("#status-bar", StatusBar).update_status(
            self.current_page, total_pages, total, self._active_tag_filter
        )

    def _current_task(self) -> Task | None:
        page_tasks = self._filtered_page(self.current_page)
        if not page_tasks or self.cursor_index >= len(page_tasks):
            return None
        return page_tasks[self.cursor_index]

    # ------------------------------------------------------------------ #
    # Key handling (dd, 0-9 jumps)                                        #
    # ------------------------------------------------------------------ #

    def on_key(self, event) -> None:
        key = event.key

        # Digit jump: 0-9 jumps to that task index on current page
        if len(key) == 1 and key.isdigit():
            idx = int(key)
            page_tasks = self.store.get_page(self.current_page)
            if idx < len(page_tasks):
                event.stop()
                self.cursor_index = idx
                self._refresh_view()
            self._awaiting_second_d = False
            return

        # dd delete (vim-style)
        if key == "d":
            event.stop()
            now = time.monotonic()
            if self._awaiting_second_d and (now - self._last_d_time) < 0.5:
                self._awaiting_second_d = False
                self._do_delete()
            else:
                self._awaiting_second_d = True
                self._last_d_time = now
            return

        # f / ff — filter by tag (ff clears the filter)
        if key == "f":
            event.stop()
            now = time.monotonic()
            if self._awaiting_second_f and (now - self._last_f_time) < 0.5:
                # ff: clear filter
                self._awaiting_second_f = False
                self._active_tag_filter = None
                self._refresh_view()
            else:
                self._awaiting_second_f = True
                self._last_f_time = now
                self.set_timer(0.25, self._maybe_open_filter_modal)
            return

        # Any other key resets dd/ff state
        self._awaiting_second_d = False
        self._awaiting_second_f = False

    # ------------------------------------------------------------------ #
    # Actions                                                              #
    # ------------------------------------------------------------------ #

    def action_cursor_up(self) -> None:
        if self.cursor_index > 0:
            self.cursor_index -= 1
            self._refresh_view()
        elif self.current_page > 0:
            # Wrap to previous page, select last item
            self.current_page -= 1
            page_tasks = self._filtered_page(self.current_page)
            self.cursor_index = max(0, len(page_tasks) - 1)
            self._refresh_view()

    def action_cursor_down(self) -> None:
        page_tasks = self._filtered_page(self.current_page)
        if self.cursor_index < len(page_tasks) - 1:
            self.cursor_index += 1
            self._refresh_view()
        else:
            total = len(self._filtered_tasks())
            total_pages = max(1, ceil(total / PAGE_SIZE))
            if self.current_page < total_pages - 1:
                self.current_page += 1
                self.cursor_index = 0
                self._refresh_view()

    def action_complete_task(self) -> None:
        task = self._current_task()
        if task is None:
            return
        self.store.complete(task.id)
        self._refresh_view()

    def action_new_task(self) -> None:
        def on_result(result: tuple[str, str, str, int | None, list[str], str] | None) -> None:
            if result is None:
                return
            title, desc, due, duration, tags, start_date = result
            new_task = Task(
                title=title,
                description=desc,
                due_date=due or None,
                duration=duration,
                tags=tags,
                start_date=start_date or None,
            )
            self.store.add(new_task)
            tasks = self.store.get_sorted()
            idx = next((i for i, t in enumerate(tasks) if t.id == new_task.id), 0)
            self.current_page, self.cursor_index = divmod(idx, PAGE_SIZE)
            self._refresh_view()

        self.push_screen(EditTaskModal(heading="New Task"), on_result)

    def action_edit_task(self) -> None:
        task = self._current_task()
        if task is None:
            return

        def on_result(result: tuple[str, str, str, int | None, list[str], str] | None) -> None:
            if result is None:
                return
            title, desc, due, duration, tags, start_date = result
            task.title = title
            task.description = desc
            task.due_date = due or None
            task.duration = duration
            task.tags = tags
            task.start_date = start_date or None
            self.store.update(task)
            self._refresh_view()

        # Reconstruct title with tags and duration suffix so the user can see/edit it
        edit_title = task.title
        if task.tags:
            edit_title = edit_title + " " + " ".join(f"#{t}" for t in task.tags)
        if task.duration:
            edit_title = f"{edit_title} {_format_duration(task.duration)}"

        self.push_screen(
            EditTaskModal(
                title=edit_title,
                description=task.description,
                due_date=task.due_date or "",
                start_date=task.start_date or "",
                heading="Edit Task",
            ),
            on_result,
        )

    def action_priority_screen(self) -> None:
        from .screens import PriorityScreen

        def on_return(result=None) -> None:
            self._refresh_view()

        self.push_screen(PriorityScreen(self.store), on_return)

    def action_schedule_screen(self) -> None:
        from .screens import ScheduleScreen

        def on_return(result=None) -> None:
            self._refresh_view()

        self.push_screen(ScheduleScreen(self.store), on_return)

    def action_configure_schedule(self) -> None:
        from .config import load_schedule_config
        from .screens import ScheduleConfigScreen

        config = load_schedule_config()

        def on_return(result=None) -> None:
            self._refresh_view()

        self.push_screen(ScheduleConfigScreen(config), on_return)

    def action_page_down(self) -> None:
        total = len(self._filtered_tasks())
        total_pages = max(1, ceil(total / PAGE_SIZE))
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.cursor_index = 0
            self._refresh_view()

    def action_page_up(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.cursor_index = 0
            self._refresh_view()

    def _maybe_open_filter_modal(self) -> None:
        if not self._awaiting_second_f:
            return  # ff was detected, timer fired but flag already cleared
        self._awaiting_second_f = False

        def on_result(tag: str | None) -> None:
            if tag is not None:
                self._active_tag_filter = tag
                self.current_page = 0
                self.cursor_index = 0
                self._refresh_view()

        self.push_screen(TagFilterModal(), on_result)

    def _do_delete(self) -> None:
        task = self._current_task()
        if task is None:
            return
        self.store.delete(task.id)
        # Keep cursor in bounds
        page_tasks = self.store.get_page(self.current_page)
        if self.cursor_index >= len(page_tasks) and self.cursor_index > 0:
            self.cursor_index -= 1
        self._refresh_view()
