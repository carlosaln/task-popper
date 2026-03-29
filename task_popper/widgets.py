from __future__ import annotations

import re
from datetime import date, datetime, timedelta

import dateparser

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static
from rich.text import Text

from .models import Task

_WEEKDAY_NAMES = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}


def _next_weekday(target_wd: int, after: date) -> date:
    """Return the first occurrence of target_wd (0=Mon…6=Sun) strictly after `after`."""
    days = (target_wd - after.weekday()) % 7 or 7
    return after + timedelta(days=days)


_TIME_WORDS = {
    "midnight": "00:00",
    "noon": "12:00",
    "midday": "12:00",
}

_TIME_PATTERN = re.compile(
    r"^(?P<base>.+?)\s+by\s+(?P<time>\S+)$",
    re.IGNORECASE,
)

_CLOCK_PATTERN = re.compile(
    r"^(?P<hour>\d{1,2})(?::(?P<min>\d{2}))?(?P<ampm>am|pm)?$",
    re.IGNORECASE,
)


def _parse_time_str(time_str: str) -> str | None:
    """Parse a time string like '8PM', '5pm', '14:30', 'noon' into 'HH:MM'. Returns None on failure."""
    t = time_str.strip().lower()
    if t in _TIME_WORDS:
        return _TIME_WORDS[t]
    m = _CLOCK_PATTERN.fullmatch(t)
    if not m:
        return None
    hour = int(m.group("hour"))
    minute = int(m.group("min")) if m.group("min") else 0
    ampm = m.group("ampm")
    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"


def _pre_parse(text: str) -> date | None:
    """Handle patterns dateparser misses: 'next <weekday>', 'this <weekday>'."""
    t = text.lower().strip()
    today = date.today()

    # "next <weekday>" → the weekday after the upcoming one
    m = re.fullmatch(r"next\s+(\w+)", t)
    if m and m.group(1) in _WEEKDAY_NAMES:
        upcoming = _next_weekday(_WEEKDAY_NAMES[m.group(1)], today)
        return upcoming + timedelta(weeks=1)

    # "this <weekday>" → the upcoming occurrence (same as bare weekday)
    m = re.fullmatch(r"this\s+(\w+)", t)
    if m and m.group(1) in _WEEKDAY_NAMES:
        return _next_weekday(_WEEKDAY_NAMES[m.group(1)], today)

    return None


def parse_due_date(text: str) -> str | None:
    """Parse a due date (with optional time) from natural language or ISO format.

    Returns an ISO string: "YYYY-MM-DD" when no time is present, or
    "YYYY-MM-DDTHH:MM" when a time component is parsed. Returns None on failure.
    """
    text = text.strip()
    if not text:
        return None

    # Strict ISO datetime fast path: "2026-04-01T14:30"
    try:
        dt = datetime.fromisoformat(text)
        return dt.strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        pass

    # Strict ISO date fast path: "2026-04-01"
    try:
        d = date.fromisoformat(text)
        return d.isoformat()
    except ValueError:
        pass

    # "... by <time>" pattern — split and parse each part separately
    m = _TIME_PATTERN.match(text)
    if m:
        base_text = m.group("base").strip()
        time_str = m.group("time").strip()
        parsed_time = _parse_time_str(time_str)
        if parsed_time:
            # Parse the base date part
            base_date = _parse_date_only(base_text)
            if base_date is not None:
                return f"{base_date.isoformat()}T{parsed_time}"

    # Pre-parser for patterns dateparser misses
    pre = _pre_parse(text)
    if pre is not None:
        return pre.isoformat()

    # General natural language fallback
    parsed = dateparser.parse(
        text,
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )
    return parsed.date().isoformat() if parsed else None


def _parse_date_only(text: str) -> date | None:
    """Internal helper: parse a date-only string (no time component)."""
    text = text.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    pre = _pre_parse(text)
    if pre is not None:
        return pre
    parsed = dateparser.parse(
        text,
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )
    return parsed.date() if parsed else None


