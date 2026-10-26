from datetime import UTC, datetime, timedelta, timezone

import pytest

from migrations.schema.fsrs_states import STATE, FsrsState, State
from migrations.schema.shared.tabs import RowError

REVIEWED = State(
    question_id="k8s-pod-lifecycle",
    fsrs_state=FsrsState.REVIEW,
    step=None,
    stability=12.345678901234,
    difficulty=5.5,
    due=datetime(2026, 10, 26, 14, 30, tzinfo=UTC),
    last_review=datetime(2026, 10, 14, 9, 0, 0, 123456, tzinfo=UTC),
    reps=4,
    lapses=1,
)
LEARNING = State(
    question_id="new-question",
    fsrs_state=FsrsState.LEARNING,
    step=0,
    due=datetime(2026, 10, 26, tzinfo=UTC),
    reps=0,
    lapses=0,
)


def test_header_matches_the_spec():
    assert STATE.header == [
        "question_id", "fsrs_state", "step", "stability", "difficulty",
        "due", "last_review", "reps", "lapses",
    ]  # fmt: skip


@pytest.mark.parametrize("state", [REVIEWED, LEARNING])
def test_row_round_trip(state):
    row = STATE.to_row(state)

    assert len(row) == len(STATE.header)
    assert STATE.from_row(row) == state
    assert STATE.from_rows(STATE.to_rows([state])) == [state]


def test_cell_formats():
    row = STATE.to_row(REVIEWED)
    assert row[1:3] == ["review", ""]
    assert row[5:7] == ["2026-10-26T14:30:00Z", "2026-10-14T09:00:00.123456Z"]
    assert STATE.to_row(LEARNING)[2:5] == ["0", "", ""]


def test_timestamps_are_normalised_to_utc():
    due = datetime(2026, 10, 26, 16, 30, tzinfo=timezone(timedelta(hours=2)))
    assert State.model_validate({**REVIEWED.model_dump(), "due": due}).due.tzinfo == UTC

    state = STATE.from_row(["q", "new", "", "", "", "2026-10-26T16:30:00+02:00", "", "0", "0"])
    assert state.due == datetime(2026, 10, 26, 14, 30, tzinfo=UTC)
    assert state.due.tzinfo == UTC


def state_row(**cells):
    row = dict(zip(STATE.header, STATE.to_row(REVIEWED), strict=True))
    row.update(cells)
    return list(row.values())


@pytest.mark.parametrize(
    ("row", "column", "message"),
    [
        (state_row(fsrs_state="done"), "fsrs_state", "not one of new, learning"),
        (state_row(due="tomorrow"), "due", "not an ISO 8601 timestamp"),
        (state_row(due="2026-10-26T14:30:00"), "due", "no time zone"),
        (state_row(due=""), "due", "not an ISO 8601 timestamp"),
        (state_row(stability="high"), "stability", "not a number"),
        (state_row(step="1.5"), "step", "not an integer"),
        (state_row(reps="-1"), "reps", "greater than or equal to 0"),
        (state_row(question_id="Bad Id"), "question_id", "should match pattern"),
    ],
)
def test_malformed_row(row, column, message):
    with pytest.raises(RowError) as raised:
        STATE.from_rows([STATE.header, row])

    error = raised.value
    assert (error.tab, error.row, error.column) == ("state", 2, column)
    assert message in error.message
    assert str(error).startswith(f"tab 'state', row 2, column {column!r}: ")
