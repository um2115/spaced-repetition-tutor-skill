# 5-add-build-task

Add a `build` task that creates a new version of the `spaced-repetition-tutor` skill in place,
bundling the data schema, the current schema version and the vendored py-fsrs, and a
`check:skill` task that fails when the bundled files drift from their sources.

Related: `4-create-tutor-skill` creates the skill and the first manual copies this task takes
over.

## Problem

The skill at `.agents/skills/spaced-repetition-tutor/` carries copies of things that live
elsewhere in the repository: `references/data-schema.md` copies `docs/data-schema.md`,
`SCHEMA_VERSION` repeats the latest migration step's version, and `scripts/vendor/fsrs/` holds
py-fsrs, whose version is pinned in `uv.lock`. Spec 4 places them once by hand. After that,
nothing updates them and nothing notices when they differ from their sources, so the skill
installed from the GitHub link can silently describe an outdated schema, check against the wrong
schema version or schedule with another FSRS version. The skill also has no version number.

## Goal

`mise run build <version>` updates the skill in place at `.agents/skills/spaced-repetition-tutor/`
from its sources and writes the given semantic version to its `VERSION` file. The result is
committed, so installing the skill from the GitHub link gets the current state. `mise run
check:skill`, also run by `mise run test`, fails whenever a bundled file differs from its source.

## Scope

### In scope

- The build script `scripts/build_skill.py` and a `build` mise task that runs it with uv and
  `--locked`.
- The drift check and a `check:skill` mise task, plus a test that runs the same check in
  `mise run test`.
- Tests in `scripts/tests/`, added to `testpaths`.
- The file `.agents/skills/spaced-repetition-tutor/VERSION`.
- `AGENTS.md`: the `build` and `check:skill` commands, and a definition-of-done item saying that a
  change to `docs/data-schema.md`, `migrations/steps/` or the py-fsrs pin runs `mise run build`
  and that `mise run check:skill` passes.
- Removing the `build` task item from `docs/specs/todos.md`.

### Out of scope (non-goals)

- A changelog, git tags, GitHub releases or a zip file.
- Changing the schema document on the way: it is copied verbatim, not shortened or generated
  from the models in `migrations/schema/`.
- Choosing or bumping the version automatically: the user passes it.
- Excluding tests, `__pycache__` or other files from the skill directory: the build works in
  place and the directory is installed as it is.
- Writing `SKILL.md`, the FSRS script or its tests; these belong to `4-create-tutor-skill`.
- Installing the skill into any agent.

## Behavior

### Build

1. `mise run build <version>` takes one argument, the new version. A missing argument or one that
   is not a valid semantic version (`MAJOR.MINOR.PATCH`, as defined by semver.org) is an error.
2. If `VERSION` exists and the new version is lower than the version in it, the build fails. An
   equal version is allowed, for rebuilding after a source changed.
3. Before writing anything, the build checks every source: `docs/data-schema.md` exists, py-fsrs is
   installed in the uv environment at the version locked in `uv.lock`, its MIT license file is
   available, and the stdlib patch (step 6) applies to every module that imports
   `typing_extensions`. If anything fails, the build prints every error and writes nothing.
4. It copies `docs/data-schema.md` verbatim to `references/data-schema.md` in the skill.
5. It writes the version of the latest step in `migrations/steps/` to `SCHEMA_VERSION`, or `1` when
   there are no steps.
6. It replaces the contents of `scripts/vendor/fsrs/` with the py-fsrs modules except
   `optimizer.py`, which needs torch, and the py-fsrs MIT license file. It patches the copied
   modules so they import with the standard library only: the import of `Self` from
   `typing_extensions` moves under `if TYPE_CHECKING:`, adding `from typing import
   TYPE_CHECKING` where a module lacks it. This is the change `scripts/vendor/README.md`
   describes, and it works because the modules use `from __future__ import annotations`. A
   module that imports `typing_extensions` in any other way, or any other third-party package, is
   an error found in step 3.
7. It writes the new version to `VERSION`.
8. It prints what it changed. A second run with the same version and unchanged sources changes no
   file.

### Check

9. `mise run check:skill` fails, naming each problem, when:
   - `references/data-schema.md` is not byte for byte equal to `docs/data-schema.md`;
   - `SCHEMA_VERSION` does not hold the latest step version (or `1` without steps);
   - the vendored py-fsrs differs from the locked version's modules with the patch of step 6
     applied, or its license file is missing;
   - `VERSION` is missing or not a valid semantic version.
10. Otherwise it exits zero. `mise run test` runs the same check as a test.

## Constraints & assumptions

- Python 3.14 and uv, as in `mise.toml`; the task runs with `--locked`.
- py-fsrs 6.3.2 is a dev dependency pinned in `uv.lock`, added by `4-create-tutor-skill`, and its
  installed package contains its MIT license file.
- In py-fsrs 6.3.2, `card.py`, `review_log.py` and `scheduler.py` import `Self` from
  `typing_extensions` for annotations only; no other module needs a third-party package except
  `optimizer.py`.
- `4-create-tutor-skill` is done: the skill directory, `references/data-schema.md`,
  `SCHEMA_VERSION` and `scripts/vendor/fsrs/` exist.
- The latest schema version is the highest step version in `migrations/steps/`, as the migration
  script determines it.
- No test touches the network.

## Acceptance criteria

- [x] `mise run build` without an argument, with an invalid version, or with a version lower than
      `VERSION` fails and writes nothing.
- [x] `mise run build` with the same version as `VERSION` succeeds.
- [x] A missing source makes the build print every error and write nothing.
- [x] After a build, `references/data-schema.md` equals `docs/data-schema.md` byte for byte,
      `SCHEMA_VERSION` holds the latest step version, `scripts/vendor/fsrs/` holds the locked
      py-fsrs scheduler modules and its license, and `VERSION` holds the given version.
- [x] The vendored py-fsrs imports without torch or any other third-party package, checked by
      importing it with `python -I -S`, and equals the locked py-fsrs with only the patch of
      step 6 applied.
- [x] A py-fsrs module whose third-party imports the patch does not cover makes the build fail
      and write nothing.
- [x] A second build with the same version and unchanged sources leaves `git status` clean.
- [x] Each drift case in *Check* makes `mise run check:skill` fail with a message naming it, and
      `mise run test` fails with it.
- [x] `AGENTS.md` names the `build` and `check:skill` tasks and has the new definition-of-done
      item; the `build` item is gone from `docs/specs/todos.md`.
- [x] `mise run test`, `mise run check:data`, `mise run check:docs` and `mise run check:skill`
      pass.
