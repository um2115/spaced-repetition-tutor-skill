"""Write a snapshot taken by the migration script back into the Google Sheet.

    python -m migrations.runner.restore SNAPSHOT [--apply] [--sheet-id ID]
        [--client-secret FILE] [--token FILE]

Without `--apply` it only prints what it would write. With `--apply` it replaces the contents of
every tab in the snapshot, creates the tabs that are missing and leaves the other tabs alone, all
in one `batchUpdate`. The `config` tab is restored too, and with it `schema_version`.
"""

import argparse
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from . import snapshots
from .shared.errors import Abort
from .shared.settings import Settings, add_arguments, connect, resolve
from .shared.sheets import Request, Row, Sheet, SheetsClient, add_tab, append_rows, clear_tab


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    connect: Callable[[Settings], SheetsClient] = connect,
) -> int:
    parser = argparse.ArgumentParser(
        prog="restore", description="Write a snapshot back into the Google Sheet."
    )
    parser.add_argument("snapshot", type=Path, help="the snapshot directory")
    parser.add_argument("--apply", action="store_true", help="write; without it, only plan")
    add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        tabs = snapshots.load(args.snapshot)
        client = connect(resolve(args, environ))
        restore(client, tabs, apply=args.apply)
    except Abort as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def restore(client: SheetsClient, tabs: dict[str, list[Row]], *, apply: bool) -> None:
    sheet = client.read()
    print("Applying." if apply else "Dry run: nothing is written. Pass --apply to write.")
    for title, rows in tabs.items():
        print(f"{'replace' if title in sheet else 'create'} tab {title} with {len(rows)} row(s)")
    for title in sheet.tabs:
        if title not in tabs:
            print(f"leave tab {title} untouched")
    print("warning: state and log rows written after the snapshot was taken are lost.")
    if apply:
        client.batch_update(_requests(sheet, tabs))
        print("Done.")


def _requests(sheet: Sheet, tabs: dict[str, list[Row]]) -> list[Request]:
    requests, new_ids = [], sheet.free_sheet_ids()
    for title, rows in tabs.items():
        if title in sheet:
            sheet_id = sheet.sheet_id(title)
            requests.append(clear_tab(sheet_id))
        else:
            sheet_id = next(new_ids)
            requests.append(add_tab(sheet_id, title))
        if rows:
            requests.append(append_rows(sheet_id, rows))
    return requests


if __name__ == "__main__":
    sys.exit(main())
