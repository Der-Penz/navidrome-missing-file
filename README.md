# Navidrome Missing File Merger

Sometimes navidrome does not pick up a changed music file due to whatever reason and you end up with a `missing file` with and the annotations and playlist references are lost with the old file and to not show up for the same new media. This tool allows you to merge the annotations and playlist references of a missing file into an existing track in the library, effectively "rescuing" that data and associating it with a real file again.

## What it does

When a Navidrome library contains a track that is no longer available on disk, the database can still keep its annotations and playlist references. This tool helps you move that data onto a real track:

1. Pick a missing file entry.
2. Pick a replacement track from the existing library, or let the tool try to auto-match one.
3. Review the merge result.
4. Confirm the merge (Only for the first user, subsequent users will have their annotations merged automatically if the first one is confirmed).
5. Write the updated annotation for each user and playlist data back into the database.
6. Delete the missing media-file record.

## Features

- Interactive TUI for choosing missing and replacement tracks.
- Fuzzy search for filtering track lists.
- Auto-selection modes for unattended runs.
- Two merge strategies for annotation data.
- Optional CSV-style merge report.
- Backup prompt before database modification.

## Requirements

- Python 3.13 or newer
- A Navidrome SQLite database file

## Installation

If you use `uv`, install dependencies with:

```bash
uv sync
```

If you prefer another workflow, install the dependencies from `pyproject.toml` in your environment of choice.

## Usage

Run the tool against a Navidrome database file:

```bash
uv run cli .\navidrome.db
```

The script modifies the database in place, so it is strongly recommended to shut down the Navidrome server before running this tool to avoid conflicts. Make sure to have a backup of your database before proceeding, although the tool will also prompt you to create one. 

I cannot guarantee that everything will work perfectly, so please make sure you can roll back to the backup if something goes wrong.

## Command-Line Options

- `navidrome_db`: Path to the Navidrome SQLite database file.
- `-s`, `--merge-strategy`: Annotation merge strategy. Available values are `add` and `overwrite`.

- `-m`, `--auto-missing`: Automatically pick the next missing file instead of prompting.
- `-t`, `--auto-target`: Automatically pick a replacement track instead of prompting.
- `-c`, `--auto-confirm`: Skip the merge confirmation screen.
- `-r`, `--report`: Write a merge report to `merge_report.txt` in the current directory.
- `-b`, `--backup`: Create a backup without asking.
- `-B`, `--no-backup`: Skip backup creation entirely.

## Merge Strategies

The tool currently supports two strategies for combining annotation data:

- `add` will combine play counts, keep the highest rating, and merge starred state 
- `overwrite` will copy the missing track's annotation over the target annotation. the target annotation will be completely lost. if you have not listened to the new songs this is probably what you want, otherwise `add` is the safer choice.

## Interactive Workflow

without any flags, the tool will guide you through an interactive process. By setting the `--auto-missing` and `--auto-target` and `--auto-confirm` flags, you can make the tool run without any user input, which is useful if you have a large number of missing files and trust the auto-matching to find the correct replacements. But matching might not be perfect.

## Safety Notes

The tool updates the SQLite database directly. While I have tested it on my own library, there may be edge cases that could lead to data loss or corruption. Always make sure to have a backup of your database before running the tool, and consider testing it on a copy of your database first to ensure it behaves as expected with your specific data. No liability is assumed for any damage caused by using this tool.