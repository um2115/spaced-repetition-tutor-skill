# AGENTS.md

`CLAUDE.md` is a symlink to this file. Edit `AGENTS.md` only.

## Rules for editing this file

These rules stay in this file. Do not move them into an instruction file.

1. **Keep it current on every step.** In the same step as the change:
   - When the user states a rule, convention or preference about the project (for example "a
     function should be at most 40 lines long"), record it in the fitting instruction file. If no
     file fits, create one and link it here.
   - When an implementation changes anything described here or in an instruction file (commands,
     layout, tools, conventions), update the affected text.
2. **Progressive disclosure.** This file holds only what every step needs: project overview,
   layout, tools and commands, general conventions and the definition of done. Everything else
   lives in an instruction file at `./docs/instructions/<instruction-file>.md`.
3. **Link each instruction file at most once in this file**, as a list item that says when to read
   it: `- [Testing](docs/instructions/testing.md) — before writing or running tests`.
4. **Link instruction files only from this file.** Links between instruction files are allowed but
   discouraged. Every instruction file must be reachable from this file.
5. **Each fact lives in one place.** Do not repeat content between this file and instruction files,
   or between instruction files. Link instead.
6. **One topic per instruction file**, named in kebab-case (`code-style.md`, `testing.md`).
7. **No dead links, no orphans.** When an instruction file is deleted, delete its link. When a
   topic grows past one file's scope, split it.
8. **Keep this file under about 100 lines.** If it grows past that, move a section into an
   instruction file.
9. **Do not record what the code already says.** Write down rules and decisions, not what
   configuration, scripts or git history already show.

`mise run check:docs` checks rules 3, 4 and 7.

## Project

An agent skill that acts as a spaced repetition tutor. The agent picks due questions, asks them,
judges the answer and, on a wrong answer, explains the topic until the gap is closed. Newer or
harder questions come up more often than older or easier ones.

Questions and review state live in a Google Sheets document that the agent reads and writes
through an MCP server. The sheet is edited by hand or through migrations in `migrations/`, which
lets git be the single source of truth.

## Tools and commands

- [mise](https://mise.jdx.dev) installs the tools (see `mise.toml`) and runs all tasks.
- [uv](https://docs.astral.sh/uv/) manages the Python dependencies in `pyproject.toml`. Commit
  `uv.lock` with every dependency change; the tasks run with `--locked`.
- `mise run check:docs` — check the documentation rules above.
- `mise run check:data` — validate every YAML question file in `migrations/questions/`. Pass a
  directory to check another one.
- `mise run test` — run the pytest tests. No test touches the network; tests use the fake Sheets
  client in `migrations/runner/tests/fake_sheets.py`.
- `mise run migrate` — plan the migration of the Google Sheet; `--apply` creates missing tabs,
  runs pending steps and syncs the YAML questions. `mise run restore <snapshot>` plans writing a
  snapshot back; `--apply` writes it. Both read `SRT_SHEET_ID`, `SRT_OAUTH_CLIENT_SECRET` and
  `SRT_OAUTH_TOKEN` (or `--sheet-id`, `--client-secret`, `--token`). Set them in the gitignored
  `mise.local.toml`; never commit their values.

## Layout

- `migrations` - the migration scripts and data to create/update the google sheets
- `migrations/questions/` — the YAML question files.
- `migrations/steps/` — numbered migration steps `<nnnn>_<name>.py`, one per schema version.
- `migrations/schema/` — one module per sheet tab (its models and row mapping), the YAML
  question file loader, and `shared/` building blocks. Tests live in `migrations/schema/tests/`.
- `migrations/runner/` — the `migrate` and `restore` commands, with their `shared/` building
  blocks (settings and login, the Sheets client). Tests live in `migrations/runner/tests/`.
- `snapshots/` — local snapshots of the sheet taken before structural steps; ignored by git.
- `.agents/skills/spaced-repetition-tutor/` — the tutor skill that agents install from the
  repository; tests of its script live in `scripts/tests/`. `.claude/skills/` links to it for
  local use.
- `scripts/` — repository tooling.
- `docs/data-schema.md` — hand-written reference of the sheet tabs and YAML question files, for
  people and the tutor agent. It must stand alone: no relative links to other repository files.
- `docs/specs/<n>-<name>/task.md` — numbered specs. Work a spec defers to later goes into
  `docs/specs/todos.md`.

## Conventions

- [Code structure](docs/instructions/code-structure.md) — before adding or moving a module
- [Migration steps](docs/instructions/migration-steps.md) — before writing a migration step
- `README.md` is for people: what the project is, how to use it, how to start contributing. It
  links to `AGENTS.md` for everything else and does not link instruction files (rule 4).

## Definition of done

Before reporting a step as done, go through every item below yourself and run every command it
names. If an item fails, fix it and go through the list again. Do not hand unchecked items to the
user. If an item cannot be met, say which one and why instead of reporting the step as done.

- The requested change is implemented.
- `mise run test` and `mise run check:data` pass.
- A change to `migrations/schema/` updates `docs/data-schema.md` in the same step, and a change to
  `docs/data-schema.md` updates `migrations/schema/` to match.
- `AGENTS.md` and the affected instruction files reflect it (rule 1).