def parse_tags(title: str) -> tuple[str, list[str]]:
    """Extract #hashtag tokens from a title. Returns (cleaned_title, tags_list)."""
    tags = re.findall(r"#(\w+)", title)
    cleaned = re.sub(r"\s*#\w+", "", title).strip()
    return cleaned, tags


def parse_duration(title: str) -> tuple[str, int | None]:
    """Extract an optional duration suffix from the last word of a title.

    Recognises: 30m, 3h, 1h30m. Returns (cleaned_title, minutes_or_None).
    """
    parts = title.rsplit(None, 1)
    if len(parts) == 2:
        last = parts[1]
        m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?", last)
        if m and (m.group(1) or m.group(2)):
            hours = int(m.group(1)) if m.group(1) else 0
            mins = int(m.group(2)) if m.group(2) else 0
            return parts[0], hours * 60 + mins
    return title, None


def _format_duration(minutes: int) -> str:
    """Format minutes as a human-readable duration string."""
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h{m}m"
    elif h:
        return f"{h}h"
    else:
        return f"{m}m"


def _format_due(due_date: str) -> tuple[str, str]:
    """Return (label, style) for a stored due date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM)."""
    has_time = "T" in due_date
    try:
        if has_time:
            due_dt = datetime.fromisoformat(due_date)
            due = due_dt.date()
            time_suffix = f" ({due_dt.strftime('%I:%M%p').lstrip('0').lower()})"
        else:
            due = date.fromisoformat(due_date)
            time_suffix = ""
    except ValueError:
        return due_date, "dim"
    today = date.today()
    delta = (due - today).days
    if delta < 0:
        label = f"overdue {-delta}d{time_suffix}"
        style = "bold red"
    elif delta == 0:
        label = f"due today{time_suffix}"
        style = "bold yellow"
    elif delta == 1:
        label = f"due tomorrow{time_suffix}"
        style = "yellow"
    elif delta <= 7:
        label = f"due in {delta}d{time_suffix}"
        style = "dim"
    else:
        date_str = due.strftime("%b %-d") if due.year == today.year else due.strftime("%b %-d %Y")
        label = f"due {date_str}{time_suffix}"
        style = "dim"
    return label, style


class TaskRow(Static):
    """Renders a single task row: index, cursor indicator, title, optional description."""

    DEFAULT_CSS = """
    TaskRow {
        height: auto;
        padding: 0 1;
    }
    TaskRow.selected {
        background: $primary 20%;
    }
    """

    def __init__(self, data: Task, page_index: int, selected: bool) -> None:
        super().__init__()
        self.data = data
        self.page_index = page_index
        self._selected = selected
        if selected:
            self.add_class("selected")

    def render(self) -> Text:
        text = Text(no_wrap=True, overflow="ellipsis")

        index_str = f" {self.page_index} "
        indicator = "▸ " if self._selected else "  "

        if self.data.completed:
            text.append(index_str, style="dim")
            text.append(indicator, style="dim")
            text.append(self.data.title, style="dim strike")
        else:
            text.append(index_str, style="bold cyan")
            text.append(indicator, style="bold green" if self._selected else "dim")
            text.append(self.data.title, style="bold")
            if self.data.tags:
                text.append("  " + " ".join(f"#{t}" for t in self.data.tags), style="dim cyan")
            if self.data.due_date:
                label, style = _format_due(self.data.due_date)
                text.append(f"  {label}", style=style)
            if self.data.duration:
                text.append(f"  ~{_format_duration(self.data.duration)}", style="dim")
            if self.data.start_date:
                try:
                    start_dt = datetime.fromisoformat(self.data.start_date)
                    if start_dt > datetime.now():
                        start_friendly = start_dt.strftime("%b %-d") if "T" not in self.data.start_date else start_dt.strftime("%b %-d %-I%p").lower()
                        text.append(f"  starts {start_friendly}", style="dim")
                except ValueError:
                    pass

        second_line = self.data.description if not self.data.completed else ""
        if second_line:
            text.append(f"\n      {second_line}", style="dim")

        return text


