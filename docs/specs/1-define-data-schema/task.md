# 1-define-data-schema

Define the shape of the tutor's data as Python models that validate the YAML question files and
map every Google Sheets tab to and from rows.

Related: `2-document-data-schema` documents this schema for people and the agent.

## Problem

The README says each sheet entry must follow a schema, but that schema is a `<TODO>`. Nothing
defines which tabs the Google Sheets document has, which columns they hold, or how questions are
written as data in `migrations/`. Hand edits, migrations and the tutor agent can therefore drift
apart, and nothing catches a malformed question before it reaches the sheet.

## Goal

Python models in `migrations/schema/` define the four sheet tabs (`questions`, `state`, `log`,
`config`) and the YAML question file format. `mise run check:data` validates every YAML question
file in `migrations/` and names each error by file and question id. Every model converts to a sheet
row and back without loss, so a later migration script can rely on it.

## Scope

### In scope

- Pydantic models for a question, an FSRS state row, a log row and the config entries.
- A loader and validator for the YAML question files.
- Mapping between each model and a sheet row: column order, header names and cell formats.
- A `check:data` mise task that runs the validation.
- Pytest tests for the models, the validation and the row mapping.

### Out of scope (non-goals)

- The migration script that writes to Google Sheets. It is a later spec.
- The `build` task that bundles the schema document into the skill. It is a later spec.
- Scheduling logic and FSRS math. This spec defines only the fields FSRS needs.
- Several learners per sheet. One sheet belongs to one learner, so no tab has a learner column.
- Answer formats other than free text, such as multiple choice.
- The human-readable schema document (`2-document-data-schema`).
- Validating the live Google Sheet. Validation covers the YAML files only.

## Behavior

### Sheet tabs

1. **`questions`** is written by migrations or by hand. It has one row per question, with columns
   in this order:

   | Column | Type | Required | Rule |
   | --- | --- | --- | --- |
   | `id` | string | yes | lowercase kebab-case slug, `^[a-z0-9]+(-[a-z0-9]+)*$`, unique across all questions |
   | `topic` | string | yes | non-empty |
   | `tags` | list of strings | no | default empty; stored in the cell as comma-separated values |
   | `question` | string | yes | non-empty |
   | `answer` | string | yes | non-empty, the expected free-text answer |
   | `explanation` | string | yes | non-empty; background the tutor uses when explaining |
   | `active` | boolean | no | default `true`; `false` retires a question without deleting it |

2. **`state`** is written by the agent only. A question gets its row when the agent reviews it for
   the first time, so a question without a row is new. Migrations never touch this tab. Columns in
   this order:

   | Column | Type | Rule |
   | --- | --- | --- |
   | `question_id` | string | references `questions.id`, unique in this tab |
   | `fsrs_state` | enum | one of `new`, `learning`, `review`, `relearning` |
   | `step` | integer or empty | learning step, empty when not in a learning step |
   | `stability` | float or empty | FSRS stability |
   | `difficulty` | float or empty | FSRS difficulty |
   | `due` | timestamp | next due time |
   | `last_review` | timestamp or empty | time of the last review |
   | `reps` | integer | number of reviews, `>= 0` |
   | `lapses` | integer | number of times forgotten, `>= 0` |

3. **`log`** is written by the agent, which only appends rows. There is one row per answer
   attempt, with columns in this order:

   | Column | Type | Rule |
   | --- | --- | --- |
   | `timestamp` | timestamp | when the answer was given |
   | `question_id` | string | references `questions.id` |
   | `answer_text` | string | the learner's answer, verbatim |
   | `rating` | integer | FSRS rating 1-4: 1 Again, 2 Hard, 3 Good, 4 Easy |
   | `judgement` | string | the agent's short reason for the rating |
   | `seconds_to_answer` | number | seconds between asking and answering, `>= 0` |

4. **`config`** has two columns, `key` and `value`, and these keys:

   | Key | Type | Default |
   | --- | --- | --- |
   | `schema_version` | integer | `1` |
   | `desired_retention` | float in `(0, 1)` | `0.9` |
   | `fsrs_weights` | list of floats, comma-separated in the cell | the FSRS-6 default parameters (21 values) of the `fsrs` (py-fsrs) library version pinned in the implementation |

### Formats

5. Timestamps are ISO 8601 in UTC, for example `2026-10-26T14:30:00Z`.
6. List values in a cell (`tags`, `fsrs_weights`) are comma-separated. Whitespace around the items
   is ignored, and an empty cell is an empty list.
7. Booleans in a cell are `TRUE` or `FALSE`, the way Google Sheets writes them.

### YAML question files

8. Questions live as YAML in `migrations/`, one file per topic. Each file has a top-level `topic`
   and a `questions` list. The topic of every question in the file comes from that `topic` field,
   and the file name is free:

   ```yaml
   topic: Kubernetes
   questions:
     - id: k8s-pod-lifecycle
       tags: [pods, basics]
       question: ...
       answer: ...
       explanation: ...
       active: true   # optional, default true
   ```

9. In YAML, `tags` is a list and `active` is a YAML boolean.

### Validation

10. `mise run check:data` loads every YAML question file and checks it against the models. It
    collects all errors instead of stopping at the first.
11. These cases are errors: a missing required field, an empty required string, a wrong type, an
    unknown field, an `id` that is not a lowercase kebab-case slug, an `id` used more than once
    across all files, and a file without `topic` or `questions`.
12. Each error names the file and, where there is one, the question `id` (otherwise the list
    index) and the field.
13. When there are errors, the task prints them and exits non-zero. When there are none, it
    exits zero. A `migrations/` directory with no question files is valid.

### Row mapping

14. Each model converts to a sheet row (a list of cell values in the column order above) and
    back. The header row for each tab comes from the same definition.
15. A row that does not match its model (wrong column count, bad enum value, unparsable number or
    timestamp) raises an error that names the tab, row and column.

## Constraints & assumptions

- Python 3.14, installed through mise (`mise.toml`).
- Dependencies: pydantic, PyYAML and pytest. Nothing else is required.
- The code lives in `migrations/schema/`.
- One learner per sheet.
- FSRS is the scheduling model. The state columns follow the py-fsrs card fields, plus `reps` and
  `lapses`.
- The exact location of the YAML files under `migrations/` is for the migration spec to decide.
  The validator finds them by the file layout that spec settles on. Until then it reads every
  `*.yaml` file under `migrations/` that is not inside `migrations/schema/`.

## Acceptance criteria

- [x] A valid sample YAML file with two topics' worth of questions passes `mise run check:data`,
      which exits zero.
- [x] Each of these fails with a non-zero exit and an error naming the file, id and field: a
      duplicate id across two files, an id with uppercase or spaces, a missing `answer`, an empty
      `explanation`, an unknown field, and `active: "yes"`.
- [x] One run with several broken files reports all of their errors.
- [x] For every tab, converting a model to a row and back gives an equal model, including an empty
      tag list, empty optional state fields and timestamps.
- [x] Each tab's header row matches the column order in this spec exactly.
- [x] The `config` defaults are `schema_version` 1, `desired_retention` 0.9 and the 21 FSRS-6
      default weights.
- [x] A malformed row (bad `fsrs_state`, `rating` 5, unparsable `due`) raises an error that names
      the tab, row and column.
- [x] The pytest tests pass when run through mise.
- [x] `AGENTS.md` names the `check:data` task and the test command.
