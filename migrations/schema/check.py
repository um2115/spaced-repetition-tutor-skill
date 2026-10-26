"""Validate every YAML question file: `python -m migrations.schema.check [directory]`.

The directory defaults to `migrations/` next to this package. Prints every error and exits
non-zero when there are any.
"""

import sys
from pathlib import Path

from .questions_file import load_directory

MIGRATIONS = Path(__file__).resolve().parent.parent


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else MIGRATIONS
    questions, errors = load_directory(root)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"{len(errors)} error(s) in question files", file=sys.stderr)
        return 1
    print(f"{len(questions)} question(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
