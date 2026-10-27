"""Bring the Google Sheet to the latest schema version and sync the YAML questions into it.

    python -m migrations.runner.migrate [--apply] [--sheet-id ID] [--client-secret FILE]
        [--token FILE]

Without `--apply` it only prints the plan. With `--apply` it creates the missing tabs, runs the
pending steps of `migrations/steps/` in version order, each as one atomic `batchUpdate`, and
syncs the questions of `migrations/questions/` in one more `batchUpdate`.

A pending structural step may change header rows, so the headers are then checked only after the
steps have run, and a dry run cannot show the question sync.
"""

import argparse
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from migrations.schema.applied_steps import APPLIED_STEPS, AppliedStep
from migrations.schema.configs import CONFIG
from migrations.schema.questions_file import load_directory_with_files
from migrations.schema.shared.tabs import RowError, check_header
from migrations.schema.workbook import TABS, header

from . import snapshots
from .question_sync import SourcedQuestion, plan_sync, unmanaged_rows
from .shared.errors import Abort
from .shared.settings import Settings, add_arguments, connect, resolve
from .shared.sheets import (
    Request,
    Row,
    Sheet,
    SheetsClient,
    TabValues,
    add_tab,
    append_rows,
    write_row,
)
from .steps import STEPS, Step, discover, latest_version

REPO = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    repo: Path = REPO
    questions: Path = REPO / "migrations" / "questions"
    steps: Path = STEPS
    snapshots: Path = snapshots.SNAPSHOTS


