#!/usr/bin/env python3
"""Check the AGENTS.md rules 3, 4 and 7 for instruction files.

Rule 3: each instruction file is linked at most once in AGENTS.md.
Rule 4: only AGENTS.md and instruction files link instruction files, and
        every instruction file is reachable from AGENTS.md.
Rule 7: no dead relative links in markdown files, no orphan instruction files.
"""

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
INSTRUCTIONS = ROOT / "docs" / "instructions"
SKIP_DIRS = {".git", "node_modules", ".venv"}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def markdown_files():
    for path in ROOT.rglob("*.md"):
        if path.is_symlink() or SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        yield path


def relative_links(path):
    """Yield resolved targets of relative links in a markdown file."""
    text = re.sub(r"```.*?```|`[^`\n]*`", "", path.read_text(), flags=re.S)
    for target in LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        target = target.split("#", 1)[0]
        yield (path.parent / target).resolve()


def is_instruction(path):
    return path.parent == INSTRUCTIONS and path.suffix == ".md"


def main():
    errors = []
    instruction_files = set(INSTRUCTIONS.glob("*.md")) if INSTRUCTIONS.is_dir() else set()
    links = {path: list(relative_links(path)) for path in markdown_files()}

    for path, targets in links.items():
        name = path.relative_to(ROOT)
        for target in targets:
            if not target.exists():
                errors.append(f"rule 7: {name} has dead link to {target.relative_to(ROOT)}")
            elif is_instruction(target) and path != AGENTS and not is_instruction(path):
                errors.append(f"rule 4: {name} links instruction file {target.name}")

    counts = Counter(t for t in links.get(AGENTS, []) if is_instruction(t))
    for target, count in counts.items():
        if count > 1:
            errors.append(f"rule 3: AGENTS.md links {target.name} {count} times")

    reachable, queue = set(), list(counts)
    while queue:
        current = queue.pop()
        if current in reachable or not current.exists():
            continue
        reachable.add(current)
        queue.extend(t for t in links.get(current, []) if is_instruction(t))
    for orphan in sorted(instruction_files - reachable):
        errors.append(f"rule 7: {orphan.name} is not reachable from AGENTS.md")

    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
