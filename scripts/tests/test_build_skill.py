import subprocess
import sys
from pathlib import Path

import pytest

from scripts.build_skill import (
    BuildError,
    Fsrs,
    Layout,
    build,
    check,
    installed_fsrs,
    main,
    patch_module,
    semver_key,
    third_party_imports,
)

LOCK = '[[package]]\nname = "fsrs"\nversion = "6.3.2"\n'
STEP = "STRUCTURAL = False\n\n\ndef requests(sheet):\n    return []\n"


@pytest.fixture
def layout(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "data-schema.md").write_text("# Data schema\n")
    (tmp_path / "migrations" / "steps").mkdir(parents=True)
    (tmp_path / "uv.lock").write_text(LOCK)
    (tmp_path / ".agents" / "skills" / "spaced-repetition-tutor").mkdir(parents=True)
    return Layout(tmp_path)


def snapshot(root: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_build_writes_every_bundled_file(layout):
    build("1.0.0", layout)

    skill = layout.skill
    assert (skill / "references" / "data-schema.md").read_text() == "# Data schema\n"
    assert (skill / "SCHEMA_VERSION").read_text() == "1\n"
    assert (skill / "VERSION").read_text() == "1.0.0\n"
    vendored = sorted(path.name for path in layout.vendor.iterdir())
    assert vendored == [
        "LICENSE", "__init__.py", "card.py", "rating.py", "review_log.py", "scheduler.py",
        "state.py",
    ]  # fmt: skip
    assert "MIT License" in (layout.vendor / "LICENSE").read_text()
    assert check(layout) == []


def test_schema_version_is_the_latest_step(layout):
    (layout.steps / "0002_add_hints.py").write_text(STEP)
    (layout.steps / "0003_add_notes.py").write_text(STEP)
    build("1.0.0", layout)
    assert (layout.skill / "SCHEMA_VERSION").read_text() == "3\n"


def test_vendored_py_fsrs_imports_with_the_standard_library_only(layout):
    build("1.0.0", layout)
    code = f"import sys; sys.path.insert(0, {str(layout.vendor.parent)!r}); import fsrs; fsrs.Scheduler()"
    result = subprocess.run([sys.executable, "-I", "-S", "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_vendored_py_fsrs_is_the_locked_one_with_only_the_patch(layout):
    build("1.0.0", layout)
    package = installed_fsrs().package
    for path in layout.vendor.glob("*.py"):
        original = (package / path.name).read_text()
        assert path.read_text() == patch_module(original)
        removed = set(original.splitlines()) - set(path.read_text().splitlines())
        assert removed <= {"from typing_extensions import Self"}


def test_second_build_changes_nothing(layout):
    build("1.0.0", layout)
    before = snapshot(layout.root)
    assert build("1.0.0", layout) == []
    assert snapshot(layout.root) == before


def test_build_replaces_stale_vendored_files(layout):
    build("1.0.0", layout)
    (layout.vendor / "old.py").write_text("")
    (layout.vendor / "card.py").write_text("# edited\n")
    changes = build("1.0.1", layout)
    assert not (layout.vendor / "old.py").exists()
    assert any(change.endswith("card.py") for change in changes)
    assert check(layout) == []


@pytest.mark.parametrize("version", ["1.0", "v1.0.0", "1.0.0.0", "01.0.0", ""])
def test_invalid_version_writes_nothing(layout, version):
    before = snapshot(layout.root)
    with pytest.raises(BuildError, match="not a semantic version"):
        build(version, layout)
    assert snapshot(layout.root) == before


def test_lower_version_writes_nothing_and_equal_version_builds(layout):
    build("1.2.0", layout)
    layout.schema_doc.write_text("# Changed\n")
    before = snapshot(layout.root)
    with pytest.raises(BuildError, match="lower than the current version 1.2.0"):
        build("1.1.9", layout)
    assert snapshot(layout.root) == before

    build("1.2.0", layout)
    assert (layout.skill / "references" / "data-schema.md").read_text() == "# Changed\n"


def test_missing_sources_are_all_reported_and_nothing_is_written(layout):
    layout.schema_doc.unlink()
    layout.lock.write_text("")
    before = snapshot(layout.root)
    with pytest.raises(BuildError) as raised:
        build("1.0.0", layout)
    assert raised.value.errors[0] == "docs/data-schema.md is missing"
    assert "uv.lock locks no py-fsrs" in raised.value.errors[1]
    assert snapshot(layout.root) == before


def test_wrong_installed_version_or_missing_license_fails(layout):
    fsrs = installed_fsrs()
    with pytest.raises(BuildError, match="6.3.1 is installed, but uv.lock locks 6.3.2"):
        build("1.0.0", layout, Fsrs(fsrs.package, fsrs.license, "6.3.1"))
    with pytest.raises(BuildError, match="no LICENSE file"):
        build("1.0.0", layout, Fsrs(fsrs.package, None, fsrs.version))
    assert not layout.vendor.exists()


def test_module_the_patch_does_not_cover_writes_nothing(layout, tmp_path):
    package = tmp_path / "site" / "fsrs"
    package.mkdir(parents=True)
    (package / "card.py").write_text("import typing_extensions\nimport requests\n")
    (package / "LICENSE").write_text("MIT License\n")
    before = snapshot(layout.root)
    with pytest.raises(BuildError, match="card.py: imports requests, typing_extensions"):
        build("1.0.0", layout, Fsrs(package, package / "LICENSE", "6.3.2"))
    assert snapshot(layout.root) == before


@pytest.mark.parametrize(
    ("source", "patched"),
    [
        (
            "from typing import TypedDict\n\nfrom typing_extensions import Self\n\nx = 1\n",
            "from typing import TypedDict\n\nfrom typing import TYPE_CHECKING\n\n"
            "if TYPE_CHECKING:\n    from typing_extensions import Self\n\nx = 1\n",
        ),
        (
            "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from torch import Tensor\n"
            "from typing_extensions import Self\n",
            "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from torch import Tensor\n"
            "    from typing_extensions import Self\n",
        ),
        (
            "from typing import TYPE_CHECKING\nfrom typing_extensions import Self\n",
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
            "    from typing_extensions import Self\n",
        ),
        ("import json\n", "import json\n"),
    ],
)
def test_patch_module(source, patched):
    assert patch_module(source) == patched
    assert third_party_imports(patched) == []


def test_third_party_imports_ignore_type_checking_blocks():
    source = "import json\nimport yaml\nif TYPE_CHECKING:\n    import torch\nelse:\n    import numpy\n"
    assert third_party_imports(source) == ["yaml", "numpy"]


@pytest.mark.parametrize(
    ("damage", "message"),
    [
        (lambda layout: layout.schema_doc.write_text("# New\n"),
         "references/data-schema.md differs from docs/data-schema.md"),
        (lambda layout: (layout.skill / "references" / "data-schema.md").unlink(),
         "references/data-schema.md is missing"),
        (lambda layout: (layout.steps / "0002_add_hints.py").write_text(STEP),
         "SCHEMA_VERSION differs from the latest schema version"),
        (lambda layout: (layout.vendor / "scheduler.py").write_text("# edited\n"),
         "vendor/fsrs/scheduler.py differs from the locked py-fsrs"),
        (lambda layout: (layout.vendor / "optimizer.py").write_text(""),
         "vendor/fsrs/optimizer.py is not part of the locked py-fsrs"),
        (lambda layout: (layout.vendor / "LICENSE").unlink(), "vendor/fsrs/LICENSE is missing"),
        (lambda layout: layout.version.unlink(), "VERSION is missing"),
        (lambda layout: layout.version.write_text("one\n"), "VERSION is not a semantic version"),
    ],
)  # fmt: skip
def test_check_names_each_drift(layout, damage, message):
    build("1.0.0", layout)
    damage(layout)
    problems = check(layout)
    assert any(message in problem for problem in problems), problems
    assert problems[-1] == "run `mise run build <version>` to update the skill"


def test_semver_precedence():
    ordered = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-beta", "1.0.0-beta.2", "1.0.0-rc.1",
               "1.0.0", "1.0.1", "1.1.0", "2.0.0"]  # fmt: skip
    assert sorted(ordered, key=semver_key) == ordered
    assert semver_key("1.0.0+build.5") == semver_key("1.0.0")


def test_build_requires_a_version():
    with pytest.raises(SystemExit) as raised:
        main(["build"])
    assert raised.value.code == 2


def test_the_skill_in_this_repository_is_built():
    assert check() == []
