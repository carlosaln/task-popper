from __future__ import annotations

import itertools
import time as _time
from datetime import date, datetime, time, timedelta
from math import ceil

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Input, Label, Static

from .config import (
    ACTIVE_CONFIG_PATH,
    DEFAULT_CONFIG_PATH,
    ScheduleConfig,
    TimeBlock,
    _parse_time,
    load_schedule_config,
    save_schedule_config,
)
from .store import PAGE_SIZE, TaskStore
from .widgets import GroupTaskRow, PriorityRow, ScheduleRow, TagFilterModal

EMPTY_MSG = "[dim]No tasks.[/dim]"


class PriorityStatusBar(Static):
    DEFAULT_CSS = """
    PriorityStatusBar {
        height: 1;
        background: $secondary-darken-2;
        color: $text;
        padding: 0 1;
    }
    """

    def update_status(self, page: int, total_pages: int, total_tasks: int, tag_filter: str | None = None) -> None:
        page_info = f"Page {page + 1}/{total_pages}  •  {total_tasks} task{'s' if total_tasks != 1 else ''}  •  sorted by priority"
        if tag_filter:
            page_info += f"  •  filter: [bold cyan]#{tag_filter}[/bold cyan]"
        self.update(page_info)


class PriorityScreen(Screen):
    """A full-screen view for reordering tasks by pure priority (no due-date influence)."""

    CSS = """
    #priority-header {
        height: 1;
        background: $secondary;
        color: $text;
        padding: 0 1;
        text-align: center;
        text-style: bold;
    }

    #priority-container {
        height: 1fr;
        padding: 0;
    }

    #priority-footer {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
        text-align: left;
    }

    PriorityRow {
        height: auto;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("J", "task_move_down", "Move↓", show=False),
        Binding("K", "task_move_up", "Move↑", show=False),
        Binding("ctrl+d", "page_down", "PgDn", show=True),
        Binding("ctrl+u", "page_up", "PgUp", show=True),
        Binding("p", "go_back", "Back", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

    def __init__(self, store: TaskStore) -> None:
        super().__init__()
        self.store = store
        self.current_page: int = 0
        self.cursor_index: int = 0
        self._active_tag_filter: str | None = None
        self._awaiting_second_f: bool = False
        self._last_f_time: float = 0.0

    def compose(self) -> ComposeResult:
        yield Static("# Priority Order", id="priority-header")
        yield PriorityStatusBar(id="priority-status")
        yield Vertical(id="priority-container")
        yield Static(
            " j/k navigate  •  J/K reorder  •  f filter  •  ff clear filter  •  0-9 jump  •  p back",
            id="priority-footer",
        )

    def on_mount(self) -> None:
        self._refresh_view()

    def _filtered_tasks(self) -> list:
        tasks = self.store.get_by_priority()
        if self._active_tag_filter:
            tasks = [t for t in tasks if self._active_tag_filter in t.tags]
        return tasks

    def _filtered_page(self, page: int) -> list:
        all_tasks = self._filtered_tasks()
        start = page * PAGE_SIZE
        return all_tasks[start : start + PAGE_SIZE]

    def _refresh_view(self) -> None:
        container = self.query_one("#priority-container", Vertical)
        container.remove_children()

        all_tasks = self._filtered_tasks()
        total = len(all_tasks)
        total_pages = max(1, ceil(total / PAGE_SIZE))

        if self.current_page >= total_pages:
            self.current_page = max(0, total_pages - 1)

        page_tasks = self._filtered_page(self.current_page)
        max_cursor = max(0, len(page_tasks) - 1)
        if self.cursor_index > max_cursor:
            self.cursor_index = max_cursor

        if not page_tasks:
            container.mount(Label(EMPTY_MSG))
        else:
            for i, task in enumerate(page_tasks):
                container.mount(PriorityRow(task, i, selected=(i == self.cursor_index)))

        self.query_one("#priority-status", PriorityStatusBar).update_status(
            self.current_page, total_pages, total, self._active_tag_filter
        )

    def _current_task(self):
        page_tasks = self._filtered_page(self.current_page)
        if not page_tasks or self.cursor_index >= len(page_tasks):
            return None
        return page_tasks[self.cursor_index]

    def on_key(self, event) -> None:
        key = event.key

        if len(key) == 1 and key.isdigit():
            idx = int(key)
            page_tasks = self._filtered_page(self.current_page)
            if idx < len(page_tasks):
                event.stop()
                self.cursor_index = idx
                self._refresh_view()
            return

        if key == "f":
            event.stop()
            now = _time.monotonic()
            if self._awaiting_second_f and (now - self._last_f_time) < 0.5:
                self._awaiting_second_f = False
                self._active_tag_filter = None
                self._refresh_view()
            else:
                self._awaiting_second_f = True
                self._last_f_time = now
                self.set_timer(0.25, self._maybe_open_filter_modal)
            return

        self._awaiting_second_f = False

    def _maybe_open_filter_modal(self) -> None:
        if not self._awaiting_second_f:
            return
        self._awaiting_second_f = False

        def on_result(tag: str | None) -> None:
            if tag is not None:
                self._active_tag_filter = tag
                self.current_page = 0
                self.cursor_index = 0
                self._refresh_view()

        self.app.push_screen(TagFilterModal(), on_result)

    def action_cursor_up(self) -> None:
        if self.cursor_index > 0:
            self.cursor_index -= 1
            self._refresh_view()
        elif self.current_page > 0:
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

    def action_task_move_up(self) -> None:
        task = self._current_task()
        if task is None:
            return
        self.store.move_up(task.id)
        filtered = self._filtered_tasks()
        new_idx = next((i for i, t in enumerate(filtered) if t.id == task.id), 0)
        self.current_page, self.cursor_index = divmod(new_idx, PAGE_SIZE)
        self._refresh_view()

    def action_task_move_down(self) -> None:
        task = self._current_task()
        if task is None:
            return
        self.store.move_down(task.id)
        filtered = self._filtered_tasks()
        new_idx = next((i for i, t in enumerate(filtered) if t.id == task.id), 0)
        self.current_page, self.cursor_index = divmod(new_idx, PAGE_SIZE)
        self._refresh_view()

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

    def action_go_back(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Schedule Screen
# ---------------------------------------------------------------------------

class ScheduleStatusBar(Static):
    DEFAULT_CSS = """
    ScheduleStatusBar {
        height: 1;
        background: $accent-darken-2;
        color: $text;
        padding: 0 1;
    }
    """

    def update_status(self, scheduled: int, total_mins: int, overflow: int) -> None:
        h, m = divmod(total_mins, 60)
        duration_str = f"{h}h{m:02d}m" if h else f"{m}m"
        overflow_str = f"  •  {overflow} unscheduled" if overflow else ""
        self.update(
            f"{scheduled} task{'s' if scheduled != 1 else ''} scheduled"
            f"  •  {duration_str} total{overflow_str}  •  today's schedule"
        )


class ScheduleScreen(Screen):
    """A full-screen view of today's scheduled task timeline."""

    CSS = """
    #schedule-header {
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
        text-align: center;
        text-style: bold;
    }

    #schedule-container {
        height: 1fr;
        padding: 0;
        overflow-y: auto;
    }

    #schedule-footer {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
        text-align: left;
    }

    ScheduleRow {
        height: auto;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("x", "complete_task", "Complete", show=True),
        Binding("r", "reschedule", "Reschedule", show=True),
        Binding("c", "configure", "Configure", show=True),
        Binding("t", "go_back", "Back", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

    def __init__(self, store: TaskStore) -> None:
        super().__init__()
        self.store = store
        self.cursor_index: int = 0
        self._slots: list = []
        self._overflow: list = []
        self._expanded_slot: int | None = None  # index of expanded group slot
        self._expanded_cursor: int = 0           # cursor within expanded group

    def compose(self) -> ComposeResult:
        today_str = date.today().strftime("%a %b %-d")
        yield Static(f"Today's Schedule — {today_str}", id="schedule-header")
        yield ScheduleStatusBar(id="schedule-status")
        yield Vertical(id="schedule-container")
        yield Static(
            " j/k navigate  •  x complete/expand  •  r reschedule  •  esc collapse  •  c configure  •  t back",
            id="schedule-footer",
        )

    def on_mount(self) -> None:
        self._build_schedule()

    def _build_schedule(self, from_time: datetime | None = None) -> None:
        from .config import load_schedule_config
        from .scheduler import build_schedule

        config = load_schedule_config()
        tasks = self.store.get_sorted()
        self._slots, self._overflow = build_schedule(tasks, config, from_time=from_time)
        self._expanded_slot = None
        self._expanded_cursor = 0
        self._refresh_view()

    def _refresh_view(self) -> None:
        container = self.query_one("#schedule-container", Vertical)
        container.remove_children()

        if not self._slots:
            container.mount(Label("[dim]No schedule — add tasks with durations.[/dim]"))
            self.query_one("#schedule-status", ScheduleStatusBar).update_status(0, 0, len(self._overflow))
            return

        max_cursor = max(0, len(self._slots) - 1)
        if self.cursor_index > max_cursor:
            self.cursor_index = max_cursor

        now = datetime.now()
        for i, slot in enumerate(self._slots):
            is_expanded = (self._expanded_slot == i)
            is_past = slot.end < now
            container.mount(ScheduleRow(slot, i, selected=(i == self.cursor_index), past=is_past))
            if is_expanded and slot.group:
                for gi, task in enumerate(slot.group):
                    container.mount(GroupTaskRow(task, selected=(gi == self._expanded_cursor), past=is_past))

        # Count scheduled tasks and total duration
        scheduled_count = sum(
            1 for s in self._slots
            if s.slot_type == "task" and (s.task is not None or s.group)
        )
        # Count individual tasks in groups
        scheduled_count = sum(
            (len(s.group) if s.group else 1)
            for s in self._slots
            if s.slot_type == "task"
        )
        total_mins = sum(
            int((s.end - s.start).total_seconds() / 60)
            for s in self._slots
            if s.slot_type == "task"
        )

        self.query_one("#schedule-status", ScheduleStatusBar).update_status(
            scheduled_count, total_mins, len(self._overflow)
        )

        # Show overflow notice if any tasks didn't fit
        if self._overflow:
            titles = ", ".join(t.title for t in self._overflow[:3])
            if len(self._overflow) > 3:
                titles += f" +{len(self._overflow) - 3} more"
            container.mount(
                Label(f"\n  [dim]Unscheduled ({len(self._overflow)}): {titles}[/dim]")
            )

    def action_cursor_up(self) -> None:
        if self._expanded_slot is not None:
            if self._expanded_cursor > 0:
                self._expanded_cursor -= 1
                self._refresh_view()
            return
        if self.cursor_index > 0:
            self.cursor_index -= 1
            self._refresh_view()

    def action_cursor_down(self) -> None:
        if self._expanded_slot is not None:
            slot = self._slots[self._expanded_slot]
            if self._expanded_cursor < len(slot.group) - 1:
                self._expanded_cursor += 1
                self._refresh_view()
            return
        if self.cursor_index < len(self._slots) - 1:
            self.cursor_index += 1
            self._refresh_view()

    def action_complete_task(self) -> None:
        if not self._slots or self.cursor_index >= len(self._slots):
            return
        slot = self._slots[self.cursor_index]
        if slot.slot_type != "task":
            return
        if self._expanded_slot is not None:
            # Complete the single task at the expanded cursor
            task = slot.group[self._expanded_cursor]
            if task.completed:
                return
            self.store.complete(task.id)
            task.completed = True
            self._refresh_view()
        elif slot.group:
            # Expand the group instead of completing
            self._expanded_slot = self.cursor_index
            self._expanded_cursor = 0
            self._refresh_view()
        elif slot.task:
            if slot.task.completed:
                return
            if slot.chunk_index is not None:
                # Chunked task: complete only this chunk's worth of time
                chunk_minutes = int((slot.end - slot.start).total_seconds() / 60)
                fully_done = self.store.complete_chunk(slot.task.id, chunk_minutes)
                if fully_done:
                    slot.task.completed = True
                # Remove this chunk from the schedule view
                self._slots.pop(self.cursor_index)
                # Also remove the break slot immediately after, if any
                if (self.cursor_index < len(self._slots)
                        and self._slots[self.cursor_index].slot_type == "break"):
                    self._slots.pop(self.cursor_index)
                if self.cursor_index >= len(self._slots) and self._slots:
                    self.cursor_index = len(self._slots) - 1
                self._refresh_view()
            else:
                self.store.complete(slot.task.id)
                slot.task.completed = True
                self._refresh_view()

    def action_reschedule(self) -> None:
        """Rebuild the schedule, only rescheduling from the current time onward."""
        self._build_schedule(from_time=datetime.now())

    def action_configure(self) -> None:
        config = load_schedule_config()

        def on_return(result: ScheduleConfig | None) -> None:
            if result is not None:
                self._build_schedule()

        self.app.push_screen(ScheduleConfigScreen(config), on_return)

    def action_go_back(self) -> None:
        if self._expanded_slot is not None:
            self._expanded_slot = None
            self._refresh_view()
            return
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Schedule Config Screen — timeline-based editor
# ---------------------------------------------------------------------------

def _fmt_time(t: time) -> str:
    """Format a time as '9:00am', '12:30pm', etc."""
    return t.strftime("%I:%M%p").lstrip("0").lower()


class _TimelineRow(Static):
    """One 15-minute row in the schedule config timeline."""

    DEFAULT_CSS = """
    _TimelineRow {
        height: 1;
        padding: 0 1;
    }
    _TimelineRow.tl-selected {
        background: $primary 20%;
    }
    """

    def __init__(self, slot_time: time, stype: str, selected: bool) -> None:
        super().__init__()
        self._slot_time = slot_time
        self._stype = stype
        self._selected = selected
        if selected:
            self.add_class("tl-selected")

    def render(self) -> Text:
        text = Text(no_wrap=True, overflow="ellipsis")
        time_str = f"{_fmt_time(self._slot_time):>8}"
        indicator = "▸ " if self._selected else "  "

        if self._stype == "blocked":
            text.append(f"  {time_str}  ", style="dim")
            text.append(indicator, style="bold red" if self._selected else "dim red")
            text.append("▌▌  Blocked", style="bold red")
        elif self._stype == "low_burn":
            text.append(f"  {time_str}  ", style="dim")
            text.append(indicator, style="bold yellow" if self._selected else "dim yellow")
            text.append("▌▌  Low-burn", style="bold yellow")
        else:
            text.append(f"  {time_str}  ", style="bold cyan" if self._selected else "dim")
            text.append(indicator, style="bold green" if self._selected else "dim")
            text.append("▌▌  Normal", style="bold green" if self._selected else "dim green")

        return text


class _ScheduleSettingsModal(ModalScreen):
    """Small modal for editing scalar schedule settings (day bounds, break %, etc.)."""

    DEFAULT_CSS = """
    _ScheduleSettingsModal {
        align: center middle;
    }
    #settings-dialog {
        padding: 1 2;
        background: $surface;
        border: thick $primary;
        width: 52;
        height: auto;
    }
    #settings-title {
        text-align: center;
        color: $primary;
        margin-bottom: 1;
    }
    .s-label {
        color: $text-muted;
        margin-top: 1;
    }
    #settings-error { height: 1; }
    #settings-buttons {
        margin-top: 1;
        height: auto;
        align: right middle;
    }
    Button { margin-left: 1; }
    """

    def __init__(self, day_start: time, day_end: time, break_pct: int,
                 short_thresh: int, min_chunk: int, max_chunk: int, low_prio: float) -> None:
        super().__init__()
        self._day_start = day_start
        self._day_end = day_end
        self._break_pct = break_pct
        self._short_thresh = short_thresh
        self._min_chunk = min_chunk
        self._max_chunk = max_chunk
        self._low_prio = low_prio

    def compose(self) -> ComposeResult:
        with Container(id="settings-dialog"):
            yield Label("Day Settings", id="settings-title")
            yield Label("Day start (HH:MM)", classes="s-label")
            yield Input(value=self._day_start.strftime("%H:%M"), id="s-day-start")
            yield Label("Day end (HH:MM)", classes="s-label")
            yield Input(value=self._day_end.strftime("%H:%M"), id="s-day-end")
            yield Label("Break % — gap after each task", classes="s-label")
            yield Input(value=str(self._break_pct), id="s-break-pct")
            yield Label("Short task threshold (min) — tasks ≤ this are bunched", classes="s-label")
            yield Input(value=str(self._short_thresh), id="s-short-thresh")
            yield Label("Min work chunk (min) — smallest partial session for a long task", classes="s-label")
            yield Input(value=str(self._min_chunk), id="s-min-chunk")
            yield Label("Max work chunk (min) — caps bunched short tasks and splits long ones", classes="s-label")
            yield Input(value=str(self._max_chunk), id="s-max-chunk")
            yield Label("Low-priority cutoff (0.0–1.0)", classes="s-label")
            yield Input(value=str(self._low_prio), id="s-low-prio")
            yield Label("", id="settings-error")
            with Horizontal(id="settings-buttons"):
                yield Button("Apply  [enter]", variant="primary", id="s-btn-apply")
                yield Button("Cancel  [esc]", id="s-btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#s-day-start", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "s-btn-apply":
            self._apply()
        else:
            self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
        elif event.key == "enter":
            event.stop()
            self._apply()

    def _apply(self) -> None:
        err = self.query_one("#settings-error", Label)

        def get(id_: str) -> str:
            return self.query_one(id_, Input).value.strip()

        try:
            day_start = _parse_time(get("#s-day-start"))
        except ValueError:
            err.update("[bold red]Invalid day start (use HH:MM)[/bold red]")
            self.query_one("#s-day-start", Input).focus()
            return

        try:
            day_end = _parse_time(get("#s-day-end"))
        except ValueError:
            err.update("[bold red]Invalid day end (use HH:MM)[/bold red]")
            self.query_one("#s-day-end", Input).focus()
            return

        try:
            break_pct = int(get("#s-break-pct"))
            assert 0 <= break_pct <= 100
        except (ValueError, AssertionError):
            err.update("[bold red]Break % must be 0–100[/bold red]")
            self.query_one("#s-break-pct", Input).focus()
            return

        try:
            short_thresh = int(get("#s-short-thresh"))
            assert short_thresh > 0
        except (ValueError, AssertionError):
            err.update("[bold red]Short threshold must be a positive integer[/bold red]")
            self.query_one("#s-short-thresh", Input).focus()
            return

        try:
            min_chunk = int(get("#s-min-chunk"))
            assert min_chunk > 0
        except (ValueError, AssertionError):
            err.update("[bold red]Min chunk must be a positive integer[/bold red]")
            self.query_one("#s-min-chunk", Input).focus()
            return

        try:
            max_chunk = int(get("#s-max-chunk"))
            assert max_chunk > 0
        except (ValueError, AssertionError):
            err.update("[bold red]Max chunk must be a positive integer[/bold red]")
            self.query_one("#s-max-chunk", Input).focus()
            return

        if min_chunk > max_chunk:
            err.update("[bold red]Min chunk must be ≤ max chunk[/bold red]")
            self.query_one("#s-min-chunk", Input).focus()
            return

        try:
            low_prio = float(get("#s-low-prio"))
            assert 0.0 <= low_prio <= 1.0
        except (ValueError, AssertionError):
            err.update("[bold red]Low-priority cutoff must be 0.0–1.0[/bold red]")
            self.query_one("#s-low-prio", Input).focus()
            return

        self.dismiss((day_start, day_end, break_pct, short_thresh, min_chunk, max_chunk, low_prio))


class ScheduleConfigScreen(Screen):
    """Timeline-based schedule editor. Navigate 15-min slots, mark as normal/low-burn/blocked."""

    CSS = """
    #cfg-header {
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
        text-align: center;
        text-style: bold;
    }
    #cfg-settings-bar {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
    }
    #cfg-timeline {
        height: 1fr;
        overflow-y: auto;
    }
    #cfg-actions {
        height: auto;
        align: left middle;
        padding: 0 1;
        background: $surface;
    }
    #cfg-actions Button {
        margin-right: 1;
    }
    #cfg-footer {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    _TimelineRow { height: 1; }
    """

    BINDINGS = [
        Binding("up",   "cursor_up",   "Up",       show=False),
        Binding("k",    "cursor_up",   "Up",       show=False),
        Binding("down", "cursor_down", "Down",     show=False),
        Binding("j",    "cursor_down", "Down",     show=False),
        Binding("K",    "jump_up",     "1hr↑",     show=False),
        Binding("J",    "jump_down",   "1hr↓",     show=False),
        Binding("n",    "set_normal",  "Normal",   show=True),
        Binding("b",    "set_blocked", "Block",    show=True),
        Binding("l",    "set_low_burn","Low-burn", show=True),
        Binding("o",    "open_settings","Settings",show=True),
        Binding("ctrl+s","save",       "Save",     show=True),
        Binding("S",    "save_default","Save Def.", show=True),
        Binding("R",    "reset_default","Reset",   show=True),
        Binding("escape","go_back",    "Back",     show=False),
    ]

    def __init__(self, config: ScheduleConfig) -> None:
        super().__init__()
        self._config = config
        self._cursor: int = 0
        # Each slot: [slot_time: time, stype: str]
        self._slots: list[list] = []
        self._day_start: time = config.work_start
        self._day_end: time = config.extended_end or config.work_end
        self._break_pct: int = config.break_percent
        self._short_thresh: int = config.short_task_threshold
        self._min_chunk: int = config.min_chunk_duration
        self._max_chunk: int = config.max_chunk_duration
        self._low_prio: float = config.low_priority_threshold

    def compose(self) -> ComposeResult:
        yield Static("Schedule Configuration", id="cfg-header")
        yield Static("", id="cfg-settings-bar")
        yield Vertical(id="cfg-timeline")
        with Horizontal(id="cfg-actions"):
            yield Button("Save  [ctrl+s]", variant="primary", id="cfg-btn-save")
            yield Button("Save as Default  [S]", id="cfg-btn-save-default")
            yield Button("Reset to Default  [R]", variant="warning", id="cfg-btn-reset")
            yield Button("Cancel  [esc]", id="cfg-btn-cancel")
        yield Static(
            " j/k 15m  J/K 1h  n normal  b block  l low-burn  o settings",
            id="cfg-footer",
        )

    def on_mount(self) -> None:
        self._build_timeline()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cfg-btn-save":
            self.action_save()
        elif event.button.id == "cfg-btn-save-default":
            self.action_save_default()
        elif event.button.id == "cfg-btn-reset":
            self.action_reset_default()
        elif event.button.id == "cfg-btn-cancel":
            self.dismiss(None)

    # ------------------------------------------------------------------
    # Timeline construction
    # ------------------------------------------------------------------

    def _build_timeline(self) -> None:
        today = date.today()
        t = datetime.combine(today, self._day_start)
        end_dt = datetime.combine(today, self._day_end)

        self._slots = []
        while t < end_dt:
            self._slots.append([t.time(), "normal"])
            t += timedelta(minutes=15)

        # Apply blocked periods
        for blk in self._config.blocked:
            for slot in self._slots:
                if blk.start <= slot[0] < blk.end:
                    slot[1] = "blocked"

        # Apply low_burn periods (only override normal slots)
        for lb in self._config.low_burn:
            for slot in self._slots:
                if lb.start <= slot[0] < lb.end and slot[1] == "normal":
                    slot[1] = "low_burn"

        self._cursor = min(self._cursor, max(0, len(self._slots) - 1))
        self._refresh_view()

    def _refresh_view(self) -> None:
        container = self.query_one("#cfg-timeline", Vertical)
        container.remove_children()

        if not self._slots:
            container.mount(Label("[dim]No slots — check day start/end in settings (o).[/dim]"))
            self._update_settings_bar()
            return

        if self._cursor >= len(self._slots):
            self._cursor = len(self._slots) - 1

        selected_widget = None
        for i, (slot_time, stype) in enumerate(self._slots):
            row = _TimelineRow(slot_time, stype, selected=(i == self._cursor))
            container.mount(row)
            if i == self._cursor:
                selected_widget = row

        self._update_settings_bar()
        if selected_widget:
            self.call_after_refresh(
                container.scroll_to_widget, selected_widget, animate=False
            )

    def _update_settings_bar(self) -> None:
        self.query_one("#cfg-settings-bar", Static).update(
            f" Day: {_fmt_time(self._day_start)}–{_fmt_time(self._day_end)}"
            f"  |  Break: {self._break_pct}%"
            f"  |  Short ≤{self._short_thresh}m"
            f"  |  Chunk {self._min_chunk}–{self._max_chunk}m"
            f"  |  Low-prio: {int(self._low_prio * 100)}%"
            f"  [dim]o: edit[/dim]"
        )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def action_cursor_up(self) -> None:
        if self._cursor > 0:
            self._cursor -= 1
            self._refresh_view()

    def action_cursor_down(self) -> None:
        if self._cursor < len(self._slots) - 1:
            self._cursor += 1
            self._refresh_view()

    def action_jump_up(self) -> None:
        self._cursor = max(0, self._cursor - 4)
        self._refresh_view()

    def action_jump_down(self) -> None:
        self._cursor = min(len(self._slots) - 1, self._cursor + 4)
        self._refresh_view()

    # ------------------------------------------------------------------
    # Slot type actions
    # ------------------------------------------------------------------

    def action_set_normal(self) -> None:
        if self._slots:
            self._slots[self._cursor][1] = "normal"
            self._refresh_view()

    def action_set_blocked(self) -> None:
        if self._slots:
            self._slots[self._cursor][1] = "blocked"
            self._refresh_view()

    def action_set_low_burn(self) -> None:
        if self._slots:
            self._slots[self._cursor][1] = "low_burn"
            self._refresh_view()

    # ------------------------------------------------------------------
    # Settings modal
    # ------------------------------------------------------------------

    def action_open_settings(self) -> None:
        def on_result(result) -> None:
            if result is None:
                return
            day_start, day_end, break_pct, short_thresh, min_chunk, max_chunk, low_prio = result
            old_start, old_end = self._day_start, self._day_end
            self._day_start = day_start
            self._day_end = day_end
            self._break_pct = break_pct
            self._short_thresh = short_thresh
            self._min_chunk = min_chunk
            self._max_chunk = max_chunk
            self._low_prio = low_prio

            if day_start != old_start or day_end != old_end:
                # Preserve existing slot types for slots that still exist
                old_types = {s[0]: s[1] for s in self._slots}
                self._build_timeline()
                for slot in self._slots:
                    if slot[0] in old_types:
                        slot[1] = old_types[slot[0]]
                self._refresh_view()
            else:
                self._refresh_view()

        self.app.push_screen(
            _ScheduleSettingsModal(
                self._day_start, self._day_end,
                self._break_pct, self._short_thresh, self._min_chunk, self._max_chunk, self._low_prio,
            ),
            on_result,
        )

    # ------------------------------------------------------------------
    # Save / reset
    # ------------------------------------------------------------------

    def _to_config(self) -> ScheduleConfig:
        """Convert current timeline state to a ScheduleConfig."""
        blocked: list[TimeBlock] = []
        low_burn: list[TimeBlock] = []
        today = date.today()
        for stype, group in itertools.groupby(self._slots, key=lambda s: s[1]):
            group_list = list(group)
            start = group_list[0][0]
            end = (
                datetime.combine(today, group_list[-1][0]) + timedelta(minutes=15)
            ).time()
            if stype == "blocked":
                blocked.append(TimeBlock(start=start, end=end))
            elif stype == "low_burn":
                low_burn.append(TimeBlock(start=start, end=end))

        return ScheduleConfig(
            work_start=self._day_start,
            work_end=self._day_end,
            extended_end=None,
            break_percent=self._break_pct,
            short_task_threshold=self._short_thresh,
            min_chunk_duration=self._min_chunk,
            max_chunk_duration=self._max_chunk,
            low_priority_threshold=self._low_prio,
            blocked=blocked,
            low_burn=low_burn,
        )

    def action_save(self) -> None:
        config = self._to_config()
        save_schedule_config(config, ACTIVE_CONFIG_PATH)
        self.dismiss(config)

    def action_save_default(self) -> None:
        config = self._to_config()
        save_schedule_config(config, ACTIVE_CONFIG_PATH)
        save_schedule_config(config, DEFAULT_CONFIG_PATH)
        self.dismiss(config)

    def action_reset_default(self) -> None:
        default = load_schedule_config(DEFAULT_CONFIG_PATH)
        save_schedule_config(default, ACTIVE_CONFIG_PATH)
        self._day_start = default.work_start
        self._day_end = default.extended_end or default.work_end
        self._break_pct = default.break_percent
        self._short_thresh = default.short_task_threshold
        self._min_chunk = default.min_chunk_duration
        self._max_chunk = default.max_chunk_duration
        self._low_prio = default.low_priority_threshold
        self._config = default
        self._cursor = 0
        self._build_timeline()

    def action_go_back(self) -> None:
        self.dismiss(None)
