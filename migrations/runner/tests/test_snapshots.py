from datetime import UTC, datetime
from pathlib import Path

import pytest

from migrations.runner import snapshots
from migrations.runner.shared.errors import Abort
from migrations.runner.shared.sheets import Sheet, TabValues

SHEET = Sheet(
    {
        "questions": TabValues(1, [["id", "topic"], ["Not A Slug", "with, comma\nand newline"]]),
        "a/b": TabValues(2, [["x"], [], ["y", "", "z"]]),
        "empty": TabValues(3, []),
    }
)


def test_round_trip_keeps_raw_values(tmp_path: Path):
    now = datetime(2026, 10, 26, 14, 30, 5, tzinfo=UTC)

    directory = snapshots.save(SHEET, tmp_path, now)

    assert directory == tmp_path / "20261026T143005Z"
    assert snapshots.load(directory) == {title: tab.rows for title, tab in SHEET.tabs.items()}


def test_unwritable_directory(tmp_path: Path):
    (tmp_path / "file").write_text("")

    with pytest.raises(Abort, match="cannot write the snapshot"):
        snapshots.save(SHEET, tmp_path / "file")


def test_missing_or_empty_directory(tmp_path: Path):
    with pytest.raises(Abort, match="not found"):
        snapshots.load(tmp_path / "missing")
    with pytest.raises(Abort, match="no CSV files"):
        snapshots.load(tmp_path)
