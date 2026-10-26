# Spec todos

Work deferred to later specs.

- [ ] **Migration script**: write questions from the YAML files in `migrations/` into the Google
      Sheet using the `migrations/schema/` models. It decides where the YAML files live, what
      happens to questions removed from YAML, and how `schema_version` changes are applied.
      Deferred from `1-define-data-schema`.
- [ ] **`build` task**: create a new version of the skill under
      `.agents/spaced-repetition-tutor`, bundling `docs/data-schema.md` so the agent ships with the
      schema. Deferred from `2-document-data-schema`.
