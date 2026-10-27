"""An in-memory `SheetsClient` that applies the `batchUpdate` requests the runner sends."""

import copy

from migrations.runner.shared.sheets import Request, Row, Sheet, TabValues


class FakeSheets:
    """A spreadsheet in memory. A batch is applied atomically, like `spreadsheets.batchUpdate`;
    an unknown request kind fails the whole batch."""

    def __init__(self, tabs: dict[str, list[Row]] | None = None):
        tabs = {"Sheet1": []} if tabs is None else tabs
        self.tabs = {
            title: TabValues(sheet_id, [list(row) for row in rows])
            for sheet_id, (title, rows) in enumerate(tabs.items())
        }
        self.batches: list[list[Request]] = []

    def read(self) -> Sheet:
        return Sheet(
            {title: TabValues(tab.sheet_id, _trim(tab.rows)) for title, tab in self.tabs.items()}
        )

    def values(self) -> dict[str, list[Row]]:
        return {title: tab.rows for title, tab in self.read().tabs.items()}

    def batch_update(self, requests: list[Request]) -> None:
        tabs = copy.deepcopy(self.tabs)
        for request in requests:
            ((kind, body),) = request.items()
            getattr(self, f"_{kind}")(tabs, body)
        self.tabs = tabs
        self.batches.append(requests)

    @staticmethod
    def _addSheet(tabs: dict[str, TabValues], body: dict) -> None:
        properties = body["properties"]
        assert properties["title"] not in tabs
        assert properties["sheetId"] not in {tab.sheet_id for tab in tabs.values()}
        tabs[properties["title"]] = TabValues(properties["sheetId"], [])

    @staticmethod
    def _appendCells(tabs: dict[str, TabValues], body: dict) -> None:
        rows = _tab(tabs, body["sheetId"]).rows
        last = max((i for i, row in enumerate(rows) if any(row)), default=-1)
        for offset, row_data in enumerate(body["rows"]):
            _set_row(rows, last + 1 + offset, 0, row_data)

    @staticmethod
    def _updateCells(tabs: dict[str, TabValues], body: dict) -> None:
        if "start" in body:
            start = body["start"]
            rows = _tab(tabs, start["sheetId"]).rows
            for offset, row_data in enumerate(body["rows"]):
                _set_row(rows, start["rowIndex"] + offset, start["columnIndex"], row_data)
            return
        grid = body["range"]
        rows = _tab(tabs, grid["sheetId"]).rows
        assert "rows" not in body
        for index in range(
            grid.get("startRowIndex", 0), min(grid.get("endRowIndex", len(rows)), len(rows))
        ):
            rows[index] = []


def _tab(tabs: dict[str, TabValues], sheet_id: int) -> TabValues:
    return next(tab for tab in tabs.values() if tab.sheet_id == sheet_id)


def _set_row(rows: list[Row], index: int, column: int, row_data: dict) -> None:
    while len(rows) <= index:
        rows.append([])
    row = rows[index]
    for offset, cell in enumerate(row_data.get("values", [])):
        while len(row) <= column + offset:
            row.append("")
        row[column + offset] = cell.get("userEnteredValue", {}).get("stringValue", "")


def _trim(rows: list[Row]) -> list[Row]:
    """Like the Sheets API: no trailing empty cells, no trailing empty rows."""
    trimmed = [list(row) for row in rows]
    for row in trimmed:
        while row and row[-1] == "":
            row.pop()
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    return trimmed
