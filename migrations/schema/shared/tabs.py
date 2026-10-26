"""Map a model to a Google Sheets tab: column order, header names and cell formats.

A row is a list of cell strings in column order. Row numbers in errors are sheet row numbers,
so the header is row 1 and the first data row is row 2.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

Row = list[str]


class RowError(ValueError):
    """A sheet row that does not match its model."""

    def __init__(self, tab: str, row: int | None, column: str | None, message: str):
        self.tab, self.row, self.column, self.message = tab, row, column, message
        where = f"tab {tab!r}"
        if row is not None:
            where += f", row {row}"
        if column is not None:
            where += f", column {column!r}"
        super().__init__(f"{where}: {message}")


@dataclass(frozen=True)
class Column:
    """A column, or a config key: its name and how its value is written to and read from a cell."""

    name: str
    format: Callable[[Any], str]
    parse: Callable[[str], Any]


@dataclass(frozen=True)
class Tab:
    """A tab with one model instance per row and one model field per column."""

    name: str
    model: type[BaseModel]
    columns: tuple[Column, ...]

    @property
    def header(self) -> Row:
        return [column.name for column in self.columns]

    def to_row(self, item: BaseModel) -> Row:
        return [column.format(getattr(item, column.name)) for column in self.columns]

    def from_row(self, row: Sequence[Any], row_number: int | None = None) -> BaseModel:
        if len(row) > len(self.columns):
            raise RowError(
                self.name, row_number, None, f"{len(row)} cells, expected {len(self.columns)}"
            )
        # The Sheets API leaves out trailing empty cells, so a short row is padded.
        row = [*(str(cell) for cell in row), *[""] * (len(self.columns) - len(row))]
        values = {}
        for column, cell in zip(self.columns, row, strict=True):
            try:
                values[column.name] = column.parse(cell)
            except ValueError as error:
                raise RowError(self.name, row_number, column.name, str(error)) from None
        try:
            return self.model.model_validate(values)
        except ValidationError as error:
            first = error.errors()[0]
            raise RowError(self.name, row_number, str(first["loc"][0]), first["msg"]) from None

    def to_rows(self, items: Sequence[BaseModel]) -> list[Row]:
        return [self.header, *(self.to_row(item) for item in items)]

    def from_rows(self, rows: Sequence[Sequence[Any]]) -> list[BaseModel]:
        check_header(self.name, rows, self.header)
        return [self.from_row(row, number) for number, row in enumerate(rows[1:], start=2)]


def check_header(tab: str, rows: Sequence[Sequence[Any]], header: Row) -> None:
    """Raise a RowError unless the first row is `header`."""
    if not rows or [str(cell) for cell in rows[0]] != header:
        found = list(rows[0]) if rows else []
        raise RowError(tab, 1, None, f"header {found} does not match {header}")
