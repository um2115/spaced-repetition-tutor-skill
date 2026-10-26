"""The questions and the `questions` tab, written by migrations or by hand."""

from typing import Annotated

from pydantic import AfterValidator

from .shared import cells
from .shared.models import Model, NonEmptyStr, QuestionId
from .shared.tabs import Column, Tab


def _valid_tag(value: str) -> str:
    if not value or value != value.strip() or "," in value:
        raise ValueError("a tag must be non-empty, without commas or surrounding whitespace")
    return value


Tag = Annotated[str, AfterValidator(_valid_tag)]


class QuestionEntry(Model):
    """A question as written in the `questions` list of a YAML question file.

    It has every field of `Question` except `topic`. A YAML file holds one topic and names it
    once in its top-level `topic` field, so the entries do not repeat it. Because unknown fields
    are rejected, a `topic` inside an entry is an error.

    `load_file` in `questions_file.py` turns each entry into a `Question` by adding the topic of
    its file.
    """

    id: QuestionId
    tags: list[Tag] = []
    question: NonEmptyStr
    answer: NonEmptyStr
    explanation: NonEmptyStr
    active: bool = True


class Question(QuestionEntry):
    """A complete question: a row of the `questions` tab.

    It is a `QuestionEntry` plus its `topic`. In the sheet, the rows of all topics share one tab,
    so every row carries its own topic. A YAML file instead names the topic once for all of its
    entries; see `QuestionEntry`.

    Use this model everywhere except when validating a YAML file's entries. Two models instead of
    one with an optional `topic` keep both mistakes errors: a sheet row without a topic, and a
    YAML entry with one.
    """

    topic: NonEmptyStr


def _parse_active(cell: str) -> bool:
    return True if cell.strip() == "" else cells.parse_bool(cell)


QUESTIONS = Tab(
    "questions",
    Question,
    (
        Column("id", cells.format_str, cells.parse_str),
        Column("topic", cells.format_str, cells.parse_str),
        Column("tags", cells.format_list, cells.parse_list),
        Column("question", cells.format_str, cells.parse_str),
        Column("answer", cells.format_str, cells.parse_str),
        Column("explanation", cells.format_str, cells.parse_str),
        Column("active", cells.format_bool, _parse_active),
    ),
)
