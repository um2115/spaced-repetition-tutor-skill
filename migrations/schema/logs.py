"""The answer attempts and the `log` tab, to which the agent only appends."""

from pydantic import Field

from .shared import cells
from .shared.models import Model, QuestionId, Timestamp
from .shared.tabs import Column, Tab


class LogEntry(Model):
    """A row of the `log` tab: one answer attempt."""

    timestamp: Timestamp
    question_id: QuestionId
    answer_text: str
    rating: int = Field(ge=1, le=4, description="1 Again, 2 Hard, 3 Good, 4 Easy")
    judgement: str
    seconds_to_answer: float = Field(ge=0)


LOG = Tab(
    "log",
    LogEntry,
    (
        Column("timestamp", cells.format_timestamp, cells.parse_timestamp),
        Column("question_id", cells.format_str, cells.parse_str),
        Column("answer_text", cells.format_str, cells.parse_str),
        Column("rating", cells.format_int, cells.parse_int),
        Column("judgement", cells.format_str, cells.parse_str),
        Column("seconds_to_answer", cells.format_float, cells.parse_float),
    ),
)
