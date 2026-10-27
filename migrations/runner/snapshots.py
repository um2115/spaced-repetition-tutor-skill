"""Local snapshots of the whole sheet, taken before structural migration steps.

A snapshot is a directory `snapshots/<UTC timestamp>/` with one CSV file per tab. The cells are
kept as read, unvalidated, so malformed hand-added rows survive. A file name is the tab title,
percent-encoded where a character is not safe in a file name.
"""

import csv
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, unquote

from .shared.errors import Abort
from .shared.sheets import Row, Sheet

SNAPSHOTS = Path(__file__).resolve().parents[2] / "snapshots"


def save(sheet: Sheet, root: Path = SNAPSHOTS, now: datetime | None = None) -> Path:
    """Write `sheet` into a new directory under `root` and return its path."""
    now = now or datetime.now(UTC)
    directory = root / now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    try:
        directory.mkdir(parents=True)
        for title, tab in sheet.tabs.items():
            with open(directory / f"{quote(title, safe=' ')}.csv", "w", newline="") as file:
                csv.writer(file).writerows(tab.rows)
    except OSError as error:
        raise Abort(f"cannot write the snapshot {directory}: {error}") from error
    return directory


def load(directory: Path) -> dict[str, list[Row]]:
    """Read a snapshot: `{tab title: rows}`."""
    if not directory.is_dir():
        raise Abort(f"snapshot directory not found: {directory}")
    files = sorted(directory.glob("*.csv"))
    if not files:
        raise Abort(f"snapshot directory holds no CSV files: {directory}")
    tabs = {}
    for path in files:
        with open(path, newline="") as file:
            tabs[unquote(path.stem)] = [list(row) for row in csv.reader(file)]
    return tabs
