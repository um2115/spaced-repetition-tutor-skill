"""The base model and the field types that several tabs share."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field

ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class Model(BaseModel):
    """Base of every model: unknown fields are errors and values are not coerced."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be empty")
    return value


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


NonEmptyStr = Annotated[str, AfterValidator(_not_blank)]
QuestionId = Annotated[str, Field(pattern=ID_PATTERN)]
Timestamp = Annotated[AwareDatetime, AfterValidator(_to_utc)]
