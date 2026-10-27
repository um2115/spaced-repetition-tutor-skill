import io
import re
from pathlib import Path
from textwrap import dedent

import pytest

from migrations.runner import snapshots
from migrations.runner.migrate import Paths, main
from migrations.runner.tests.fake_sheets import FakeSheets
from migrations.schema.questions import QUESTIONS
from migrations.schema.workbook import TABS

ROOT = Path(__file__).resolve().parents[3]
ENV = {
    "SRT_SHEET_ID": "sheet",
    "SRT_OAUTH_CLIENT_SECRET": "secret.json",
    "SRT_OAUTH_TOKEN": "token.json",
}

GIT = """\
    topic: Git
    questions:
      - id: git-rebase
        tags: [branches]
        question: What does git rebase do?
        answer: It replays commits onto another base.
        explanation: Rebasing rewrites the commits of a branch on top of another commit.
      - id: git-stash
        question: What does git stash do?
        answer: It shelves uncommitted changes.
        explanation: The stash keeps changes aside so the working tree is clean.
"""

STRUCTURAL_STEP = """\
    from migrations.runner.shared.sheets import add_tab, append_rows

    STRUCTURAL = True


    def requests(sheet):
        sheet_id = next(sheet.free_sheet_ids())
        return [add_tab(sheet_id, "notes"), append_rows(sheet_id, [["note"]])]
"""

DATA_STEP = """\
    from migrations.runner.shared.sheets import append_rows

    STRUCTURAL = False


    def requests(sheet):
        return [append_rows(sheet.sheet_id("config"), [["desired_retention", "0.85"]])]
"""

FAILING_STEP = """\
    STRUCTURAL = False


    def requests(sheet):
        return [{"fail": {}}]
"""


class Terminal(io.StringIO):
    """Standard input typed by a person."""

    def isatty(self) -> bool:
        return True


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    paths = Paths(
        repo=tmp_path,
        questions=tmp_path / "migrations" / "questions",
        steps=tmp_path / "migrations" / "steps",
        snapshots=tmp_path / "snapshots",
    )
    paths.questions.mkdir(parents=True)
    paths.steps.mkdir(parents=True)
    write(paths.questions / "git.yaml", GIT)
    return paths


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text))


def run(fake: FakeSheets, paths: Paths, *args: str, stdin=None, environ=ENV) -> int:
    return main(
        list(args),
        environ=environ,
        connect=lambda settings: fake,
        stdin=stdin or io.StringIO(""),
        paths=paths,
    )


def migrated(paths: Paths) -> FakeSheets:
    """A sheet at schema version 1 that holds the YAML questions."""
    fake = FakeSheets()
    assert run(fake, paths, "--apply") == 0
    return fake


def documented_headers() -> dict[str, list[str]]:
    """The columns of each tab as `docs/data-schema.md` lists them."""
    text = (ROOT / "docs" / "data-schema.md").read_text()
    headers = {}
    for section in re.split(r"^## ", text, flags=re.M):
        if match := re.match(r"Tab: `(\w+)`", section):
            table = re.search(r"^\| (?:Column|Key) \|.*?\n\|[- |]+\n((?:\|.*\n)+)", section, re.M)
            headers[match[1]] = re.findall(r"^\| `(\w+)` \|", table[1], re.M)
    headers["config"] = ["key", "value"]
    return headers


def test_dry_run_writes_nothing_and_prints_the_plan(paths, capsys):
    fake = FakeSheets()

    assert run(fake, paths) == 0

    assert fake.batches == []
    output = capsys.readouterr().out
    assert "Dry run" in output
    for tab in TABS:
        assert f"create tab {tab.name}" in output
    assert "no snapshot" in output
    assert "append question git-rebase from migrations/questions/git.yaml" in output


def test_apply_to_an_empty_sheet(paths):
    fake = migrated(paths)
    values = fake.values()

    headers = documented_headers()
    assert set(headers) == {tab.name for tab in TABS}
    for tab in TABS:
        assert values[tab.name][0] == headers[tab.name]
    assert ["schema_version", "1"] in values["config"]
    assert [row[0] for row in values["questions"][1:]] == ["git-rebase", "git-stash"]
    assert QUESTIONS.from_row(values["questions"][1]).tags == ["branches"]
    assert values["managed_questions"][1:] == [
        ["git-rebase", "migrations/questions/git.yaml"],
        ["git-stash", "migrations/questions/git.yaml"],
    ]
    assert values["Sheet1"] == []


def test_new_config_gets_the_latest_version(paths):
    write(paths.steps / "0002_add_notes.py", STRUCTURAL_STEP)

    values = migrated(paths).values()

    assert ["schema_version", "2"] in values["config"]
    assert "notes" not in values


