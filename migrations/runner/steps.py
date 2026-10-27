"""Find and load the numbered migration steps in `migrations/steps/`.

A step is a file `<nnnn>_<name>.py`, where `<nnnn>` is the schema version the step brings the
sheet to. Version 1 is the schema a new sheet starts with, so the first step is `0002_<name>.py`.
A step module defines:

- `STRUCTURAL: bool`: true when the step changes tabs, columns or the format of cells, so a
  snapshot is taken first and hand-added questions may break; false when it only changes data.
- `requests(sheet: Sheet) -> list[Request]`: the `spreadsheets.batchUpdate` requests that apply
  the step to `sheet`, the cell values as read before the step. The request builders in
  `migrations/runner/shared/sheets.py` help to write them.

The runner adds the requests that set `config.schema_version` and log the step in the
`migrations` tab, and sends everything as one atomic `batchUpdate`.
"""

import importlib.util
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .shared.errors import Abort
from .shared.sheets import Request, Sheet

STEPS = Path(__file__).resolve().parent.parent / "steps"
BASE_VERSION = 1
FILE_NAME = re.compile(r"^(\d{4})_([a-z0-9]+(?:_[a-z0-9]+)*)\.py$")


@dataclass(frozen=True)
class Step:
    version: int
    name: str
    structural: bool
    requests: Callable[[Sheet], list[Request]]

    @property
    def label(self) -> str:
        return f"{self.version:04d}_{self.name}"


def discover(directory: Path = STEPS) -> list[Step]:
    """Load every step in `directory`, sorted by version."""
    steps: dict[int, Step] = {}
    for path in sorted(directory.glob("*.py")) if directory.is_dir() else []:
        if path.name == "__init__.py":
            continue
        step = _load(path)
        if step.version in steps:
            raise Abort(f"{path}: version {step.version} is used by two steps")
        steps[step.version] = step
    return [steps[version] for version in sorted(steps)]


def latest_version(steps: list[Step]) -> int:
    return max((step.version for step in steps), default=BASE_VERSION)


def _load(path: Path) -> Step:
    match = FILE_NAME.match(path.name)
    if not match:
        raise Abort(f"{path}: a step file is named <nnnn>_<name>.py, such as 0002_add_hints.py")
    version, name = int(match[1]), match[2]
    if version <= BASE_VERSION:
        raise Abort(f"{path}: the first step has version {BASE_VERSION + 1}")
    spec = importlib.util.spec_from_file_location(f"migrations.steps.{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise Abort(f"{path}: cannot load the step: {error}") from error
    structural, requests = getattr(module, "STRUCTURAL", None), getattr(module, "requests", None)
    if not isinstance(structural, bool) or not callable(requests):
        raise Abort(f"{path}: a step defines STRUCTURAL (True or False) and requests(sheet)")
    return Step(version, name, structural, requests)
