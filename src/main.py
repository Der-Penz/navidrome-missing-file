import argparse
import logging
from pathlib import Path
import shutil
import sys
from src.db_query import DBQuery


from rich.prompt import Confirm
from rich.console import Console
from src.logger import setup_logger
from src.merge import MERGE_STRATEGIES
from src.tui import NavidromeSelectorApp

console = Console()


def create_backup(db_path: Path) -> Path | None:
    """
    Creates a backup of the SQLite database file.

    Parameters
    ----------
    db_path : Path
        The path to the original database file.

    Returns
    -------
    Path | None
        The path to the created backup or None if failed.
    """
    backup_path = db_path.with_suffix(db_path.suffix + ".bak")
    try:
        shutil.copy2(db_path, backup_path)
        logging.info(f"Backup created at: {backup_path}")
        console.print(f"[green]Backup created:[/green] {backup_path}")
        return backup_path
    except Exception as e:
        logging.error(f"Failed to create backup: {e}")
        return None


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
        "-s",
        help="Strategy to merge annotations (default: add)",
        choices=list(MERGE_STRATEGIES.keys()),
        default=list(MERGE_STRATEGIES.keys())[0],
    )

    parser.add_argument(
        "--auto-missing",
        "-m",
        help="Automatically select the first missing file for merging without prompting",
        action="store_true",
    )

    parser.add_argument(
        "--auto-target",
        "-t",
        help="Automatically select the target song for merging without prompting (tries to find a suitable match based on metadata)",
        action="store_true",
    )

    parser.add_argument(
        "--auto-confirm",
        "-c",
        help="Automatically confirm the merge without prompting",
        action="store_true",
    )

    parser.add_argument(
        "--report",
        "-r",
        help="Generate a report of all matched files",
        action="store_true",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        help="Enable verbose logging for debugging purposes",
        action="store_true",
    )

    backup_group = parser.add_mutually_exclusive_group()
    backup_group.add_argument(
        "-b",
        "--backup",
        action="store_true",
        help="Force creation of a backup without asking",
    )
    backup_group.add_argument(
        "-B",
        "--no-backup",
        action="store_true",
        help="Skip backup creation entirely",
    )

    args = parser.parse_args()
    db_file: Path = args.navidrome_db
    merge_strategy = MERGE_STRATEGIES[args.merge_strategy]
    no_backup = args.no_backup
    force_backup = args.backup

    if args.verbose:
        setup_logger()

    if not db_file.exists() or not db_file.is_file():
        console.print(f"[red]Error:[/red] '{db_file}' does not exist.")
        sys.exit(1)

    if force_backup or (
        not no_backup
        and Confirm.ask(
            "This script will modify the database. Create a backup?",
            default=True,
        )
    ):
        create_backup(db_file)

    with DBQuery(db_file) as db:
        app = NavidromeSelectorApp(
            db,
            merge_strategy,
            args.auto_missing,
            args.auto_target,
            args.auto_confirm,
            args.report,
        )
        app.run()


if __name__ == "__main__":
    main()
