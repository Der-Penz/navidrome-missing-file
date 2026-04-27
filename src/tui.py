import asyncio
import logging

from rich.console import Console

from src.file_selector import FileSelector
from src.merge import Merge
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

    def __init__(self, db: DBQuery, merge_strategy: Merge) -> None:
        super().__init__()
        self.db = db
        self.merge_strategy = merge_strategy

    def on_ready(self) -> None:
        """Trigger the selection flow without blocking the main loop."""
        self.run_worker(self.run_selection_flow())

    async def run_selection_flow(self) -> None:
        """This now runs in the background, keeping the UI alive."""
        try:
            while True:
                missing = await self.select_file(
                    missing=1, prompt_title="Select missing song"
                )

                if not missing:
                    logging.info("Missing file selection cancelled. Exiting.")
                    break

                target = await self.select_file(
                    missing=0, prompt_title="Select replacement song"
                )

                if target is None:
                    logging.info("Target file selection cancelled. Exiting.")
                    break

                await self.handle_merge(missing, target)
        except asyncio.CancelledError:
            logging.info("Selection flow worker was cancelled.")
        finally:
            self.exit()

    async def select_file(self, missing: int, prompt_title: str) -> Song | None:
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
        selector = FileSelector(rows, title=prompt_title)
        await self.mount(selector)

        # wait for the user's choice
        try:
            selected_song = await selector.result_future
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
        # Fetch annotations

        anno_missing = self.db.get_annotation(missing)

        if anno_missing is None:
            self.notify(
                f"No annotation found for missing song '{missing.title}', using defaults.",
                severity="warning",
            )
            exit(0)

        anno_target = self.db.get_annotation(target, anno_missing.user_id)

        if anno_target is None:
            self.notify(
                f"No annotation found for target song '{target.title}', using defaults.",
                severity="warning",
            )
            exit(0)

        logging.debug(f"Merging missing {missing} with target {target}")

        combined = self.merge_strategy.merge(anno_missing, anno_target)

        self.db.replace_song(missing, target, combined)

        self.notify("Merge successful!", severity="information")
