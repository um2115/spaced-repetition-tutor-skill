# 4-create-tutor-skill

Create the `spaced-repetition-tutor` agent skill, which runs a spaced repetition review session
from the learner's Google Sheet: it asks due questions, judges the answers, explains on a wrong
answer and records the review state with FSRS.

Related: `5-add-build-task` adds the build that keeps the bundled schema copy, `SCHEMA_VERSION`
and the vendored py-fsrs in the skill up to date.

## Problem

Questions, the sheet schema and the migration script exist, but no agent can run a review
session. Nothing picks due questions, judges answers or writes the `state` and `log` tabs, so the
sheet is never used for learning and the FSRS state never changes.

## Goal

When the user calls the skill explicitly, the agent runs one review session against the sheet the
user names. It asks the active questions that are due, filtered by tag and topic if the user asks
for that, judges each answer with an FSRS rating from 1 to 4, shows the expected answer and the
rating, and on a wrong answer explains the topic until the learner says it is clear. After each
question it writes the new FSRS state, computed by a bundled stdlib Python script, to `state` and
appends the attempt to `log`, so aborting the session loses nothing. The session ends when
nothing is due or the requested number of questions is reached, with a summary.

## Triggers

The skill activates only when the user names it explicitly, like a command.

- "/spaced-repetition-tutor"
- "start the spaced repetition tutor"
- "spaced repetition tutor, 10 questions tagged git"

## Anti-triggers

Requests that do not name the skill must not activate it, even when they are about quizzing or
the questions:

- "quiz me on git"
- "explain git rebase"
- "add a question about rebase"

## Behavior

### Start

1. The skill checks that it can run code. Without code execution it tells the user that it needs
   code execution and stops.
2. It determines the sheet. If the user named a sheet, it uses that one. If the user named none
   and exactly one sheet is loaded in the session, it uses that one. If none or several are
   loaded, it asks the user which sheet to use.
3. It reads the `config` tab through whatever Google Sheets MCP server the agent has. If
   `schema_version` differs from the version in the skill's `SCHEMA_VERSION` file, it tells the
   user and stops without writing. Missing keys take their defaults (see *Config keys*).
4. It reads `questions`, `state` and `log`. It parses the user's request for a tag filter, a topic
   filter and a number of questions. Without a number there is no cap.

### Queue

5. The queue holds active questions only (`active` is `TRUE` or empty) that match the tag and
   topic filters. Due questions (a `state` row with `due` at or before now) come first, the most
   overdue first. New questions (no `state` row) follow.
6. If the queue is empty, the skill tells the user that nothing is due and stops.

### Per question

7. The skill asks the question and records the time it asked, using the script for the current
   time.
8. When the learner answers, it records the time of the answer and judges the answer against the
   question's `answer` and `explanation`, picking an FSRS rating: `1` Again (wrong or forgotten),
   `2` Hard, `3` Good, `4` Easy. It shows the learner the expected answer, the rating and a short
   reason for the rating.
9. It runs the script with the question's current state (or none for a new question), the rating,
   the review time and the scheduler settings from `config`, and gets the new state.
10. Right away, before the next question, it writes the new state to the question's `state` row
    (creating the row for a new question) and appends one `log` row: `timestamp` (time of the
    answer), `question_id`, `answer_text` (verbatim), `rating`, `judgement` (the short reason) and
    `seconds_to_answer` (time between asking and answering).
11. The learner may dispute or discuss the rating. The skill discusses it to help the learner
    understand, but the rating and the rows written in step 10 stay as they are, and nothing else
    is stored.

### Wrong answer

12. On rating `1`, the skill explains the topic, using the question's `explanation`, and asks the
    learner whether it is clear now. It keeps explaining and answering the learner's questions
    until the learner says it is clear.
13. The question then goes back into the queue after the remaining due and new questions and is
    asked again later in the same session, even though FSRS would set it due only minutes later.
    The repeat is judged, written and logged like any other review (steps 7 to 12). Repeats do not
    count toward the number of questions the user asked for.

### End

14. The session ends when the queue is empty or the requested number of questions (repeats not
    counted) has been asked. The learner can also stop at any time; everything answered so far is
    already written.
15. At the end the skill shows a summary: how many questions were asked, the ratings they got, and
    when the next question is due.

### Script

16. The script lives in the skill's `scripts/` directory and is runnable with Python 3.10 or newer,
    stdlib only, with no install step. It imports the scheduler of py-fsrs 6.3.2, vendored in
    `scripts/vendor/fsrs/` with that project's MIT license file.
17. It returns the current time in UTC and, given a state, a rating, a review time and the
    scheduler settings, the new state with every `state` column in the formats of
    `docs/data-schema.md`.
18. Pytest tests check that the script's results equal py-fsrs 6.3.2's for the same inputs.
    py-fsrs is added as a dev dependency only.

### Config keys

