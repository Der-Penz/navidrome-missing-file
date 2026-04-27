import logging

from rapidfuzz import fuzz, process
from rich.text import Text
from src.db_query import Song
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Key
from textual.widgets import Input, Static


import asyncio
from typing import List

try:
    from rapidfuzz import process, fuzz

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class FileSelector(Static):
    """A single-widget virtualized selector that exposes a Future which completes with the selected item or None."""

    DEFAULT_CSS = """
    VirtualSelector {
        height: 1fr;
    }
    """

    def __init__(self, rows: List[Song], title: str = "Select a file") -> None:
        super().__init__()
        self.rows = rows
        self.filtered: List[Song] = rows[:]
        self.title = title
        self.cursor_index = 0
        self.window_lines = 15
        self.result_future: asyncio.Future[Song | None] = (
            asyncio.get_event_loop().create_future()
        )

        # widgets placeholders (set in compose)
        self.search_input: Input | None = None
        self.body: Static | None = None

    def compose(self) -> ComposeResult:
        with Vertical():
            self.search_input = Input(
                placeholder=f"{self.title} (type to search…)", id="search"
            )
            yield self.search_input
            self.body = Static()
            yield self.body

    def on_mount(self) -> None:
        # tune window size based on available panel height
        try:
            avail = max(6, self.app.size.height - 6)
            self.window_lines = min(avail, max(3, len(self.filtered)))
        except Exception:
            self.window_lines = min(15, max(3, len(self.filtered)))

        # focus the input
        if self.search_input:
            self.search_input.focus()
        self.refresh_body()

    def filter_rows(self, query: str) -> None:
        q = query.strip().lower()
        if not q:
            self.filtered = self.rows
            self.cursor_index = 0
            self.refresh_body()
            return

        if RAPIDFUZZ_AVAILABLE:
            choices = [r.search_text for r in self.rows]
            results = process.extract_iter(
                q, choices, scorer=fuzz.WRatio, score_cutoff=60
            )
            # results yields tuples: (match, score, index)
            # collect indices sorted by score desc
            ranked = sorted(results, key=lambda x: x[1], reverse=True)
            indices = [idx for _, _, idx in ranked]
            # keep unique and in order
            seen = set()
            new_filtered = []
            for idx in indices:
                if idx not in seen:
                    seen.add(idx)
                    new_filtered.append(self.rows[idx])
            self.filtered = new_filtered
        else:
            self.filtered = [r for r in self.rows if q in r.search_text]

        # clamp cursor
        self.cursor_index = (
            0 if not self.filtered else min(self.cursor_index, len(self.filtered) - 1)
        )
        self.refresh_body()

    def refresh_body(self) -> None:
        if not self.body:
            return

        total = len(self.filtered)
        if total == 0:
            self.body.update(Text("No items match the query.", style="yellow"))
            return

        self.cursor_index = max(0, min(self.cursor_index, total - 1))

        half = self.window_lines // 2
        start = max(0, self.cursor_index - half)
        end = start + self.window_lines
        if end > total:
            end = total
            start = max(0, end - self.window_lines)

        txt = Text()
        for i in range(start, end):
            r = self.filtered[i]
            idx_label = f"{i + 1:>4}"
            title = r.title or "<untitled>"
            album = r.album or "-"
            artist = r.artist or "-"
            line = f"{idx_label}  {title} — {album} — {artist}\n"
            if i == self.cursor_index:
                txt.append(line, style="reverse")
            else:
                txt.append(line)
        footer = f"  Showing {start + 1}-{end} of {total}  (Use ↑↓ PgUp PgDn Home End Enter Esc)"
        txt.append("\n" + footer, style="dim")
        self.body.update(txt)

    def on_input_changed(self, event: Input.Changed) -> None:  # type: ignore[override]
        self.filter_rows(event.value)

    def on_key(self, event: Key) -> None:
        key = event.key

        if key in ("up",):
            if self.cursor_index > 0:
                self.cursor_index -= 1
                self.refresh_body()
            return

        if key in ("down",):
            if self.cursor_index < len(self.filtered) - 1:
                self.cursor_index += 1
                self.refresh_body()
            return

        if key == "pageup":
            step = max(1, self.window_lines - 2)
            self.cursor_index = max(0, self.cursor_index - step)
            self.refresh_body()
            return

        if key == "pagedown":
            step = max(1, self.window_lines - 2)
            self.cursor_index = min(len(self.filtered) - 1, self.cursor_index + step)
            self.refresh_body()
            return

        if key == "home":
            self.cursor_index = 0
            self.refresh_body()
            return

        if key == "end":
            self.cursor_index = max(0, len(self.filtered) - 1)
            self.refresh_body()
            return

        if key in ("enter",):
            if not self.filtered:
                if not self.result_future.done():
                    self.result_future.set_result(None)
                self.remove()
                return
            sel = self.filtered[self.cursor_index]
            if not self.result_future.done():
                self.result_future.set_result(sel)
            self.remove()
            return
