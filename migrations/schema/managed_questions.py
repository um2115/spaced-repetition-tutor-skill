"""The questions the migration script owns and the `managed_questions` tab.

A `questions` row whose id is listed here comes from a YAML question file and is overwritten by
the next migration run. Any other `questions` row was added by hand and is left alone.
"""

from .shared import cells
from .shared.models import Model, NonEmptyStr, QuestionId
from .shared.tabs import Column, RowError, Tab


class ManagedQuestion(Model):
    """A row of the `managed_questions` tab."""

    question_id: QuestionId
    source_file: NonEmptyStr
    """The YAML file path, relative to the repository root."""


MANAGED_QUESTIONS = Tab(
    "managed_questions",
    ManagedQuestion,
    (
        Column("question_id", cells.format_str, cells.parse_str),
        Column("source_file", cells.format_str, cells.parse_str),
    ),
)


def managed_rows(rows: list[list[str]]) -> dict[str, tuple[int, ManagedQuestion]]:
    """Parse the tab's rows into `{question_id: (sheet row number, row)}`; ids must be unique."""
    result: dict[str, tuple[int, ManagedQuestion]] = {}
    for number, managed in enumerate(MANAGED_QUESTIONS.from_rows(rows), start=2):
        if managed.question_id in result:
            message = f"duplicate question_id {managed.question_id!r}"
            raise RowError(MANAGED_QUESTIONS.name, number, "question_id", message)
        result[managed.question_id] = (number, managed)
    return result
