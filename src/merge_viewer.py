import asyncio
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Grid
from textual.containers import Container
from textual.widget import Widget

from src.db_query import Annotation, Song


class MergeViewer(Widget, can_focus=True):
    DEFAULT_CSS = """
    MergeViewer {
        width: 95%;
        height: 95%;
        border: round gray;
        padding: 1;
    }

    #grid {
        layout: grid;
        grid-size: 2 3;
        grid-gutter: 1;
        height: 1fr;
    }

    #missing_song,
    #target_song,
    #missing_anno,
    #target_anno {
        border: round gray;
        padding: 0;
    }

    #merged {
        column-span: 2;
        border: heavy green;
        padding: 0;
        background: $surface;
    }

    #footer {
    dock: bottom;
    height: 3;
    align: center middle;
    background: $surface;
    color: yellow;
    padding: 0 1;
}
    """

    def __init__(
        self,
        missing: Song,
        target: Song,
        missing_anno: Annotation,
        target_anno: Annotation,
        anno_merged: Annotation,
    ):
        super().__init__()
        self.missing = missing
        self.target = target
        self.missing_anno = missing_anno
        self.target_anno = target_anno
        self.merged = anno_merged

        self.result_future: asyncio.Future[bool] = (
            asyncio.get_event_loop().create_future()
        )

    def compose(self) -> ComposeResult:
        with Grid(id="grid"):
            yield Static(self._section("Missing Song", self.missing), id="missing_song")
            yield Static(self._section("Target Song", self.target), id="target_song")

            yield Static(
                self._section_anno("Missing Annotation", self.missing_anno),
                id="missing_anno",
            )
            yield Static(
                self._section_anno("Target Annotation", self.target_anno),
                id="target_anno",
            )

            yield Static(self._section_anno("Merged Result", self.merged), id="merged")

        with Container(id="footer"):
            yield Static(
                "✔ Enter: accept   ✖ q: cancel   x: exit app",
                id="footer",
            )

    def _section(self, title: str, song: Song) -> str:
        return (
            f"{title}\n"
            f"Title : {song.title}\n"
            f"Artist: {song.artist}\n"
            f"Album : {song.album}\n"
        )

    def _section_anno(self, title: str, anno: Annotation) -> str:
        return (
            f"{title}\n"
            f"Play Count: {anno.play_count}\n"
            f"Rating: {anno.rating}\n"
            f"Starred: {anno.starred}\n"
            f"Rated At: {anno.rated_at}\n"
            f"Starred At: {anno.starred_at}\n"
        )

    def on_mount(self) -> None:
        self.focus()

    def on_key(self, event) -> None:
        if event.key == "enter":
            if not self.result_future.done():
                self.result_future.set_result(True)
            self.remove()

        elif event.key == "q":
            if not self.result_future.done():
                self.result_future.set_result(False)
            self.remove()

        elif event.key == "x":
            if not self.result_future.done():
                self.result_future.set_result(None)
