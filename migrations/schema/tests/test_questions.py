import pytest

from migrations.schema.questions import QUESTIONS, Question
from migrations.schema.shared.tabs import RowError

QUESTION = Question(
    id="k8s-pod-lifecycle",
    topic="Kubernetes",
    tags=["pods", "basics"],
    question="Which phases can a pod be in?",
    answer="Pending, Running, Succeeded, Failed, Unknown",
    explanation="A multi-line\nexplanation, with commas.",
)
RETIRED = QUESTION.model_copy(update={"tags": [], "active": False})


def test_header_matches_the_spec():
    assert QUESTIONS.header == [
        "id", "topic", "tags", "question", "answer", "explanation", "active",
    ]  # fmt: skip


@pytest.mark.parametrize("question", [QUESTION, RETIRED])
def test_row_round_trip(question):
    row = QUESTIONS.to_row(question)

    assert len(row) == len(QUESTIONS.header)
    assert QUESTIONS.from_row(row) == question
    assert QUESTIONS.from_rows(QUESTIONS.to_rows([question])) == [question]


def test_cell_formats():
    assert QUESTIONS.to_row(QUESTION)[2::4] == ["pods,basics", "TRUE"]
    assert QUESTIONS.to_row(RETIRED)[2::4] == ["", "FALSE"]


def test_cell_parsing():
    row = ["k8s-pod-lifecycle", "Kubernetes", " pods , basics ", "Q?", "A.", "Why.", ""]

    question = QUESTIONS.from_row(row)

    assert question.tags == ["pods", "basics"]
    assert question.active is True


@pytest.mark.parametrize(
    ("row", "column", "message"),
    [
        (["a", "T", "", "Q", "", "E", "TRUE"], "answer", "must not be empty"),
        (["a", "", "", "Q", "A", "E", "TRUE"], "topic", "must not be empty"),
        (["a", "T", "", "Q", "A", "E", "yes"], "active", "not TRUE or FALSE"),
        (["a", "T", "x,,y", "Q", "A", "E", "TRUE"], "tags", "without commas"),
        (["A b", "T", "", "Q", "A", "E", "TRUE"], "id", "should match pattern"),
    ],
)
def test_malformed_row(row, column, message):
    with pytest.raises(RowError) as raised:
        QUESTIONS.from_rows([QUESTIONS.header, row])

    assert (raised.value.tab, raised.value.row, raised.value.column) == ("questions", 2, column)
    assert message in raised.value.message
