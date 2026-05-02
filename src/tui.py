import asyncio
import logging

from rich.console import Console

from src.file_selector import FileSelector
from src.merge import Merge
from src.merge_viewer import MergeViewer
from src.target_matching import select_target_for_missing
from textual.app import App

from src.db_query import DBQuery, Song

console = Console()


class NavidromeSelectorApp(App):
    """Main App that exposes selection helper methods which query the DB via DBQuery."""

    CSS = """
    Screen {
        align: center middle;
    }

    #container {
        width: 95%;
        height: 95%;
    }

    Input {
        margin-bottom: 1;
    }

    Static {
        border: round gray;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        db: DBQuery,
        merge_strategy: Merge,
        auto_missing: bool,
        auto_target: bool,
        auto_confirm: bool,
        report: bool,
    ) -> None:
        super().__init__()
        self.db = db
        self.merge_strategy = merge_strategy
        self.auto_missing = auto_missing
        self.auto_target = auto_target
        self.auto_confirm = auto_confirm
        self.skipped_missing_ids: set[int] = set()
        self.report = report
        self.exit_app = False

        if self.report:
            with open("merge_report.txt", "w") as f:
                f.write(
                    "Missing Title,Missing Artist,Missing Album,Missing ID,Target Title,Target Artist,Target Album,Target ID\n"
                )

    def on_ready(self) -> None:
        """Trigger the selection flow without blocking the main loop."""
        self.run_worker(self.run_selection_flow())

    async def run_selection_flow(self) -> None:
        """This now runs in the background, keeping the UI alive."""
        try:
            while True:
                if self.exit_app:
                    logging.info("Exit flag set, terminating selection flow.")
                    break

                if not self.auto_missing:
                    missing = await self.select_file(
                        missing=1, prompt_title="Select missing song"
                    )
                else:
                    rows = self.db.find_files(missing=1)
                    missing = None
                    for row in rows:
                        if row.id in self.skipped_missing_ids:
                            continue
                        missing = row
                        break

                    logging.info(f"Auto-selected missing song: {missing}")

                if not missing:
                    logging.info("Missing file selection cancelled. Exiting.")
                    break

                if not self.auto_target:
                    target = await self.select_file(
                        missing=0,
                        prompt_title="Select replacement song",
                        subtitle=f"Selected missing file: {missing.title} - {missing.artist}",
                    )
                else:
                    rows = self.db.find_files(missing=0)
                    target = select_target_for_missing(missing, rows) if rows else None
                    logging.info(f"Auto-selected target song: {target}")

                if target is None:
                    logging.info("Target file selection cancelled. Exiting.")
                    break

                await self.handle_merge(missing, target)
        except asyncio.CancelledError:
            logging.info("Selection flow worker was cancelled.")
        finally:
            self.exit()

    async def select_file(
        self, missing: int, prompt_title: str, subtitle: str = ""
    ) -> Song | None:
        """
        Query the DB for files with given missing flag and present the virtual selector.
        Returns a lightweight dict (id,title,album,artist,path) or None if cancelled / empty.
        This function is async and can be awaited from other parts of the app.
        """
        rows = self.db.find_files(missing)
        if not rows:
            console.print(
                f"[green]No {'missing' if missing else 'existing'} files found.[/green]"
            )
            return None

        # create selector widget
        selector = FileSelector(rows, title=prompt_title, subtitle=subtitle)
        await self.mount(selector)

        # wait for the user's choice
        try:
            selected_song = await selector.result_future
            logging.debug(f"Selected song: {selected_song}")
        except asyncio.CancelledError:
            selected_song = None

        # ensure widget cleaned up
        if selector in self.query("#selector"):
            await selector.remove()

        if selected_song is None:
            console.print("[yellow]Selection cancelled.[/yellow]")
            return None

        return selected_song

    async def handle_merge(self, missing: Song, target: Song) -> None:
        anno_missing = self.db.get_annotation(missing)

        if anno_missing is None:
            self.notify(
                f"No annotation found for missing song '{missing.title}', file will be deleted, since no data is connected to it.",
                severity="information",
            )
            self.db.delete_media_file(missing)
            return

        anno_target = self.db.get_annotation(target, anno_missing.user_id)

        if anno_target is None:
            combined = anno_missing
        else:
            combined = self.merge_strategy.merge(anno_missing, anno_target)

        if not self.auto_confirm:
            viewer = MergeViewer(missing, target, anno_missing, anno_target, combined)
            await self.mount(viewer)

            accepted = await viewer.result_future

            if accepted is None:
                self.exit_app = True
                return
            elif not accepted:
                self.notify("Merge cancelled.", severity="warning")
                self.skipped_missing_ids.add(missing.id)
                return

        self.db.replace_song(missing, target, combined)

        if self.report:
            with open("merge_report.txt", "a") as f:
                f.write(
                    f'"{missing.title}","{missing.artist}","{missing.album}",{missing.id},'
                    f'"{target.title}","{target.artist}","{target.album}",{target.id}\n'
                )

        self.notify("Merge successful!", severity="information")
