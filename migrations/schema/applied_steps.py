"""The applied migration steps and the `migrations` tab, written by the migration script only.

Version 1 is the schema a new sheet starts with, so the first step has version 2.
"""

from pydantic import Field

from .shared import cells
from .shared.models import Model, NonEmptyStr, Timestamp
from .shared.tabs import Column, Tab


class AppliedStep(Model):
    """A row of the `migrations` tab: one migration step applied to the sheet."""

    version: int = Field(ge=2)
    name: NonEmptyStr
    applied_at: Timestamp


APPLIED_STEPS = Tab(
    "migrations",
    AppliedStep,
    (
        Column("version", cells.format_int, cells.parse_int),
        Column("name", cells.format_str, cells.parse_str),
        Column("applied_at", cells.format_timestamp, cells.parse_timestamp),
    ),
)
