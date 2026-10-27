# Data schema

The spaced repetition tutor keeps its questions and review history in one Google Sheets document
with six tabs, and its question source in YAML files. This page describes every tab, column and
format, and says who may write what. It is for people who edit the sheet by hand, people who
write YAML question files, and the tutor agent.

One sheet belongs to one learner, so no tab has a learner column.

## Overview

| Tab | Holds | Written by |
| --- | --- | --- |
| `questions` | one row per question | the migration script or by hand; the agent only reads it |
| `state` | the FSRS review state, one row per reviewed question | the agent; migration steps may change it |
| `log` | one row per answer attempt | the agent, only by appending; migration steps may change it |
| `config` | tutor settings as `key`/`value` rows | by hand or the migration script; the agent only reads it |
| `migrations` | one row per applied migration step | the migration script only |
| `managed_questions` | the questions the migration script owns | the migration script only |

Rules for every tab:

- Row 1 is the header row. It holds the column names below, exactly as written and in exactly
  this order. Data starts in row 2.
- A row has no more cells than the tab has columns. Empty cells at the end of a row are fine.
- Cell values follow the [formats](#formats) below.
- The tab names are exactly `questions`, `state`, `log`, `config`, `migrations` and
  `managed_questions`.

## Tab: `questions`

One row per question. Columns in this order:

| Column | Type | Required | Default | Rule |
| --- | --- | --- | --- | --- |
| `id` | string | yes | | a lowercase [id slug](#id-slug), unique across all questions |
| `topic` | string | yes | | not empty |
| `tags` | list of strings | no | empty list | [list](#lists) of tags; each tag is not empty and has no comma |
| `question` | string | yes | | not empty; the question the tutor asks |
| `answer` | string | yes | | not empty; the expected free-text answer |
| `explanation` | string | yes | | not empty; background the tutor uses when it explains the topic |
| `active` | boolean | no | `TRUE` | [boolean](#booleans); `FALSE` retires the question without deleting it |

"Not empty" means the cell holds more than whitespace. An empty `active` cell counts as `TRUE`.

The tutor asks only active questions. Never change the `id` of a question that has been reviewed:
its `state` and `log` rows refer to it by `id`.

A question whose `id` is listed in [`managed_questions`](#tab-managed_questions) is managed: it
comes from a YAML question file, and the migration script overwrites its row whenever the row
differs from the YAML. Any other row is unmanaged: it was added by hand, and the migration script
neither changes nor validates it, unless a YAML question with the same `id` takes it over.

## Tab: `state`

The FSRS review state of each question. The agent writes it; nobody else does, except a numbered
migration step that changes the schema. A question gets its row when the agent reviews it for the first time, so a
question without a row here is new. Columns in this order:

| Column | Type | Required | Default | Rule |
| --- | --- | --- | --- | --- |
| `question_id` | string | yes | | the `id` of a row in `questions`; unique in this tab |
| `fsrs_state` | enum | yes | | one of `new`, `learning`, `review`, `relearning` |
| `step` | integer | no | empty | the current learning step; empty when the question is not in a learning step |
| `stability` | float | no | empty | FSRS stability: the number of days until the chance of recall falls to 90%; empty before the first rating |
| `difficulty` | float | no | empty | FSRS difficulty, from 1 (easy) to 10 (hard); empty before the first rating |
| `due` | timestamp | yes | | when the question is next due |
| `last_review` | timestamp | no | empty | when the question was last reviewed |
| `reps` | integer | yes | `0` for a new row | number of reviews, `0` or more |
| `lapses` | integer | yes | `0` for a new row | number of times the learner forgot the answer, `0` or more |

`fsrs_state` values:

- `new`: never reviewed.
- `learning`: being learned for the first time, in short steps.
- `review`: learned; comes back at growing intervals.
- `relearning`: forgotten during review and being learned again, in short steps.

## Tab: `log`

One row per answer attempt. The agent only appends rows: it never changes or deletes one, and
neither should anybody else, except a numbered migration step that changes the schema. Columns in this order:

| Column | Type | Required | Rule |
| --- | --- | --- | --- |
| `timestamp` | timestamp | yes | when the learner gave the answer |
| `question_id` | string | yes | the `id` of a row in `questions` |
| `answer_text` | string | yes | the learner's answer, verbatim; may be empty |
| `rating` | integer | yes | the FSRS rating, `1` to `4` (see below) |
| `judgement` | string | yes | the agent's short reason for the rating; may be empty |
| `seconds_to_answer` | number | yes | seconds between asking and answering, `0` or more |

`rating` values:

- `1` Again: wrong or forgotten.
- `2` Hard: right, with serious difficulty.
- `3` Good: right, after some thought.
- `4` Easy: right, without effort.

## Tab: `config`

Two columns, `key` and `value`. Each row sets one key. A key missing from the tab takes its
default, an unknown key is an error, and a key may appear only once.

| Key | Type | Default | Rule |
| --- | --- | --- | --- |
| `schema_version` | integer | `1` | `1` or more; the version of this schema the sheet follows. The migration script sets it; do not change it by hand |
| `desired_retention` | float | `0.9` | greater than `0` and less than `1`; the share of reviews the learner should get right |
| `fsrs_weights` | list of floats | the FSRS-6 default parameters (below) | [list](#lists) of exactly 21 numbers |

The default `fsrs_weights` are the FSRS-6 default parameters of py-fsrs 6.3.2:

```text
0.212,1.2931,2.3065,8.2956,6.4133,0.8334,3.0194,0.001,1.8722,0.1666,0.796,1.4835,0.0614,0.2629,1.6483,0.6014,1.8729,0.5425,0.0912,0.0658,0.1542
```

A key that is present needs a valid value; leave the row out to get the default.

## Tab: `migrations`

One row per migration step the migration script has applied to the sheet, in the order they were
applied. Only the migration script writes this tab. Columns in this order:

| Column | Type | Required | Rule |
| --- | --- | --- | --- |
| `version` | integer | yes | the schema version the step brought the sheet to, `2` or more |
| `name` | string | yes | not empty; the step's name |
| `applied_at` | timestamp | yes | when the step was applied |

A new sheet starts at schema version `1`, which needs no step, so this tab starts empty.

## Tab: `managed_questions`

The questions the migration script owns: one row per question it wrote from a YAML question file.
Only the migration script writes this tab. Columns in this order:

| Column | Type | Required | Rule |
| --- | --- | --- | --- |
| `question_id` | string | yes | the `id` of a row in `questions`; unique in this tab |
| `source_file` | string | yes | not empty; the path of the YAML question file, relative to the repository root, such as `migrations/questions/git.yaml` |

## Formats

### Timestamps

ISO 8601 with a time zone, for example `2026-10-26T14:30:00Z`. Values are written in UTC with a
trailing `Z`. A timestamp in another time zone, such as `2026-10-26T16:30:00+02:00`, is read and
converted to UTC. A timestamp without a time zone is an error.

### Numbers

An integer is written without a decimal point, such as `3`. A float or number uses a dot as the
decimal separator, such as `0.9`.

### Lists

`tags` and `fsrs_weights` hold lists as comma-separated values in one cell, for example
`pods,basics`. Whitespace around each item is ignored, so `pods, basics` is the same list. An
empty cell is an empty list.

### Booleans

`TRUE` or `FALSE`, the way Google Sheets writes them. Lowercase is accepted too.

### Id slug

A question `id` is lowercase kebab-case: lowercase letters `a`-`z` and digits `0`-`9`, in groups
joined by single hyphens. It matches `^[a-z0-9]+(-[a-z0-9]+)*$`.

- Valid: `k8s-pod-lifecycle`, `git-rebase`, `http2`
- Invalid: `Git-Rebase` (uppercase), `git rebase` (space), `git--rebase` (double hyphen),
  `-git` (leading hyphen), `git_rebase` (underscore)

## YAML question files

Migrations keep questions in YAML files in the `migrations/questions/` directory of the
repository, so git is the single source of truth. Every `*.yaml` file under `migrations/questions/`,
in subdirectories too, is a question file. The file name is free.

Each file holds one topic: a top-level `topic` and a `questions` list.

```yaml
topic: Kubernetes
questions:
  - id: k8s-pod-lifecycle
    tags: [pods, basics]
    question: Which phases can a pod be in?
    answer: Pending, Running, Succeeded, Failed and Unknown.
    explanation: >-
      The phase is a summary of where the pod is in its lifecycle. A pod is Pending until all of
      its containers have been created, Running while at least one container runs, Succeeded or
      Failed once all containers have stopped, and Unknown when the node cannot be reached.
  - id: k8s-service-purpose
    question: What does a Service give a set of pods?
    answer: A stable network address and load balancing across the pods.
    explanation: >-
      Pods come and go and change their IP addresses. A Service selects pods by label and gives
      them one stable virtual IP and DNS name that spreads traffic across them.
    active: false
```

Each entry in `questions` has the fields of the [`questions` tab](#tab-questions) except
`topic`, which comes from the file's top-level `topic`:

- `id`, `question`, `answer` and `explanation` are required strings and must not be empty.
- `tags` is optional; it is a YAML list of strings, such as `[pods, basics]`, not a
  comma-separated string.
- `active` is optional and defaults to `true`; it is a YAML boolean, `true` or `false`, not a
  string such as `"yes"`.

Values are not converted: `id: 123` is a number, not a string, and is an error. Quote such values
(`id: "123"`).

### Checking the files

Run `mise run check:data` in the repository. It checks every question file and reports all
errors at once, not only the first. These are errors:

- a missing required field, or an empty required string
- a value of the wrong type
- an unknown field, including `topic` inside a question entry
- an `id` that is not a valid [id slug](#id-slug)
- an `id` used more than once, in the same file or across files
- a file without `topic` or `questions`, or a file that is not valid YAML

Each error names the file, the question (by `id`, or by its position in the list, counted from 0, such as `#2`,
when it has no usable id) and the field:

```text
migrations/questions/git.yaml: question Git-Rebase: field id: String should match pattern '^[a-z0-9]+(-[a-z0-9]+)*$'
migrations/questions/git.yaml: question Git-Rebase: field explanation: Value error, must not be empty
2 error(s) in question files
```

The task exits non-zero when there are errors and zero when there are none. A
`migrations/questions/` directory without question files is valid.

### Writing the files into the sheet

`mise run migrate --apply` writes the YAML questions into the `questions` tab, after it has
checked the files the same way:

- A question whose `id` is not in the sheet is appended, and listed in `managed_questions`.
- A managed question whose row differs from the YAML is overwritten with the YAML values.
- A managed question that is no longer in any YAML file is left in the sheet. Retire it with
  `active: false` instead of deleting it from YAML.
- An unmanaged row with the `id` of a YAML question is taken over: it gets the YAML values and
  becomes managed.

Without `--apply`, the task only prints what it would change.

## Editing by hand

### Add a question

1. Open the `questions` tab and go to the first empty row.
2. In `id`, type a new [id slug](#id-slug) that no other row uses, such as `git-rebase-onto`.
3. Fill in `topic`, `question`, `answer` and `explanation`. None of them may be empty.
4. Optionally fill in `tags`, separated by commas, such as `git,branches`.
5. Leave `active` empty or type `TRUE`.

Do not add a `state` row for it. The agent creates one on the first review.

### Retire a question

Set `active` to `FALSE`. The tutor stops asking the question, and its review history stays. Set
it back to `TRUE` to bring the question back with its history.

### Do

- Keep the header row of every tab exactly as described above.
- Use a new `id` for a new question, even one that replaces a retired question.
- Write timestamps, lists and booleans in the [formats](#formats) above.
- Change `config` values if you want other settings; delete a `config` row to return to its
  default.

### Don't

- Don't delete question rows; retire them with `active` set to `FALSE`. Their `state` and `log`
  rows refer to them.
- Don't change the `id` of an existing question.
- Don't edit the `state` or `log` tabs. The agent owns them.
- Don't edit the `migrations` or `managed_questions` tabs, or `schema_version` in `config`. The
  migration script owns them.
- Don't rename, reorder, add or remove columns or tabs.
- Don't put commas inside a tag.
- Don't edit by hand the questions you keep in YAML files, the managed ones. Change the YAML
  instead: the next migration overwrites hand edits of managed rows.
