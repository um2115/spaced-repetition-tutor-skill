from pathlib import Path

from migrations.runner import snapshots
from migrations.runner.restore import main
from migrations.runner.shared.sheets import Sheet, TabValues
from migrations.runner.tests.fake_sheets import FakeSheets

ENV = {"SRT_SHEET_ID": "s", "SRT_OAUTH_CLIENT_SECRET": "c.json", "SRT_OAUTH_TOKEN": "t.json"}
SNAPSHOT = {
    "config": [["key", "value"], ["schema_version", "1"]],
    "questions": [["id", "topic"], ["hand made", "x"]],
    "notes": [["n"]],
}


def restore(fake: FakeSheets, directory: Path, *args: str) -> int:
    return main([str(directory), *args], environ=ENV, connect=lambda settings: fake)


def snapshot(tmp_path: Path) -> Path:
    sheet = Sheet({title: TabValues(0, rows) for title, rows in SNAPSHOT.items()})
    return snapshots.save(sheet, tmp_path)


def current() -> FakeSheets:
    return FakeSheets(
        {
            "config": [["key", "value"], ["schema_version", "2"], ["desired_retention", "0.8"]],
            "questions": [["id"], ["a"], ["b"], ["c"]],
            "log": [["timestamp"], ["2026"]],
        }
    )


def test_dry_run_writes_nothing(tmp_path: Path, capsys):
    fake = current()

    assert restore(fake, snapshot(tmp_path)) == 0

    assert fake.batches == []
    output = capsys.readouterr().out
    assert "replace tab config with 2 row(s)" in output
    assert "create tab notes with 1 row(s)" in output
    assert "leave tab log untouched" in output
    assert "state and log rows written after the snapshot" in output


def test_apply_writes_the_snapshot_back(tmp_path: Path):
    fake = current()

    assert restore(fake, snapshot(tmp_path), "--apply") == 0

    assert len(fake.batches) == 1
    values = fake.values()
    assert {title: values[title] for title in SNAPSHOT} == SNAPSHOT
    assert values["log"] == [["timestamp"], ["2026"]]


def test_invalid_snapshot_directory(tmp_path: Path, capsys):
    fake = current()

    assert restore(fake, tmp_path / "missing", "--apply") == 1
    assert restore(fake, tmp_path, "--apply") == 1

    assert fake.batches == []
    error = capsys.readouterr().err
    assert "not found" in error
    assert "no CSV files" in error
