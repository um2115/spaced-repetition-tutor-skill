"""The FSRS review state of a question and the `state` tab, written by the agent only.

A question gets its row on its first review, so a question without a row is new.
"""

from enum import StrEnum

from pydantic import Field

from .shared import cells
from .shared.models import Model, QuestionId, Timestamp
from .shared.tabs import Column, Tab


class FsrsState(StrEnum):
    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    RELEARNING = "relearning"


class State(Model):
    """A row of the `state` tab: the py-fsrs card fields plus `reps` and `lapses`."""

    question_id: QuestionId
    fsrs_state: FsrsState
    step: int | None = None
    stability: float | None = None
    difficulty: float | None = None
    due: Timestamp
    last_review: Timestamp | None = None
    reps: int = Field(default=0, ge=0)
    lapses: int = Field(default=0, ge=0)


def _parse_fsrs_state(cell: str) -> FsrsState:
    try:
        return FsrsState(cell.strip())
    except ValueError:
        allowed = ", ".join(state.value for state in FsrsState)
        raise ValueError(f"not one of {allowed}: {cell!r}") from None


STATE = Tab(
    "state",
    State,
    (
        Column("question_id", cells.format_str, cells.parse_str),
        Column("fsrs_state", lambda state: state.value, _parse_fsrs_state),
        Column("step", cells.format_int, cells.parse_optional_int),
        Column("stability", cells.format_float, cells.parse_optional_float),
        Column("difficulty", cells.format_float, cells.parse_optional_float),
        Column("due", cells.format_timestamp, cells.parse_timestamp),
        Column("last_review", cells.format_timestamp, cells.parse_optional_timestamp),
        Column("reps", cells.format_int, cells.parse_int),
        Column("lapses", cells.format_int, cells.parse_int),
    ),
)
