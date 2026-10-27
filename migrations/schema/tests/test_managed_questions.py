import pytest

from migrations.schema.managed_questions import MANAGED_QUESTIONS, ManagedQuestion, managed_rows
from migrations.schema.shared.tabs import RowError

MANAGED = ManagedQuestion(question_id="git-rebase", source_file="migrations/questions/git.yaml")


def test_header_matches_the_spec():
    assert MANAGED_QUESTIONS.header == ["question_id", "source_file"]


def test_row_round_trip():
    rows = MANAGED_QUESTIONS.to_rows([MANAGED])

    assert rows[1] == ["git-rebase", "migrations/questions/git.yaml"]
    assert managed_rows(rows) == {"git-rebase": (2, MANAGED)}


@pytest.mark.parametrize(
    ("row", "column", "message"),
    [
        (["Git Rebase", "a.yaml"], "question_id", "should match pattern"),
        (["git-rebase", ""], "source_file", "must not be empty"),
    ],
)
def test_malformed_row(row, column, message):
    with pytest.raises(RowError) as raised:
        managed_rows([MANAGED_QUESTIONS.header, row])

    assert (raised.value.row, raised.value.column) == (2, column)
    assert message in raised.value.message


def test_duplicate_question_id():
    rows = MANAGED_QUESTIONS.to_rows([MANAGED, MANAGED])

    with pytest.raises(RowError) as raised:
        managed_rows(rows)

    assert (raised.value.tab, raised.value.row, raised.value.column) == (
        "managed_questions", 3, "question_id",
    )  # fmt: skip
