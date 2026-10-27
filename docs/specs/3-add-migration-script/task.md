# 3-add-migration-script

Add a migration script that brings the Google Sheet to the latest schema version and writes the
questions from the YAML files in `migrations/` into it, plus a restore command for the snapshots
it takes before structural changes.

Related: `1-define-data-schema` defines the models this script uses, `2-document-data-schema`
documents them.

## Problem

Questions can be written as YAML in `migrations/` and checked with `mise run check:data`, but
nothing writes them into the Google Sheet. Git therefore cannot be the single source of truth the
README promises: every question has to be copied into the sheet by hand. `config.schema_version`
exists, but there is no way to apply a schema change to an existing sheet, and no way to set up a
new, empty sheet with the right tabs and headers.

## Goal

`mise run migrate` shows by default what it would change and, with `--apply`, creates any missing
tabs, runs the pending numbered migration steps in order and syncs the YAML questions into the
`questions` tab. It reports every question it overwrote and every row it left alone. Before a
structural step it saves a local snapshot of the whole sheet, and `mise run restore` writes such a
snapshot back.

## Scope

### In scope

- The migration script and a `migrate` mise task.
- The restore command and a `restore` mise task.
- OAuth user login to the Google Sheets API with `google-api-python-client` and
  `google-auth-oauthlib`.
- Numbered migration steps in `migrations/steps/<nnnn>_<name>.py` and the code that finds and runs
  them. No step ships with this spec.
- Moving the YAML question files to `migrations/questions/`; `check:data` reads only that
  directory.
- Two new tabs in schema version 1, `migrations` and `managed_questions`: their models and row
  mapping in `migrations/schema/`, and their description in `docs/data-schema.md`.
- Local snapshots of the sheet before structural steps.
- Pytest tests against a fake Sheets client.

### Out of scope (non-goals)

- Deleting or retiring questions that were removed from YAML. They stay as they are and are
  reported.
- Changing or validating hand-added (unmanaged) question rows during a question sync.
- Writing `state` or `log` rows outside a numbered step.
- Any concrete migration step. There is no live sheet yet, so the new tabs join schema version 1
  and the latest version stays `1`.
- Taking snapshots before data-only runs, or in Drive.
- The README section "Managing data via migration". It goes to `docs/specs/todos.md`.
- The `build` task that bundles the skill.
- Migrating more than one sheet per run.
- Network access in the tests.

## Behavior

### Settings and login

1. The script reads the sheet id, the path of the OAuth client secret file and the path of the
   token cache from the environment variables `SRT_SHEET_ID`, `SRT_OAUTH_CLIENT_SECRET` and
   `SRT_OAUTH_TOKEN`. The command line flags `--sheet-id`, `--client-secret` and `--token`
   override them.
2. A missing setting is an error that names the variable and the flag, before any network access.
3. Without a cached token the script opens the browser for the Google login and stores the token
   at the token path. Later runs reuse and refresh it.

### Migrate

4. The script first validates every YAML question file in `migrations/questions/`, the same way
   `check:data` does. On errors it prints them and exits non-zero without touching the network.
5. It reads the sheet. Tabs that do not exist are planned for creation with their header row; a
   new `config` tab gets `schema_version` set to the latest step version. An existing tab whose
   header row differs from the schema aborts the run with an error naming the tab.
6. If `config.schema_version` is higher than the latest step in the repository, the script aborts,
   writes nothing and tells the user to update the repository.
7. Steps whose version is higher than `config.schema_version` are pending. Each step declares
   whether it is structural or data-only. A step may change any tab, including `state` and `log`.
8. If a structural step is pending and the `questions` tab holds rows whose id is not in
   `managed_questions` (unmanaged rows), the script lists their ids, warns that they may break
   because their format may not fit the change, and asks y/N. No aborts the run without writing.
   When standard input is not interactive, it aborts.
9. Before the first structural step of an `--apply` run, the script saves a snapshot (see below)
   and prints its path. If the snapshot cannot be written, it aborts without writing to the sheet.
10. Pending steps run in version order. Each step is one atomic `spreadsheets.batchUpdate` that
    also sets `config.schema_version` to the step's version and appends a row to the `migrations`
    tab. If a step fails, the steps before it stay applied, the error names the failed step, and
    the next run resumes from it.
