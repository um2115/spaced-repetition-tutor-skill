import pytest

from migrations.schema.shared import cells
from migrations.schema.shared.models import Model, NonEmptyStr
from migrations.schema.shared.tabs import Column, RowError, Tab


class Item(Model):
    name: NonEmptyStr
    note: str = ""


ITEMS = Tab(
    "items",
    Item,
    (
        Column("name", cells.format_str, cells.parse_str),
        Column("note", cells.format_str, cells.parse_str),
    ),
)


def test_header_comes_from_the_columns():
    assert ITEMS.header == ["name", "note"]
    assert ITEMS.to_rows([Item(name="a")]) == [["name", "note"], ["a", ""]]


def test_trailing_empty_cells_may_be_missing():
    # The Sheets API leaves out trailing empty cells.
    assert ITEMS.from_row(["a"]) == Item(name="a")


def test_row_with_too_many_cells():
    with pytest.raises(RowError) as raised:
        ITEMS.from_row(["a", "b", "c"], 7)

    assert (raised.value.tab, raised.value.row, raised.value.column) == ("items", 7, None)
    assert "3 cells, expected 2" in raised.value.message


@pytest.mark.parametrize("rows", [[], [["note", "name"]]])
def test_wrong_header(rows):
    with pytest.raises(RowError) as raised:
        ITEMS.from_rows(rows)

    assert (raised.value.tab, raised.value.row, raised.value.column) == ("items", 1, None)


def test_rows_are_numbered_like_the_sheet():
    with pytest.raises(RowError) as raised:
        ITEMS.from_rows([ITEMS.header, ["a"], [""]])

    assert (raised.value.row, raised.value.column) == (3, "name")
    assert str(raised.value) == "tab 'items', row 3, column 'name': Value error, must not be empty"