PATHS = Paths()


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    connect: Callable[[Settings], SheetsClient] = connect,
    stdin: TextIO = sys.stdin,
    paths: Paths = PATHS,
) -> int:
    parser = argparse.ArgumentParser(
        prog="migrate", description="Migrate the Google Sheet and sync the YAML questions."
    )
    parser.add_argument("--apply", action="store_true", help="write; without it, only plan")
    add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        questions = load_questions(paths)
        steps = discover(paths.steps)
        client = connect(resolve(args, environ))
        migrate(client, questions, steps, apply=args.apply, stdin=stdin, paths=paths)
    except (Abort, RowError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def load_questions(paths: Paths) -> list[SourcedQuestion]:
    """Load and validate the YAML questions; print every error and abort if there are any."""
    sourced, errors = load_directory_with_files(paths.questions)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        raise Abort(f"{len(errors)} error(s) in question files")
    return [SourcedQuestion(question, _relative(path, paths.repo)) for question, path in sourced]


def migrate(
    client: SheetsClient,
    questions: list[SourcedQuestion],
    steps: list[Step],
    *,
    apply: bool,
    stdin: TextIO,
    paths: Paths,
) -> None:
    sheet = client.read()
    latest = latest_version(steps)
    missing = [tab.name for tab in TABS if tab.name not in sheet]
    version = _schema_version(sheet, latest)
    pending = [step for step in steps if step.version > version]
    structural = [step for step in pending if step.structural]
    if not structural:
        _check_headers(sheet)

    print("Applying." if apply else "Dry run: nothing is written. Pass --apply to write.")
    for name in missing:
        print(f"create tab {name}")
    print(f"schema version {version}, latest {latest}")
    for step in pending:
        print(f"run step {step.label} ({'structural' if step.structural else 'data-only'})")
    if structural:
        _warn_unmanaged(sheet, structural, apply, stdin)

    if not apply:
        print(f"take a snapshot before step {structural[0].label}" if structural else "no snapshot")
        if structural:
            print("question sync: planned once the structural steps have run")
            return
        _print_sync(plan_sync(_with_tabs(sheet, missing, latest), questions).report())
        return

    if structural:
        print(f"snapshot saved to {snapshots.save(sheet, paths.snapshots)}")
    if missing:
        client.batch_update(_create_tabs(sheet, missing, latest))
        sheet = client.read()
    for step in pending:
        _run_step(client, sheet, step)
        print(f"applied step {step.label}")
        sheet = client.read()
    _check_headers(sheet)
    plan = plan_sync(sheet, questions)
    _print_sync(plan.report())
    if plan.changes:
        client.batch_update(plan.requests(sheet))
    print("Done.")


def _relative(path: Path, repo: Path) -> str:
    return path.relative_to(repo).as_posix() if path.is_relative_to(repo) else str(path)


def _schema_version(sheet: Sheet, latest: int) -> int:
    """The sheet's schema version; a sheet without `config` gets one at the latest version."""
    if CONFIG.name not in sheet:
        return latest
    version = CONFIG.from_rows(sheet.rows(CONFIG.name)).schema_version
    if version > latest:
        raise Abort(
            f"the sheet has schema version {version}, but the latest step in this repository has "
            f"version {latest}. Update the repository. Nothing was written."
        )
    return version


def _check_headers(sheet: Sheet) -> None:
    for tab in TABS:
        if tab.name in sheet:
            check_header(tab.name, sheet.rows(tab.name), header(tab.name))


def _warn_unmanaged(sheet: Sheet, structural: list[Step], apply: bool, stdin: TextIO) -> None:
    """Warn about hand-added questions before a structural step; with `apply`, ask y/N."""
    unmanaged = unmanaged_rows(sheet)
    if not unmanaged:
        return
    names = ", ".join(question or f"row {row}" for row, question in unmanaged)
    labels = ", ".join(step.label for step in structural)
    print(
        f"warning: these questions are not managed by the migration script: {names}. They may "
        f"break, because their format may not fit the structural step(s) {labels}."
    )
    if not apply:
        print("--apply asks before it writes anything.")
        return
    if not stdin.isatty():
        raise Abort(
            "standard input is not interactive, so nobody can confirm. Nothing was written."
        )
    print("Continue? [y/N] ", end="", flush=True)
    if stdin.readline().strip().lower() not in ("y", "yes"):
        raise Abort("aborted. Nothing was written.")


def _initial_rows(name: str, latest: int) -> list[Row]:
    rows = [header(name)]
    if name == CONFIG.name:
        rows.append(["schema_version", str(latest)])
    return rows


def _with_tabs(sheet: Sheet, missing: list[str], latest: int) -> Sheet:
    """`sheet` as it would be once the missing tabs are created."""
    planned = Sheet(dict(sheet.tabs))
    ids = sheet.free_sheet_ids()
    for name in missing:
        planned.tabs[name] = TabValues(next(ids), _initial_rows(name, latest))
    return planned


def _create_tabs(sheet: Sheet, missing: list[str], latest: int) -> list[Request]:
    planned = _with_tabs(sheet, missing, latest)
    requests = []
    for name in missing:
        tab = planned.tabs[name]
        requests += [add_tab(tab.sheet_id, name), append_rows(tab.sheet_id, tab.rows)]
    return requests


def _run_step(client: SheetsClient, sheet: Sheet, step: Step) -> None:
    """Apply `step`, set `schema_version` and log the step, all in one `batchUpdate`."""
    try:
        requests = [
            *step.requests(sheet),
            _set_schema_version(sheet, step.version),
            append_rows(
                sheet.sheet_id(APPLIED_STEPS.name),
                [APPLIED_STEPS.to_row(_applied(step))],
            ),
        ]
        client.batch_update(requests)
    except Exception as error:
        raise Abort(
            f"step {step.label} failed: {error}. The steps before it stay applied; the next run "
            "resumes from it."
        ) from error


def _applied(step: Step) -> AppliedStep:
    return AppliedStep(version=step.version, name=step.name, applied_at=datetime.now(UTC))


def _set_schema_version(sheet: Sheet, version: int) -> Request:
    config = sheet.sheet_id(CONFIG.name)
    for number, row in enumerate(sheet.rows(CONFIG.name)[1:], start=2):
        if row and row[0].strip() == "schema_version":
            return write_row(config, number, [str(version)], column=1)
    return append_rows(config, [["schema_version", str(version)]])


def _print_sync(lines: list[str]) -> None:
    print("question sync:")
    for line in lines:
        print(f"  {line}")


if __name__ == "__main__":
    sys.exit(main())
