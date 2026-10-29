"""The tutor settings and the `config` tab, which holds one `key`/`value` row per setting."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Any

from pydantic import Field, ValidationError

from .shared import cells
from .shared.models import Model
from .shared.tabs import Column, Row, RowError, check_header

# The FSRS-6 default parameters of py-fsrs 6.3.2 (fsrs.scheduler.DEFAULT_PARAMETERS).
DEFAULT_FSRS_WEIGHTS = (
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666, 0.796,
    1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542,
)  # fmt: skip


class Config(Model):
    """The entries of the `config` tab. A key missing from the tab takes its default."""

    schema_version: int = Field(default=1, ge=1)
    desired_retention: float = Field(default=0.9, gt=0, lt=1)
    fsrs_weights: list[float] = Field(
        default=list(DEFAULT_FSRS_WEIGHTS), min_length=21, max_length=21
    )
    # The scheduler settings of py-fsrs 6.3.2, with its defaults; steps are in minutes.
    learning_steps: list[Annotated[float, Field(gt=0)]] = Field(default=[1.0, 10.0])
    relearning_steps: list[Annotated[float, Field(gt=0)]] = Field(default=[10.0])
    maximum_interval: int = Field(default=36500, ge=1)
    enable_fuzzing: bool = True


@dataclass(frozen=True)
class ConfigTab:
    """A key/value tab: one row per field of `Config`, unlike `Tab`'s one row per model."""

    name: str
    entries: tuple[Column, ...]
    header: tuple[str, ...] = ("key", "value")

    def to_rows(self, config: Config) -> list[Row]:
        rows = [[entry.name, entry.format(getattr(config, entry.name))] for entry in self.entries]
        return [list(self.header), *rows]

    def from_rows(self, rows: Sequence[Sequence[Any]]) -> Config:
        check_header(self.name, rows, list(self.header))
        entries = {entry.name: entry for entry in self.entries}
        values, rows_of = {}, {}
        for number, row in enumerate(rows[1:], start=2):
            row = [str(cell) for cell in row]
            if len(row) > 2:
                raise RowError(self.name, number, None, f"{len(row)} cells, expected 2")
            key, cell = (*row, "", "")[:2]
            key = key.strip()
            if key not in entries:
                raise RowError(self.name, number, "key", f"unknown key {key!r}")
            if key in values:
                raise RowError(self.name, number, "key", f"duplicate key {key!r}")
            try:
                values[key] = entries[key].parse(cell)
            except ValueError as error:
                raise RowError(self.name, number, "value", f"{key}: {error}") from None
            rows_of[key] = number
        try:
            return Config.model_validate(values)
        except ValidationError as error:
            first = error.errors()[0]
            key = str(first["loc"][0])
            raise RowError(self.name, rows_of.get(key), "value", f"{key}: {first['msg']}") from None


CONFIG = ConfigTab(
    "config",
    (
        Column("schema_version", cells.format_int, cells.parse_int),
        Column("desired_retention", cells.format_float, cells.parse_float),
        Column("fsrs_weights", cells.format_float_list, cells.parse_float_list),
        Column("learning_steps", cells.format_float_list, cells.parse_float_list),
        Column("relearning_steps", cells.format_float_list, cells.parse_float_list),
        Column("maximum_interval", cells.format_int, cells.parse_int),
        Column("enable_fuzzing", cells.format_bool, cells.parse_bool),
    ),
)