def test_second_run_without_changes_writes_nothing(paths, capsys):
    fake = migrated(paths)
    batches = len(fake.batches)
    capsys.readouterr()

    assert run(fake, paths, "--apply") == 0

    assert len(fake.batches) == batches
    output = capsys.readouterr().out
    assert "questions are up to date" in output
    assert "create tab" not in output


def test_report_names_every_kind_of_change(paths, capsys):
    fake = migrated(paths)
    questions = fake.tabs["questions"].rows
    questions[1][4] = "Something else."  # git-rebase answer, changed by hand
    questions.append(["hand-made", "Misc", "", "Q?", "A.", "E.", "TRUE"])
    questions.append(["git-merge", "not", "validated"])
    write(
        paths.questions / "git.yaml",
        GIT.replace("git-stash", "git-merge").replace("shelves", "joins"),
    )
    capsys.readouterr()

    assert run(fake, paths, "--apply") == 0

    output = capsys.readouterr().out
    assert "overwrite question git-rebase (row 2): answer" in output
    assert "managed question git-stash is no longer in YAML; left untouched" in output
    assert "unmanaged question hand-made (row 4) left untouched" in output
    assert "take over unmanaged question git-merge (row 5)" in output
    values = fake.values()
    assert values["questions"][1][4] == "It replays commits onto another base."
    assert values["questions"][2][0] == "git-stash"
    assert values["questions"][3][0] == "hand-made"
    assert QUESTIONS.from_row(values["questions"][4]).answer == "It joins uncommitted changes."
    assert ["git-merge", "migrations/questions/git.yaml"] in values["managed_questions"]

    assert run(fake, paths, "--apply") == 0
    assert "questions are up to date" in capsys.readouterr().out


def test_moved_question_updates_its_source_file(paths, capsys):
    fake = migrated(paths)
    (paths.questions / "git.yaml").rename(paths.questions / "vcs.yaml")

    assert run(fake, paths, "--apply") == 0

    assert "overwrite question git-rebase (row 2): source_file" in capsys.readouterr().out
    assert fake.values()["managed_questions"][1] == ["git-rebase", "migrations/questions/vcs.yaml"]


def test_malformed_managed_row_aborts(paths, capsys):
    fake = migrated(paths)
    fake.tabs["questions"].rows[2][6] = "maybe"
    batches = len(fake.batches)

    assert run(fake, paths, "--apply") == 1

    assert len(fake.batches) == batches
    assert "tab 'questions', row 3, column 'active'" in capsys.readouterr().err


def with_unmanaged_row_and_structural_step(paths: Paths) -> FakeSheets:
    fake = migrated(paths)
    fake.tabs["questions"].rows.append(["hand-made", "Misc"])
    write(paths.steps / "0002_add_notes.py", STRUCTURAL_STEP)
    return fake


def test_unmanaged_rows_before_a_structural_step_ask_first(paths, capsys):
    fake = with_unmanaged_row_and_structural_step(paths)
    batches = len(fake.batches)

    assert run(fake, paths, "--apply", stdin=Terminal("n\n")) == 1

    assert len(fake.batches) == batches
    captured = capsys.readouterr()
    assert "hand-made" in captured.out
    assert "may break" in captured.out
    assert "Continue? [y/N]" in captured.out
    assert "Nothing was written" in captured.err
    assert not paths.snapshots.exists()


def test_non_interactive_input_aborts(paths, capsys):
    fake = with_unmanaged_row_and_structural_step(paths)
    batches = len(fake.batches)

    assert run(fake, paths, "--apply", stdin=io.StringIO("y\n")) == 1

    assert len(fake.batches) == batches
    assert "not interactive" in capsys.readouterr().err


def test_confirmed_structural_step_runs(paths, capsys):
    fake = with_unmanaged_row_and_structural_step(paths)

    assert run(fake, paths, "--apply", stdin=Terminal("y\n")) == 0

    assert fake.values()["notes"] == [["note"]]
    assert "unmanaged question hand-made (row 4) left untouched" in capsys.readouterr().out


def test_dry_run_warns_but_does_not_ask(paths, capsys):
    fake = with_unmanaged_row_and_structural_step(paths)
    batches = len(fake.batches)

    assert run(fake, paths) == 0

    assert len(fake.batches) == batches
    output = capsys.readouterr().out
    assert "may break" in output
    assert "Continue?" not in output
    assert "take a snapshot before step 0002_add_notes" in output


