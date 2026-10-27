# Migration steps

- Never edit, rename or renumber a step once it has run against a live sheet. Fix it with a new
  step.
- A step that changes the columns of a tab updates that tab's module in `migrations/schema/`
  and `docs/data-schema.md` in the same change: after the steps run, the migration script checks
  every header row against `migrations/schema/`.
- Mark a step structural when it adds, removes or renames tabs or columns, or changes the format
  of cells. Only data changes within the current format are data-only.
- A step does not move the `schema_version` row of `config`: the runner sets it by the row number
  it read before the step.
- Test every step against the fake Sheets client: one test from the previous version's sheet to
  the step's version.
