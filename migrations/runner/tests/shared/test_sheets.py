import pytest

from migrations.runner.shared.sheets import (
    GoogleSheetsClient,
    Sheet,
    TabValues,
    quote_title,
    to_cell,
)


@pytest.mark.parametrize(
    ("value", "cell"),
    [(True, "TRUE"), (False, "FALSE"), (3, "3"), (3.0, "3"), (0.9, "0.9"), ("x", "x")],
)
def test_cells_are_read_as_strings(value, cell):
    assert to_cell(value) == cell


def test_titles_are_quoted():
    assert quote_title("it's") == "'it''s'"


def test_free_sheet_ids():
    ids = Sheet({"a": TabValues(4), "b": TabValues(0)}).free_sheet_ids()
    assert [next(ids), next(ids)] == [5, 6]


class Call:
    def __init__(self, result=None, log=None, name=""):
        self.result, self.log, self.name = result, log, name

    def __call__(self, **kwargs):
        self.log.append((self.name, kwargs))
        return self

    def execute(self):
        return self.result


class FakeService:
    """The call chain of the Sheets API client, recording each call."""

    def __init__(self):
        self.log = []
        meta = {"sheets": [{"properties": {"sheetId": 7, "title": "questions"}}]}
        values = {"valueRanges": [{"values": [["id", "active"], ["a", True]]}]}
        self.get = Call(meta, self.log, "get")
        self.batchGet = Call(values, self.log, "batchGet")
        self.batchUpdate = Call({}, self.log, "batchUpdate")

    def spreadsheets(self):
        return self

    def values(self):
        return self


def test_google_client_reads_and_writes():
    service = FakeService()
    client = GoogleSheetsClient(service, "sheet-id")

    sheet = client.read()
    client.batch_update([{"addSheet": {}}])

    assert sheet.tabs == {"questions": TabValues(7, [["id", "active"], ["a", "TRUE"]])}
    calls = dict(service.log)
    assert calls["batchGet"]["ranges"] == ["'questions'"]
    assert calls["batchGet"]["valueRenderOption"] == "UNFORMATTED_VALUE"
    assert calls["batchUpdate"] == {
        "spreadsheetId": "sheet-id",
        "body": {"requests": [{"addSheet": {}}]},
    }