def test_snapshot_before_the_first_structural_step(paths, capsys):
    fake = migrated(paths)
    before = fake.values()
    write(paths.steps / "0002_add_notes.py", STRUCTURAL_STEP)
    write(paths.steps / "0003_tune.py", DATA_STEP)
    write(paths.steps / "0004_more_notes.py", STRUCTURAL_STEP.replace('"notes"', '"more"'))
    capsys.readouterr()

    assert run(fake, paths, "--apply") == 0

    (snapshot,) = paths.snapshots.iterdir()
    assert f"snapshot saved to {snapshot}" in capsys.readouterr().out
    assert {path.stem for path in snapshot.glob("*.csv")} == set(before)
    assert snapshots.load(snapshot) == before


@pytest.mark.parametrize("steps", [{}, {"0002_tune.py": DATA_STEP}])
def test_no_snapshot_without_a_structural_step(paths, capsys, steps):
    fake = migrated(paths)
    for name, text in steps.items():
        write(paths.steps / name, text)

    assert run(fake, paths, "--apply") == 0

    assert not paths.snapshots.exists()
    assert "snapshot" not in capsys.readouterr().out


def test_failing_snapshot_aborts_before_any_write(paths, capsys):
    paths.snapshots.write_text("a file, not a directory")
    write(paths.steps / "0002_add_notes.py", STRUCTURAL_STEP)
    fake = migrated(paths)  # a new config starts at version 2, so no step runs yet
    fake.tabs["config"].rows[1] = ["schema_version", "1"]
    batches = len(fake.batches)

    assert run(fake, paths, "--apply") == 1

    assert len(fake.batches) == batches
    assert "cannot write the snapshot" in capsys.readouterr().err


def test_each_step_sets_the_version_and_logs_itself_in_one_batch(paths):
    fake = migrated(paths)
    batches = len(fake.batches)
    write(paths.steps / "0002_tune.py", DATA_STEP)
    write(paths.steps / "0003_add_notes.py", STRUCTURAL_STEP)

    assert run(fake, paths, "--apply") == 0

    step_batches = fake.batches[batches:]
    assert len(step_batches) == 2
    assert all(len(batch) >= 3 for batch in step_batches)
    values = fake.values()
    assert ["schema_version", "3"] in values["config"]
    assert [row[:2] for row in values["migrations"][1:]] == [["2", "tune"], ["3", "add_notes"]]
    assert values["migrations"][1][2].endswith("Z")


def test_failing_step_keeps_earlier_steps_and_the_next_run_resumes(paths, capsys):
    fake = migrated(paths)
    write(paths.steps / "0002_tune.py", DATA_STEP)
    write(paths.steps / "0003_broken.py", FAILING_STEP)

    assert run(fake, paths, "--apply") == 1

    assert "step 0003_broken failed" in capsys.readouterr().err
    values = fake.values()
    assert ["schema_version", "2"] in values["config"]
    assert len(values["migrations"]) == 2

    write(paths.steps / "0003_broken.py", STRUCTURAL_STEP)
    assert run(fake, paths, "--apply") == 0

    output = capsys.readouterr().out
    assert "run step 0002_tune" not in output
    assert "applied step 0003_broken" in output
    values = fake.values()
    assert ["schema_version", "3"] in values["config"]
    assert [row[0] for row in values["migrations"][1:]] == ["2", "3"]
    assert values["config"].count(["desired_retention", "0.85"]) == 1


def test_newer_sheet_aborts(paths, capsys):
    fake = migrated(paths)
    fake.tabs["config"].rows[1] = ["schema_version", "2"]
    batches = len(fake.batches)

    assert run(fake, paths, "--apply") == 1

    assert len(fake.batches) == batches
    assert "update the repository" in capsys.readouterr().err.lower()


def test_wrong_header_names_the_tab(paths, capsys):
    fake = migrated(paths)
    fake.tabs["state"].rows[0][1] = "status"
    batches = len(fake.batches)

    assert run(fake, paths, "--apply") == 1

    assert len(fake.batches) == batches
    assert "tab 'state', row 1: header" in capsys.readouterr().err


def test_invalid_yaml_aborts_before_any_network_call(paths, capsys):
    write(paths.questions / "bad.yaml", "topic: Bad\nquestions:\n  - id: Bad-Id\n")

    def connect(settings):
        raise AssertionError("connected")

    assert main(["--apply"], environ=ENV, connect=connect, paths=paths) == 1
    assert "bad.yaml: question Bad-Id: field id" in capsys.readouterr().err


def test_missing_setting_names_variable_and_flag(paths, capsys):
    def connect(settings):
        raise AssertionError("connected")

    environ = {"SRT_OAUTH_TOKEN": "token.json"}
    assert main([], environ=environ, connect=connect, paths=paths) == 1

    error = capsys.readouterr().err
    assert "set SRT_SHEET_ID or pass --sheet-id" in error
    assert "set SRT_OAUTH_CLIENT_SECRET or pass --client-secret" in error
    assert "SRT_OAUTH_TOKEN" not in error