class PriorityRow(Static):
    """Renders a task row for the priority screen: rank number, title, optional due date."""

    DEFAULT_CSS = """
    PriorityRow {
        height: auto;
        padding: 0 1;
    }
    PriorityRow.selected {
        background: $secondary 20%;
    }
    """

    def __init__(self, data: Task, page_index: int, selected: bool) -> None:
        super().__init__()
        self.data = data
        self.page_index = page_index
        self._selected = selected
        if selected:
            self.add_class("selected")

    def render(self) -> Text:
        text = Text(no_wrap=True, overflow="ellipsis")
        rank = self.data.priority_order + 1
        indicator = "▸ " if self._selected else "  "
        text.append(f" #{rank:<3}", style="bold magenta")
        text.append(indicator, style="bold green" if self._selected else "dim")
        text.append(self.data.title, style="bold")
        if self.data.due_date:
            label, _ = _format_due(self.data.due_date)
            text.append(f"  ({label})", style="dim")
        if self.data.duration:
            text.append(f"  ~{_format_duration(self.data.duration)}", style="dim")
        return text


class EditTaskModal(ModalScreen):
    """Modal overlay for creating or editing a task."""

    DEFAULT_CSS = """
    EditTaskModal {
        align: center middle;
    }

    #dialog {
        padding: 1 2;
        background: $surface;
        border: thick $primary;
        width: 64;
        height: auto;
    }

    #modal-title {
        text-align: center;
        color: $primary;
        margin-bottom: 1;
    }

    #field-label {
        margin-top: 1;
        color: $text-muted;
    }

    #desc-label {
        margin-top: 1;
        color: $text-muted;
    }

    #due-label {
        margin-top: 1;
        color: $text-muted;
    }

    #due-preview {
        color: $text-muted;
        height: 1;
        padding: 0 1;
    }

    #start-label {
        margin-top: 1;
        color: $text-muted;
    }

    #buttons {
        margin-top: 1;
        height: auto;
        align: right middle;
    }

    Button {
        margin-left: 1;
    }
    """

    def __init__(
        self,
        title: str = "",
        description: str = "",
        due_date: str = "",
        start_date: str = "",
        heading: str = "New Task",
    ) -> None:
        super().__init__()
        self._initial_title = title
        self._initial_desc = description
        self._initial_due = due_date
        self._initial_start = start_date
        self._heading = heading

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self._heading, id="modal-title")
            yield Label("Title *", id="field-label")
            yield Input(
                value=self._initial_title,
                id="title-input",
                placeholder="Task title…",
            )
            yield Label("Description", id="desc-label")
            yield Input(
                value=self._initial_desc,
                id="desc-input",
                placeholder="Optional description…",
            )
            yield Label("Due date", id="due-label")
            yield Input(
                value=self._initial_due,
                id="due-input",
                placeholder="e.g. today by 8pm, tomorrow, next wednesday, 2026-04-01",
            )
            yield Label("", id="due-preview")
            yield Label("Start date (not before)", id="start-label")
            yield Input(
                value=self._initial_start,
                id="start-input",
                placeholder="e.g. tomorrow, 2026-04-02, 2pm today",
            )
            with Horizontal(id="buttons"):
                yield Button("Save  [enter]", variant="primary", id="btn-save")
                yield Button("Cancel  [esc]", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#title-input", Input).focus()
        self._update_due_preview(self._initial_due)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "due-input":
            self._update_due_preview(event.value)

    def _update_due_preview(self, raw: str) -> None:
        preview = self.query_one("#due-preview", Label)
        raw = raw.strip()
        if not raw:
            preview.update("")
            return
        parsed_iso = parse_due_date(raw)
        if parsed_iso:
            label, _ = _format_due(parsed_iso)
            if "T" in parsed_iso:
                dt = datetime.fromisoformat(parsed_iso)
                friendly = dt.strftime("%A, %B %-d %Y at %-I:%M%p").lower().capitalize()
            else:
                d = date.fromisoformat(parsed_iso)
                friendly = d.strftime("%A, %B %-d %Y")
            preview.update(f"  → {friendly}  ({label})")
        else:
            preview.update("  [bold red]couldn't parse date[/bold red]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save()
        else:
            self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
        elif event.key == "enter":
            event.stop()
            self._save()

    def _save(self) -> None:
        raw_title = self.query_one("#title-input", Input).value.strip()
        if not raw_title:
            self.query_one("#title-input", Input).focus()
            return
        title_no_tags, tags = parse_tags(raw_title)
        title, duration = parse_duration(title_no_tags)
        if not title:
            self.query_one("#title-input", Input).focus()
            return
        desc = self.query_one("#desc-input", Input).value.strip()
        due_raw = self.query_one("#due-input", Input).value.strip()
        due = ""
        if due_raw:
            due_iso = parse_due_date(due_raw)
            if due_iso:
                due = due_iso
            else:
                self.query_one("#due-input", Input).focus()
                return
        start_raw = self.query_one("#start-input", Input).value.strip()
        start_date = ""
        if start_raw:
            start_iso = parse_due_date(start_raw)
            if start_iso:
                start_date = start_iso
            else:
                self.query_one("#start-input", Input).focus()
                return
        self.dismiss((title, desc, due, duration, tags, start_date))


class TagFilterModal(ModalScreen):
    """Modal for entering a tag name to filter the task list."""

    DEFAULT_CSS = """
    TagFilterModal {
        align: center middle;
    }
    #filter-dialog {
        padding: 1 2;
        background: $surface;
        border: thick $primary;
        width: 48;
        height: auto;
    }
    #filter-title {
        text-align: center;
        color: $primary;
        margin-bottom: 1;
    }
    #filter-buttons {
        margin-top: 1;
        height: auto;
        align: right middle;
    }
    Button { margin-left: 1; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="filter-dialog"):
            yield Label("Filter by Tag", id="filter-title")
            yield Input(placeholder="tag name (without #)", id="filter-input")
            with Horizontal(id="filter-buttons"):
                yield Button("Apply  [enter]", variant="primary", id="btn-apply")
                yield Button("Cancel  [esc]", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#filter-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-apply":
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
        tag = self.query_one("#filter-input", Input).value.strip().lstrip("#")
        self.dismiss(tag if tag else None)


class GroupTaskRow(Static):
    """Renders a single task within an expanded group slot."""

    DEFAULT_CSS = """
    GroupTaskRow {
        height: auto;
        padding: 0 1;
    }
    GroupTaskRow.selected {
        background: $primary 20%;
    }
    """

    def __init__(self, data: Task, selected: bool, past: bool = False) -> None:
        super().__init__()
        self.data = data
        self._selected = selected
        self._past = past
        if selected:
            self.add_class("selected")

    def render(self) -> Text:
        text = Text(no_wrap=True, overflow="ellipsis")
        indicator = "▸ " if self._selected else "  "
        # Indent to align with task titles in ScheduleRow
        text.append("                    ", style="dim")
        if self._past:
            text.append(indicator, style="dim")
            text.append(self.data.title, style="dim")
        elif self.data.completed:
            text.append(indicator, style="dim")
            text.append(self.data.title, style="dim strike")
        else:
            text.append(indicator, style="bold green" if self._selected else "dim")
            text.append(self.data.title, style="bold")
            if self.data.duration:
                text.append(f"  ~{_format_duration(self.data.duration)}", style="dim")
            if self.data.due_date:
                label, style = _format_due(self.data.due_date)
                text.append(f"  {label}", style=style)
        return text


class ScheduleRow(Static):
    """Renders a single slot in the daily schedule view."""

    DEFAULT_CSS = """
    ScheduleRow {
        height: auto;
        padding: 0 1;
    }
    ScheduleRow.selected {
        background: $primary 20%;
    }
    """

    def __init__(self, data: "ScheduleSlot", page_index: int, selected: bool, past: bool = False) -> None:  # noqa: F821
        super().__init__()
        self.data = data
        self.page_index = page_index
        self._selected = selected
        self._past = past
        if selected:
            self.add_class("selected")

    def render(self) -> Text:
        from .scheduler import ScheduleSlot  # local import to avoid circular

        text = Text(no_wrap=True, overflow="ellipsis")
        slot = self.data
        time_str = (
            f"  {slot.start.strftime('%I:%M%p').lstrip('0').lower()}"
            f" - {slot.end.strftime('%I:%M%p').lstrip('0').lower()}  "
        )
        indicator = "▸ " if self._selected else "  "

        if self._past:
            # Entire row is dimmed for past time slots
            text.append(time_str, style="dim")
            text.append(indicator, style="dim")
            if slot.slot_type == "task":
                if slot.group:
                    titles = ", ".join(t.title for t in slot.group)
                    text.append(f"{len(slot.group)} quick tasks: {titles}", style="dim")
                elif slot.task:
                    text.append(slot.task.title, style="dim")
            elif slot.slot_type == "blocked":
                text.append(f"[{slot.label}]", style="dim italic")
            elif slot.slot_type == "break":
                text.append("-- break --", style="dim")
            elif slot.slot_type == "gap":
                text.append("-- free --", style="dim")
        elif slot.slot_type == "blocked":
            text.append(time_str, style="dim")
            text.append(indicator, style="dim")
            text.append(f"[{slot.label}]", style="dim italic")

        elif slot.slot_type == "break":
            text.append(time_str, style="dim")
            text.append(indicator, style="dim")
            text.append("-- break --", style="dim")

        elif slot.slot_type == "gap":
            text.append(time_str, style="dim")
            text.append(indicator, style="dim")
            text.append("-- free --", style="dim")

        elif slot.slot_type == "task":
            # Check if all tasks in this slot are completed
            all_completed = (
                all(t.completed for t in slot.group) if slot.group
                else (slot.task and slot.task.completed)
            )
            if all_completed:
                text.append(time_str, style="dim")
                text.append(indicator, style="dim")
                if slot.group:
                    titles = ", ".join(t.title for t in slot.group)
                    text.append(f"{len(slot.group)} quick tasks: {titles}", style="dim strike")
                elif slot.task:
                    text.append(slot.task.title, style="dim strike")
            else:
                text.append(time_str, style="bold cyan" if self._selected else "dim cyan")
                text.append(indicator, style="bold green" if self._selected else "dim")

                if slot.group:
                    # Short-task bunch
                    titles = ", ".join(t.title for t in slot.group)
                    total_mins = sum(t.duration for t in slot.group if t.duration)
                    text.append(f"{len(slot.group)} quick tasks: ", style="bold")
                    text.append(titles, style="bold")
                    text.append(f"  ~{_format_duration(total_mins)}", style="dim")
                else:
                    task = slot.task
                    if task:
                        text.append(task.title, style="bold")
                        if slot.chunk_index is not None and slot.total_chunks is not None:
                            text.append(
                                f"  [{slot.chunk_index + 1}/{slot.total_chunks}]",
                                style="bold magenta",
                            )
                        if task.duration:
                            slot_mins = int((slot.end - slot.start).total_seconds() / 60)
                            text.append(f"  ~{_format_duration(slot_mins)}", style="dim")
                            if slot.total_chunks and slot.total_chunks > 1:
                                text.append(f" of {_format_duration(task.duration)}", style="dim")
                        if task.due_date:
                            label, style = _format_due(task.due_date)
                            text.append(f"  {label}", style=style)

        return text
