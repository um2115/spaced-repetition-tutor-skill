# 2-document-data-schema

Write `docs/data-schema.md`, the reference for the tutor's Google Sheets tabs and YAML question
files, and make keeping it in step with the schema code a gate for agents.

Related: `1-define-data-schema` defines the schema this document describes.

## Context

The README says each entry must follow a schema "defined in <TODO>". People who edit the sheet by
hand, people who write migration YAML, and the tutor agent have no place to learn which tabs and
columns exist, which ones are required, and who may write what.

## Audience & outcome

- **Hand-editor:** a person who edits the Google Sheet directly. They know spreadsheets but not
  the code. Afterwards they can add or retire a question by hand without breaking the agent, and
  they know which tabs to leave alone.
- **Migration author:** a person who writes YAML question files in `migrations/`. They know YAML
  and git. Afterwards they can write a valid topic file and check it with `mise run check:data`.
- **Tutor agent:** it reads and writes the sheet through an MCP server. Afterwards it knows each
  tab's columns, formats and write rules: append-only `log`, a `state` row created on first
  review, and a read-only `questions` tab.

## Scope

### In scope

- A new hand-written page, `docs/data-schema.md`.
- In `README.md`, replace the schema `<TODO>` with a link to `docs/data-schema.md`.
- **Gate:** add an item to the Definition of done in `AGENTS.md` that says a change to
  `migrations/schema/` must update `docs/data-schema.md` in the same step, and the reverse.

### Out of scope (non-goals)

- The `build` task that bundles `docs/data-schema.md` into the skill. It is a later spec.
- Generating the document from the Python models. It is written by hand.
- Setup and usage sections of the README (the other `<TODO>`s).
- Documenting the migration script, which does not exist yet.
- Explaining FSRS itself beyond what each column means.

## Sources of truth

- Tabs, columns, types, required fields, defaults and formats come from the models in
  `migrations/schema/` (spec `1-define-data-schema`).
- Who writes which tab (migrations or hand for `questions`, agent only for `state` and `log`)
  comes from spec `1-define-data-schema`, Behavior.
- The YAML file layout and validation errors come from the `migrations/schema/` loader and
  `mise run check:data`.
- The FSRS rating meanings (1 Again, 2 Hard, 3 Good, 4 Easy) come from the FSRS / py-fsrs
  documentation.

## Deliverable & outline

- `docs/data-schema.md` (new)
  1. Overview: the four tabs and who writes which
  2. Tab: `questions` (columns, types, required, rules)
  3. Tab: `state` (FSRS columns, values)
  4. Tab: `log` (columns, append-only rule)
  5. Tab: `config` (keys, defaults)
  6. Formats (timestamps, tags and other lists, booleans, id slug)
  7. YAML question files (layout and example)
  8. Editing by hand: do's and don'ts
- `README.md` (changed): the "Managing data manually by hand" section links to the page.
- `AGENTS.md` (changed): the new Definition of done item.

## Constraints & assumptions

- Depends on `1-define-data-schema` being implemented. The document describes the code, not the
  spec.
- `docs/data-schema.md` is not an instruction file, so README may link it without breaking rule 4
  of `AGENTS.md`.
- The page has to work on its own once a later build task copies it into the skill bundle. It
  must not depend on relative links to repository files outside the page.
- `AGENTS.md` stays under about 100 lines.

## Acceptance criteria

- [x] Every tab, column and config key in `migrations/schema/` appears in `docs/data-schema.md`
      with the same name, type, required flag and default, and the page names no column the code
      lacks.
- [x] The YAML example on the page, saved as a file in `migrations/`, passes
      `mise run check:data`.
- [x] A hand-editor who knows only spreadsheets can add a valid question row and retire one using
      this page alone.
- [x] `README.md` links to `docs/data-schema.md`, and no schema `<TODO>` remains.
- [x] `AGENTS.md` has the Definition of done item that ties `migrations/schema/` and
      `docs/data-schema.md` together.
- [x] `mise run check:docs` passes.
- [x] No unresolved placeholders or TODOs on the page.
