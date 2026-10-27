"""Sync the YAML questions into the `questions` tab.

The `managed_questions` tab lists the questions the migration script owns. A managed row is
overwritten whenever it differs from its YAML question. Any other row of `questions` was added by
hand: it is left alone and not validated, unless a YAML question with its id takes it over.
Nothing is ever deleted; a managed question removed from YAML is only reported.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from migrations.schema.managed_questions import MANAGED_QUESTIONS, ManagedQuestion, managed_rows
from migrations.schema.questions import QUESTIONS, Question
from migrations.schema.shared.tabs import check_header

from .shared.sheets import Request, Row, Sheet, append_rows, clear_row, write_row


@dataclass(frozen=True)
class SourcedQuestion:
    question: Question
    source_file: str
    """The YAML file path, relative to the repository root."""


@dataclass(frozen=True)
class Change:
    """A YAML question to write into `questions` and to list in `managed_questions`."""

    question: Question
    source_file: str
    row: int | None
    """The `questions` row to overwrite; None to append the question."""
    managed_row: int | None
    """The question's `managed_questions` row; None when it is not managed yet."""
    fields: tuple[str, ...] = ()
    """The question fields that differ from the sheet row."""
    source_changed: bool = False

    @property
    def takeover(self) -> bool:
        return self.row is not None and self.managed_row is None


@dataclass
class SyncPlan:
    changes: list[Change] = field(default_factory=list)
    removed_from_yaml: list[str] = field(default_factory=list)
    """Managed question ids that are no longer in any YAML file."""
    unmanaged: list[tuple[int, str]] = field(default_factory=list)
    """(row, id) of the hand-added rows that are left alone."""

    def requests(self, sheet: Sheet) -> list[Request]:
        """The `batchUpdate` requests that apply the plan to `sheet`."""
        questions = sheet.sheet_id(QUESTIONS.name)
        managed = sheet.sheet_id(MANAGED_QUESTIONS.name)
        requests, new_questions, new_managed = [], [], []
        for change in self.changes:
            row = QUESTIONS.to_row(change.question)
            if change.row is None:
                new_questions.append(row)
            elif change.fields or change.takeover:
                requests += [
                    clear_row(questions, change.row),
                    write_row(questions, change.row, row),
                ]
            managed_row = MANAGED_QUESTIONS.to_row(
                ManagedQuestion(question_id=change.question.id, source_file=change.source_file)
            )
            if change.managed_row is None:
                new_managed.append(managed_row)
            elif change.source_changed:
                requests.append(write_row(managed, change.managed_row, managed_row))
        if new_questions:
            requests.append(append_rows(questions, new_questions))
        if new_managed:
            requests.append(append_rows(managed, new_managed))
        return requests

    def report(self) -> list[str]:
        lines = []
        for change in self.changes:
            question = change.question.id
            if change.row is None:
                lines.append(f"append question {question} from {change.source_file}")
            elif change.takeover:
                lines.append(
                    f"take over unmanaged question {question} (row {change.row}) "
                    f"from {change.source_file}"
                )
            else:
                fields = [*change.fields, *(["source_file"] if change.source_changed else [])]
                lines.append(
                    f"overwrite question {question} (row {change.row}): {', '.join(fields)}"
                )
        if not self.changes:
            lines.append("questions are up to date")
        for question in self.removed_from_yaml:
            lines.append(f"managed question {question} is no longer in YAML; left untouched")
        for row, question in self.unmanaged:
            name = f"question {question}" if question else "row without id"
            lines.append(f"unmanaged {name} (row {row}) left untouched")
        return lines


def unmanaged_rows(sheet: Sheet) -> list[tuple[int, str]]:
    """(row, id) of every non-empty `questions` row whose id is not in `managed_questions`.

    It reads the first column of both tabs without validating them, because a pending
    structural step may have changed their format.
    """
    managed = {row[0].strip() for row in sheet.rows(MANAGED_QUESTIONS.name)[1:] if row}
    return [
        (number, (row[0] if row else "").strip())
        for number, row in enumerate(sheet.rows(QUESTIONS.name)[1:], start=2)
        if any(cell.strip() for cell in row) and (row[0] if row else "").strip() not in managed
    ]


def plan_sync(sheet: Sheet, questions: Sequence[SourcedQuestion]) -> SyncPlan:
    """Compare the YAML questions with the sheet. A malformed managed row raises a RowError."""
    managed = _managed(sheet)
    rows = _question_rows(sheet)
    in_sheet: dict[str, tuple[int, Question | None]] = {}
    for number, question_id, row in rows:
        if question_id in in_sheet:
            continue
        parsed = QUESTIONS.from_row(row, number) if question_id in managed else None
        in_sheet[question_id] = (number, parsed)

    plan, yaml_ids = SyncPlan(), set()
    for sourced in questions:
        question = sourced.question
        yaml_ids.add(question.id)
        managed_row, entry = managed.get(question.id, (None, None))
        source_changed = entry is not None and entry.source_file != sourced.source_file
        row, current = in_sheet.get(question.id, (None, None))
        fields = ()
        if current is not None:
            fields = tuple(
                name for name in QUESTIONS.header
                if getattr(current, name) != getattr(question, name)
            )  # fmt: skip
        change = Change(question, sourced.source_file, row, managed_row, fields, source_changed)
        if row is None or change.takeover or fields or source_changed:
            plan.changes.append(change)

    plan.removed_from_yaml = [qid for qid in managed if qid not in yaml_ids]
    taken_over = {change.row for change in plan.changes if change.takeover}
    plan.unmanaged = [
        (number, qid) for number, qid, _ in rows
        if qid not in managed and number not in taken_over
    ]  # fmt: skip
    return plan


def _managed(sheet: Sheet) -> dict[str, tuple[int, ManagedQuestion]]:
    return managed_rows(sheet.rows(MANAGED_QUESTIONS.name))


def _question_rows(sheet: Sheet) -> list[tuple[int, str, Row]]:
    """(row, stripped id, cells) of every non-empty `questions` row."""
    rows = sheet.rows(QUESTIONS.name)
    check_header(QUESTIONS.name, rows, QUESTIONS.header)
    return [
        (number, (row[0] if row else "").strip(), row)
        for number, row in enumerate(rows[1:], start=2)
        if any(cell.strip() for cell in row)
    ]
