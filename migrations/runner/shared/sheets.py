"""Read a Google Sheet and change it with `spreadsheets.batchUpdate` requests.

Every cell is read as a string and written as a string, so the row mapping in
`migrations/schema/` sees the same values it writes. Each `batch_update` call is one
`spreadsheets.batchUpdate`, which Google Sheets applies atomically.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

Row = list[str]
Request = dict[str, Any]


@dataclass
class TabValues:
    sheet_id: int
    rows: list[Row] = field(default_factory=list)


@dataclass
class Sheet:
    """The cell values of every tab, as read: unvalidated and without trailing empty cells."""

    tabs: dict[str, TabValues] = field(default_factory=dict)

    def __contains__(self, name: str) -> bool:
        return name in self.tabs

    def rows(self, name: str) -> list[Row]:
        return self.tabs[name].rows if name in self.tabs else []

    def sheet_id(self, name: str) -> int:
        return self.tabs[name].sheet_id

    def free_sheet_ids(self) -> Iterator[int]:
        """Sheet ids no tab uses yet, for new tabs."""
        next_id = max((tab.sheet_id for tab in self.tabs.values()), default=0) + 1
        while True:
            yield next_id
            next_id += 1


class SheetsClient(Protocol):
    def read(self) -> Sheet: ...

    def batch_update(self, requests: list[Request]) -> None: ...


class GoogleSheetsClient:
    """A `SheetsClient` for one spreadsheet, given a Sheets API v4 service."""

    def __init__(self, service: Any, spreadsheet_id: str):
        self._spreadsheets = service.spreadsheets()
        self._id = spreadsheet_id

    def read(self) -> Sheet:
        meta = self._spreadsheets.get(
            spreadsheetId=self._id, fields="sheets.properties(sheetId,title)"
        ).execute()
        properties = [sheet["properties"] for sheet in meta.get("sheets", [])]
        response = (
            self._spreadsheets.values()
            .batchGet(
                spreadsheetId=self._id,
                ranges=[quote_title(p["title"]) for p in properties],
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="FORMATTED_STRING",
            )
            .execute()
        )
        value_ranges = response.get("valueRanges", [])
        return Sheet(
            {
                p["title"]: TabValues(p["sheetId"], to_rows(values.get("values", [])))
                for p, values in zip(properties, value_ranges, strict=True)
            }
        )

    def batch_update(self, requests: list[Request]) -> None:
        self._spreadsheets.batchUpdate(
            spreadsheetId=self._id, body={"requests": requests}
        ).execute()


def quote_title(title: str) -> str:
    """An A1 range that covers the whole tab called `title`."""
    return "'" + title.replace("'", "''") + "'"


def to_rows(values: Sequence[Sequence[Any]]) -> list[Row]:
    return [[to_cell(value) for value in row] for row in values]


def to_cell(value: Any) -> str:
    """A cell value from the API as the string the row mapping reads."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def add_tab(sheet_id: int, title: str) -> Request:
    return {"addSheet": {"properties": {"sheetId": sheet_id, "title": title}}}


def append_rows(sheet_id: int, rows: Sequence[Row]) -> Request:
    """Append `rows` after the last row with data, adding grid rows as needed."""
    return {
        "appendCells": {
            "sheetId": sheet_id,
            "rows": [_row_data(row) for row in rows],
            "fields": "userEnteredValue",
        }
    }


def write_row(sheet_id: int, row_number: int, row: Row, column: int = 0) -> Request:
    """Write `row` into sheet row `row_number` (1 is the header), starting at `column`."""
    return {
        "updateCells": {
            "start": {"sheetId": sheet_id, "rowIndex": row_number - 1, "columnIndex": column},
            "rows": [_row_data(row)],
            "fields": "userEnteredValue",
        }
    }


def clear_row(sheet_id: int, row_number: int) -> Request:
    """Clear every cell of sheet row `row_number`."""
    grid_range = {"sheetId": sheet_id, "startRowIndex": row_number - 1, "endRowIndex": row_number}
    return {"updateCells": {"range": grid_range, "fields": "userEnteredValue"}}


def clear_tab(sheet_id: int) -> Request:
    """Clear every cell of the tab."""
    return {"updateCells": {"range": {"sheetId": sheet_id}, "fields": "userEnteredValue"}}


def _row_data(row: Row) -> dict:
    # A cell without a value is written empty.
    return {"values": [{"userEnteredValue": {"stringValue": cell}} if cell else {} for cell in row]}
