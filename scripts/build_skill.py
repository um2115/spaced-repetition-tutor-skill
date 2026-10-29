"""Build the spaced-repetition-tutor skill in place, and check that it is built.

    python -m scripts.build_skill build <version>
    python -m scripts.build_skill check

The skill bundles copies of files that live elsewhere: `docs/data-schema.md`, the latest schema
version of `migrations/steps/`, and py-fsrs at the version locked in `uv.lock`. `build` writes
them and the given semantic version into the skill; `check` fails when one differs from its
source.

py-fsrs is vendored with the standard library only: its modules import `Self` from
`typing_extensions` for annotations only, so the build moves that import under
`if TYPE_CHECKING:`. The modules use `from __future__ import annotations`, so the name is never
needed at run time. Any other third-party import that runs is an error.
"""

import argparse
import ast
import importlib.metadata
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from migrations.runner.shared.errors import Abort
from migrations.runner.steps import discover, latest_version

ROOT = Path(__file__).resolve().parent.parent
SKILL = Path(".agents/skills/spaced-repetition-tutor")
# semver.org's regular expression for a semantic version.
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
SKIPPED_MODULES = {"optimizer.py"}  # needs torch
ALLOWED_IMPORTS = set(sys.stdlib_module_names) | {"__future__", "fsrs"}
SELF_IMPORT = "    from typing_extensions import Self\n"


class BuildError(Exception):
    """Sources that cannot be built; holds every problem found."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


@dataclass(frozen=True)
class Layout:
    """Where the build reads and writes, relative to a repository root."""

    root: Path = ROOT

    @property
    def skill(self) -> Path:
        return self.root / SKILL

    @property
    def schema_doc(self) -> Path:
        return self.root / "docs" / "data-schema.md"

    @property
    def steps(self) -> Path:
        return self.root / "migrations" / "steps"

    @property
    def lock(self) -> Path:
        return self.root / "uv.lock"

    @property
    def vendor(self) -> Path:
        return self.skill / "scripts" / "vendor" / "fsrs"

    @property
    def version(self) -> Path:
        return self.skill / "VERSION"


@dataclass(frozen=True)
class Fsrs:
    """The installed py-fsrs package: its module directory, license file and version."""

    package: Path | None
    license: Path | None
    version: str | None


def installed_fsrs() -> Fsrs:
    try:
        dist = importlib.metadata.distribution("fsrs")
    except importlib.metadata.PackageNotFoundError:
        return Fsrs(None, None, None)
    files = dist.files or []
    licenses = [file for file in files if file.name == "LICENSE" and "licenses" in file.parts]
    license = Path(dist.locate_file(licenses[0])) if licenses else None
    return Fsrs(Path(dist.locate_file("fsrs")), license, dist.version)


def locked_version(lock: Path, name: str) -> str | None:
    if not lock.is_file():
        return None
    packages = tomllib.loads(lock.read_text()).get("package", [])
    return next((package["version"] for package in packages if package["name"] == name), None)


# --- Semantic versions -------------------------------------------------------------------------


def semver_key(version: str) -> tuple:
    """A key that orders versions by semver precedence; build metadata does not count."""
    match = SEMVER.match(version)
    if not match:
        raise ValueError(f"not a semantic version: {version!r}")
    core = tuple(int(part) for part in match.groups()[:3])
    if match[4] is None:
        return (*core, 1, ())
    pre = tuple((0, int(part), "") if part.isdigit() else (1, 0, part) for part in match[4].split("."))
    return (*core, 0, pre)


# --- Patching py-fsrs --------------------------------------------------------------------------


def _is_type_checking(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Name)
        and node.test.id == "TYPE_CHECKING"
    )


def third_party_imports(source: str) -> list[str]:
    """The modules imported at run time that are neither stdlib nor py-fsrs itself."""
    found = []

    def visit(node: ast.AST) -> None:
        if _is_type_checking(node):
            for child in node.orelse:
                visit(child)
            return
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append(node.module)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(ast.parse(source))
    return [name for name in found if name.split(".")[0] not in ALLOWED_IMPORTS]


def patch_module(source: str) -> str:
    """Move a top-level `from typing_extensions import Self` under `if TYPE_CHECKING:`."""
    tree = ast.parse(source)
    imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "typing_extensions"
        and [(alias.name, alias.asname) for alias in node.names] == [("Self", None)]
    ]
    if not imports:
        return source
    line = imports[0].lineno
    lines = source.splitlines(keepends=True)
    block = next((node for node in tree.body if _is_type_checking(node)), None)
    if block is not None:
        patched = []
        for number, text in enumerate(lines, start=1):
            if number != line:
                patched.append(text)
            if number == block.body[-1].end_lineno:
                patched.append(SELF_IMPORT)
        return "".join(patched)
    has_flag = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "typing"
        and any(alias.name == "TYPE_CHECKING" for alias in node.names)
        for node in tree.body
    )
    replacement = ("" if has_flag else "from typing import TYPE_CHECKING\n\n") + (
        "if TYPE_CHECKING:\n" + SELF_IMPORT
    )
    return "".join(lines[: line - 1]) + replacement + "".join(lines[line:])


def vendored_files(fsrs: Fsrs) -> dict[str, bytes]:
    """The files of `scripts/vendor/fsrs/` by name, built from the installed py-fsrs."""
    files, errors = {}, []
    for path in sorted(fsrs.package.glob("*.py")):
        if path.name in SKIPPED_MODULES:
            continue
        source = patch_module(path.read_text())
        imports = third_party_imports(source)
        if imports:
            errors.append(
                f"py-fsrs {path.name}: imports {', '.join(sorted(set(imports)))} at run time, "
                "which the stdlib patch does not cover"
            )
        files[path.name] = source.encode()
    if errors:
        raise BuildError(errors)
    files["LICENSE"] = fsrs.license.read_bytes()
    return files


# --- Build and check ---------------------------------------------------------------------------


def _schema_version(layout: Layout) -> int:
    try:
        return latest_version(discover(layout.steps))
    except Abort as error:
        raise BuildError([str(error)]) from None


def expected_files(layout: Layout, fsrs: Fsrs) -> dict[Path, bytes]:
    """Every file the build writes, except VERSION, with its content. Raises BuildError."""
    errors = []
    if not layout.schema_doc.is_file():
        errors.append(f"{layout.schema_doc.relative_to(layout.root)} is missing")
    locked = locked_version(layout.lock, "fsrs")
    if locked is None:
        errors.append("uv.lock locks no py-fsrs (package fsrs)")
    if fsrs.package is None:
        errors.append("py-fsrs is not installed; run `uv sync --locked`")
    elif fsrs.version != locked:
        errors.append(f"py-fsrs {fsrs.version} is installed, but uv.lock locks {locked}")
    elif fsrs.license is None or not fsrs.license.is_file():
        errors.append("the installed py-fsrs has no LICENSE file")
    try:
        schema_version = _schema_version(layout)
    except BuildError as error:
        errors.extend(error.errors)
    if not errors:
        try:
            vendored = vendored_files(fsrs)
        except BuildError as error:
            errors.extend(error.errors)
    if errors:
        raise BuildError(errors)
    files = {
        layout.skill / "references" / "data-schema.md": layout.schema_doc.read_bytes(),
        layout.skill / "SCHEMA_VERSION": f"{schema_version}\n".encode(),
    }
    files.update({layout.vendor / name: content for name, content in vendored.items()})
    return files


def _vendor_files_on_disk(layout: Layout) -> list[Path]:
    if not layout.vendor.is_dir():
        return []
    return [
        path
        for path in layout.vendor.rglob("*")
        if path.is_file() and "__pycache__" not in path.relative_to(layout.vendor).parts
    ]


def build(version: str, layout: Layout = Layout(), fsrs: Fsrs | None = None) -> list[str]:
    """Write the skill's bundled files and VERSION; return what changed. Raises BuildError."""
    errors = []
    try:
        new_key = semver_key(version)
    except ValueError as error:
        errors.append(str(error))
    if not errors and layout.version.is_file():
        current = layout.version.read_text().strip()
        try:
            if new_key < semver_key(current):
                errors.append(f"version {version} is lower than the current version {current}")
        except ValueError:
            errors.append(f"VERSION holds {current!r}, which is not a semantic version")
    try:
        files = expected_files(layout, fsrs or installed_fsrs())
    except BuildError as error:
        errors.extend(error.errors)
    if errors:
        raise BuildError(errors)

    files[layout.version] = f"{version}\n".encode()
    changes = []
    for path in _vendor_files_on_disk(layout):
        if path not in files:
            path.unlink()
            changes.append(f"removed {path.relative_to(layout.root)}")
    for path, content in files.items():
        if path.is_file() and path.read_bytes() == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        changes.append(f"wrote {path.relative_to(layout.root)}")
    return changes