11. Then the script syncs the questions, in one `batchUpdate`:
    - A YAML question whose id is not in the sheet is appended to `questions`, and its id and
      source file are appended to `managed_questions`.
    - A managed question whose sheet row differs from YAML is overwritten with the YAML values.
      The report lists the id and each changed field.
    - A managed question that is no longer in any YAML file is left untouched and reported.
    - Unmanaged rows are left untouched, are not validated, and are reported.
    - A YAML question whose id matches an unmanaged row takes that row over: the row gets the YAML
      values, the id is added to `managed_questions`, and the takeover is reported.
    - A managed row in `questions` that does not match its model aborts the run with an error
      naming the tab, row and column.
12. Without `--apply` the script only prints the plan (tabs to create, pending steps, whether a
    snapshot would be taken, and the sync changes and reports above) and exits zero without
    writing. With `--apply` it writes and prints the same report of what it did.
13. A second `--apply` run without YAML or step changes plans no changes.

### Snapshots

14. A snapshot is a directory `snapshots/<UTC timestamp>/` in the repository, ignored by git,
    holding one CSV file per tab with the raw cell values as read, unvalidated, so malformed
    hand-added rows are kept.
15. Snapshots are taken only before structural steps of an `--apply` run, once per run.

### Restore

16. `mise run restore <snapshot directory>` uses the same settings and login as `migrate`.
17. Without `--apply` it prints the tabs and row counts it would write and exits zero without
    writing.
18. With `--apply` it replaces the contents of every tab in the snapshot with the snapshot's
    values, creates tabs that are missing, and leaves tabs that are not in the snapshot untouched.
    Because `config` is a tab, this also restores `schema_version`.
19. Before writing, restore warns that `state` and `log` rows written after the snapshot are lost.
20. A snapshot directory that does not exist or holds no CSV files is an error.

### New tabs

21. **`migrations`** logs applied steps, one row per step, written only by the migration script.
    Columns in this order: `version` (integer, `2` or more), `name` (string, the step's name),
    `applied_at` (timestamp).
22. **`managed_questions`** lists the questions the migration script owns, written only by the
    migration script. Columns in this order: `question_id` (string, unique, references
    `questions.id`), `source_file` (string, the YAML file path relative to the repository root).

## Constraints & assumptions

- Python 3.14 and uv, as in `mise.toml`. New dependencies: `google-api-python-client` and
  `google-auth-oauthlib`, pinned in `pyproject.toml` with `uv.lock` committed.
- The user has a Google Cloud project with the Sheets API enabled and an OAuth client secret file
  for a desktop app.
- The script uses the models and row mapping in `migrations/schema/`.
- No live sheet exists yet, so adding `migrations` and `managed_questions` to schema version 1
  breaks no one.
- Google Sheets applies a single `spreadsheets.batchUpdate` atomically.

## Acceptance criteria

- [x] `mise run migrate` without `--apply` against a fake sheet writes nothing and prints the
      plan.
- [x] `--apply` against an empty fake sheet creates `questions`, `state`, `log`, `config`,
      `migrations` and `managed_questions` with header rows that match `docs/data-schema.md`,
      sets `schema_version` to the latest version and writes every YAML question.
- [x] A second `--apply` run without changes plans and writes no changes.
- [x] An overwritten managed question, a managed question removed from YAML, an unmanaged row and
      a takeover of an unmanaged row each appear in the report by id.
- [x] With a pending structural step and an unmanaged row, the script asks y/N and warns about
      broken formats; answering no writes nothing, and non-interactive input aborts.
- [x] A snapshot with every tab exists before the first structural write, and its path is
      printed; a run with only data-only steps or none takes no snapshot; a failing snapshot
      write aborts before any sheet write.
- [x] Each applied step sets `schema_version` and appends one `migrations` row in the same
      `batchUpdate`; a failing step leaves the earlier steps applied and the next run resumes
      from it.
- [x] A sheet with a higher `schema_version` than the latest step aborts without writing.
- [x] A tab with a wrong header row aborts with an error naming the tab.
- [x] Invalid YAML aborts before any network call.
- [x] A missing setting names its environment variable and flag; a flag overrides its
      environment variable.
- [x] `mise run restore` without `--apply` writes nothing; with `--apply` it writes a snapshot
      back so the fake sheet's cell values equal the snapshot's.
- [x] `check:data` reads only `migrations/questions/`.
- [x] `docs/data-schema.md` describes the two new tabs, the YAML location and who writes what;
      `AGENTS.md` names the `migrate` and `restore` tasks and `migrations/steps/`.
- [x] `snapshots/` is ignored by git.
- [x] `mise run test` and `mise run check:data` pass, and no test touches the network.
