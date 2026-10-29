"""Check the layout of the skill bundle."""

from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]


def test_only_the_skill_file_is_named_skill_md():
    named = [path for path in SKILL.rglob("*") if path.name.lower() == "skill.md"]
    assert named == [SKILL / "SKILL.md"]


def test_vendored_py_fsrs_ships_with_its_license():
    vendor = SKILL / "scripts" / "vendor" / "fsrs"
    assert "MIT License" in (vendor / "LICENSE").read_text()
    assert not (vendor / "optimizer.py").exists()


def test_schema_version_is_an_integer():
    assert int((SKILL / "SCHEMA_VERSION").read_text().strip()) >= 1
