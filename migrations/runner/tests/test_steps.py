from pathlib import Path

import pytest

from migrations.runner.shared.errors import Abort
from migrations.runner.shared.sheets import Sheet
from migrations.runner.steps import STEPS, discover, latest_version

STEP = """\
STRUCTURAL = {structural}


def requests(sheet):
    return [{{"step": {version}}}]
"""


def write(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text)


def test_steps_are_sorted_by_version(tmp_path: Path):
    write(tmp_path, "0010_later.py", STEP.format(structural=False, version=10))
    write(tmp_path, "0002_first.py", STEP.format(structural=True, version=2))
    write(tmp_path, "__init__.py", "")

    steps = discover(tmp_path)

    assert [(s.version, s.name, s.structural, s.label) for s in steps] == [
        (2, "first", True, "0002_first"),
        (10, "later", False, "0010_later"),
    ]
    assert steps[1].requests(Sheet()) == [{"step": 10}]
    assert latest_version(steps) == 10


def test_no_steps(tmp_path: Path):
    assert discover(tmp_path) == []
    assert discover(tmp_path / "missing") == []
    assert latest_version([]) == 1


def test_repository_ships_no_step():
    assert discover(STEPS) == []


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ({"2_short.py": STEP}, "<nnnn>_<name>.py"),
        ({"0002_Bad-Name.py": STEP}, "<nnnn>_<name>.py"),
        ({"0001_base.py": STEP}, "the first step has version 2"),
        ({"0002_a.py": STEP, "0002_b.py": STEP}, "version 2 is used by two steps"),
        ({"0002_a.py": "def requests(sheet):\n    return []\n"}, "defines STRUCTURAL"),
        ({"0002_a.py": "STRUCTURAL = 'yes'\ndef requests(sheet): ...\n"}, "defines STRUCTURAL"),
        ({"0002_a.py": "STRUCTURAL = True\n"}, "requests(sheet)"),
        ({"0002_a.py": "raise RuntimeError('boom')\n"}, "cannot load the step: boom"),
    ],
)
def test_invalid_step_files(tmp_path: Path, files: dict[str, str], message: str):
    for name, text in files.items():
        write(tmp_path, name, text.format(structural=True, version=2))

    with pytest.raises(Abort) as raised:
        discover(tmp_path)

    assert message in str(raised.value)
