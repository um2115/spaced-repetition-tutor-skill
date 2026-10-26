from datetime import UTC, datetime

import pytest

from migrations.schema.logs import LOG, LogEntry
from migrations.schema.shared.tabs import RowError

ENTRY = LogEntry(
    timestamp=datetime(2026, 10, 26, 14, 30, 5, tzinfo=UTC),
    question_id="k8s-pod-lifecycle",
    answer_text="  pending, running, done ",
    rating=2,
    judgement="Missed Failed and Unknown.",
    seconds_to_answer=12.5,
)


def test_header_matches_the_spec():
    assert LOG.header == [
        "timestamp", "question_id", "answer_text", "rating", "judgement", "seconds_to_answer",
    ]  # fmt: skip


@pytest.mark.parametrize(
    "entry", [ENTRY, ENTRY.model_copy(update={"answer_text": "", "seconds_to_answer": 0.0})]
)
def test_row_round_trip(entry):
    row = LOG.to_row(entry)

    assert len(row) == len(LOG.header)
    assert LOG.from_row(row) == entry
    assert LOG.from_rows(LOG.to_rows([entry])) == [entry]


def log_row(**cells):
    row = dict(zip(LOG.header, LOG.to_row(ENTRY), strict=True))
    row.update(cells)
    return list(row.values())


@pytest.mark.parametrize(
    ("row", "column", "message"),
    [
        (log_row(rating="5"), "rating", "less than or equal to 4"),
        (log_row(rating="0"), "rating", "greater than or equal to 1"),
        (log_row(rating="good"), "rating", "not an integer"),
        (log_row(timestamp="now"), "timestamp", "not an ISO 8601 timestamp"),
        (log_row(seconds_to_answer="-1"), "seconds_to_answer", "greater than or equal"),
    ],
)
def test_malformed_row(row, column, message):
    with pytest.raises(RowError) as raised:
        LOG.from_rows([LOG.header, row])

    assert (raised.value.tab, raised.value.row, raised.value.column) == ("log", 2, column)
    assert message in raised.value.message