def check(layout: Layout = Layout(), fsrs: Fsrs | None = None) -> list[str]:
    """Every way the built skill differs from its sources; empty when it is up to date."""
    try:
        files = expected_files(layout, fsrs or installed_fsrs())
    except BuildError as error:
        return error.errors
    problems = []
    for path, content in files.items():
        name = path.relative_to(layout.root)
        if not path.is_file():
            problems.append(f"{name} is missing")
        elif path.read_bytes() != content:
            source = {
                "data-schema.md": "docs/data-schema.md",
                "SCHEMA_VERSION": "the latest schema version of migrations/steps/",
            }.get(path.name, "the locked py-fsrs with the stdlib patch")
            problems.append(f"{name} differs from {source}")
    for path in _vendor_files_on_disk(layout):
        if path not in files:
            problems.append(f"{path.relative_to(layout.root)} is not part of the locked py-fsrs")
    if not layout.version.is_file():
        problems.append(f"{layout.version.relative_to(layout.root)} is missing")
    elif not SEMVER.match(layout.version.read_text().strip()):
        problems.append(f"{layout.version.relative_to(layout.root)} is not a semantic version")
    if problems:
        problems.append("run `mise run build <version>` to update the skill")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or check the spaced-repetition-tutor skill.")
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build", help="update the skill and set its version")
    build_parser.add_argument("version", help="the new semantic version, such as 1.2.0")
    commands.add_parser("check", help="fail when the skill differs from its sources")
    args = parser.parse_args(argv)

    if args.command == "check":
        problems = check()
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        if not problems:
            print("the skill is up to date")
        return 1 if problems else 0
    try:
        changes = build(args.version)
    except BuildError as error:
        for message in error.errors:
            print(f"error: {message}", file=sys.stderr)
        print("nothing written", file=sys.stderr)
        return 1
    for change in changes:
        print(change)
    print(f"built version {args.version}" + ("" if changes else ", nothing changed"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
