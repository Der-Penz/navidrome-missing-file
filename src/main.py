import argparse
from pathlib import Path
import shutil
import sys
from src.db_query import DBQuery


from rich.prompt import Confirm
from rich.console import Console
from src.logger import setup_logger
from src.merge import MERGE_STRATEGIES
from src.tui import NavidromeSelectorApp

setup_logger()

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Merge data from missing files into another song"
    )

    parser.add_argument(
        "navidrome_db",
        help="Path to the Navidrome SQLite database file",
        type=Path,
    )

    parser.add_argument(
        "--merge-strategy",
        help="Strategy to merge annotations (default: add)",
        choices=list(MERGE_STRATEGIES.keys()),
        default=list(MERGE_STRATEGIES.keys())[0],
    )

    args = parser.parse_args()
    db_file: Path = args.navidrome_db
    merge_strategy = MERGE_STRATEGIES[args.merge_strategy]

    if not db_file.exists() or not db_file.is_file():
        console.print(f"[red]Error:[/red] '{db_file}' does not exist.")
        sys.exit(1)

    if Confirm.ask(
        "This script will modify the database. Create a backup?",
        default=True,
    ):
        destination = db_file.with_suffix(db_file.suffix + ".bak")
        shutil.copy2(db_file, destination)
        console.print(f"[green]Backup created:[/green] {destination}")

    with DBQuery(db_file) as db:
        app = NavidromeSelectorApp(db, merge_strategy)
        app.run()


if __name__ == "__main__":
    main()