19. Four new `config` keys make the scheduler settable. A missing key takes its default, which is
    the py-fsrs default, so no migration step is needed:
    - `learning_steps`: list of minutes, each greater than `0`, default `1,10`.
    - `relearning_steps`: list of minutes, each greater than `0`, default `10`.
    - `maximum_interval`: integer days, `1` or more, default `36500`.
    - `enable_fuzzing`: boolean, default `TRUE`.

## Scope

### In scope

- `.agents/skills/spaced-repetition-tutor/SKILL.md`.
- The FSRS script in `.agents/skills/spaced-repetition-tutor/scripts/`.
- A one-time manual copy of the py-fsrs 6.3.2 scheduler modules (those that import with stdlib
  only) and its MIT license file into `.agents/skills/spaced-repetition-tutor/scripts/vendor/fsrs/`,
  and a one-time manual `.agents/skills/spaced-repetition-tutor/SCHEMA_VERSION` file holding the
  current schema version.
- Pytest tests for the script in `.agents/skills/spaced-repetition-tutor/scripts/tests/`, added to
  `testpaths`, and py-fsrs 6.3.2 as a dev dependency with `uv.lock` updated.
- A one-time manual copy of `docs/data-schema.md` into the skill, at
  `.agents/skills/spaced-repetition-tutor/references/data-schema.md`, which the skill reads for
  the tab formats.
- The four new `config` keys in `migrations/schema/` and `docs/data-schema.md`, with tests.
- A symlink `.claude/skills/spaced-repetition-tutor` → `../../.agents/skills/spaced-repetition-tutor`
  for local use.
- The `AGENTS.md` layout line changed from `.agents/spaced-repetition-tutor` to
  `.agents/skills/spaced-repetition-tutor`.

### Out of scope (non-goals)

Once activated, the skill does not:

- add, change or retire questions in the `questions` tab;
- change the `config` tab;
- edit or delete existing `log` rows;
- change a rating or a written row after a discussion with the learner, or store notes from it;
- calculate FSRS by hand when code execution is missing.

Not part of this spec either:

- The build task and keeping `references/data-schema.md`, `SCHEMA_VERSION` and the vendored
  py-fsrs in sync with their sources after this first manual copy. These go to `5-add-build-task`.
- Packaging and installing the skill.
- A migration step for the new `config` keys: a missing key takes its default.
- A cap on new questions per session or day, unless the user names a number.

## Draft description

> Runs a spaced repetition review session from the learner's Google Sheet: asks due questions,
> judges each answer with an FSRS rating, explains the topic on a wrong answer, and writes the
> review state and log after every question. Use only when the user explicitly names this skill,
> for example "/spaced-repetition-tutor", "start the spaced repetition tutor" or "spaced
> repetition tutor, 10 questions tagged git". Never activate on your own for general requests to
> quiz, explain a topic, or add or edit questions.

## Constraints & assumptions

- Harness-agnostic: frontmatter carries only `name` and `description`, bundled files are
  referenced by relative path, and no harness-specific tool, command or agent is named. Sheets
  access goes through whatever Google Sheets MCP server the agent has.
- `SKILL.md` is reserved: no other file in the bundle, at any depth, is named `SKILL.md` in any
  capitalization.
- The agent can run code; the script needs Python 3.10 or newer and no network access.
- The main target is claude.ai, where the user tells the agent to install the skill from the
  GitHub repository; the user has confirmed that this works. The skill must also run in other
  agents that have code execution and a Sheets MCP server.
- The sheet follows `docs/data-schema.md` at the current `schema_version`.
- py-fsrs 6.3.2 is MIT licensed and its default parameters match the default `fsrs_weights`.

## Acceptance criteria

- [ ] "/spaced-repetition-tutor", "start the spaced repetition tutor" and "spaced repetition
      tutor, 10 questions tagged git" activate the skill.
- [ ] The adjacent request "quiz me on git" does not activate it.
- [ ] Read cold, with no other context, every step is executable with only `SKILL.md` and its
      referenced files.
- [ ] The skill does only what *Behavior* states: no writes to `questions` or `config`, no edits
      to existing `log` rows.
- [ ] Without code execution the skill stops with a message; with no sheet or several sheets
      loaded it asks which sheet to use; with a different `schema_version` it stops without
      writing.
- [ ] `state` and the new `log` row are written after every question, before the next one is
      asked.
- [ ] A question rated `1` is asked again later in the same session, and the repeat does not count
      toward the requested number.
- [ ] An empty queue tells the user that nothing is due and stops; a finished session shows the
      summary.
- [x] The script runs with stdlib only, and its tests show it gives the same results as py-fsrs
      6.3.2; the vendored code ships with the MIT license file.
- [x] `learning_steps`, `relearning_steps`, `maximum_interval` and `enable_fuzzing` are validated
      in `migrations/schema/` and documented in `docs/data-schema.md`.
- [x] No file in the skill other than `SKILL.md` is named `SKILL.md` in any capitalization.
- [x] `.claude/skills/spaced-repetition-tutor` links to the skill, and `AGENTS.md` names
      `.agents/skills/spaced-repetition-tutor`.
- [x] `mise run test`, `mise run check:data` and `mise run check:docs` pass.
