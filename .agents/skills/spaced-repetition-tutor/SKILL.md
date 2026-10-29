---
name: spaced-repetition-tutor
description: Runs a spaced repetition review session from the learner's Google Sheet - asks due questions, judges each answer with an FSRS rating, explains the topic on a wrong answer, and writes the review state and log after every question. Use only when the user explicitly names this skill, for example "/spaced-repetition-tutor", "start the spaced repetition tutor" or "spaced repetition tutor, 10 questions tagged git". Never activate on your own for general requests to quiz, explain a topic, or add or edit questions.
---

# Spaced repetition tutor

You run one review session for one learner. The questions and the review history live in a
Google Sheet that you read and write through the Google Sheets tools you have. A bundled script
does the FSRS scheduling; never calculate a schedule yourself.

Paths below are relative to the directory that holds this file:

- `references/data-schema.md` describes every tab, column and cell format of the sheet. Read it
  before the first write.
- `SCHEMA_VERSION` holds the schema version this skill follows.
- `scripts/fsrs_review.py` tells the time and schedules a review. It needs Python 3.10 or newer
  and nothing else; run it with `python3`.

## What you never do

- Add, change, retire or delete rows in `questions`.
- Change `config`, `migrations` or `managed_questions`.
- Change or delete an existing `log` row. You only append.
- Change a rating, or a row you wrote, after the learner disputes it, or store notes from the
  discussion.
- Work out a schedule, a due date or a stability by hand.

## 1. Start

1. Run `python3 scripts/fsrs_review.py now`. If you cannot run code, tell the learner: "The
   spaced repetition tutor needs code execution to schedule reviews, so I can't run a session
   here." Then stop. If you have no tool to read and write Google Sheets, say so and stop.
2. Pick the sheet:
   - If the learner named one (a link, an id or a title), use it.
   - Otherwise, if exactly one Google Sheet has come up in this conversation, use it.
   - Otherwise (none, or several), ask the learner which sheet to use, and wait.
3. Read the `config` tab. Read cell values unformatted if your tools allow it, so numbers keep
   every digit. Build a map from each `key` to its `value` cell, as text. If `schema_version` is
   missing it is `1`. If it differs from the number in `SCHEMA_VERSION`, tell the learner that
   the sheet follows schema version X and this skill follows version Y, that the sheet or the
   skill needs updating, and stop without writing anything.
4. Check the config: run the script's `review` command once (see *Scheduling*) with
   `"question_id": "config-check"`, `"state": null`, `"rating": 3`, the time from step 1 and the
   config map. If it exits with an error, show the error, say the `config` tab must be fixed, and
   stop without writing anything. Discard its output.
5. Read the `questions` and `state` tabs the same way, and note the sheet row of each `state`
   row so you can overwrite it later.
6. From the learner's request, take:
   - a number of questions, if they named one. Without a number there is no limit.
   - tags, if they named any ("tagged git", "tag k8s").
   - topics, if they named any ("on Kubernetes", "topic Git").

## 2. Build the queue

1. Keep the questions whose `active` cell is `TRUE` or empty (case does not matter).
2. If the learner named topics, keep the questions whose `topic` matches one of them, ignoring
   case. If they named tags, keep the questions that have at least one of them in `tags`
   (a comma-separated list), ignoring case. If they named both, a question must match both.
3. A question is **due** when it has a `state` row whose `due` is at or before now. Compare the
   timestamps as times, not as text: a value may carry an offset such as `+02:00`.
4. A question is **new** when it has no `state` row, or its `fsrs_state` is `new`.
5. The queue is the due questions, the earliest `due` first, followed by the new questions in
   sheet order. Questions that are neither due nor new are not asked.
6. If the queue is empty, tell the learner that nothing is due (for their filter, if they gave
   one) and stop.

## 3. Ask a question

Repeat for each question in the queue. Take questions from the front of the queue until you have
asked the number the learner named. Repeats (see *Wrong answer*) do not count toward that number.

1. Run `python3 scripts/fsrs_review.py now` and keep the time as **asked at**. Then ask the
   `question` text, with its topic, and nothing else. Do not hint at the answer.
2. When the learner answers, first run `now` again and keep the time as **answered at**.
3. Judge the answer against `answer` and `explanation`, on meaning rather than wording, and pick
   the rating:
   - `1` Again: wrong, missing the core of the answer, or "I don't know".
   - `2` Hard: right in its core, but incomplete, partly wrong, or reached with obvious struggle.
   - `3` Good: right, possibly with small gaps or after some thought.
   - `4` Easy: fully right, precise and immediate.
4. Show the learner the expected `answer`, the rating with its name, and one short reason for the
   rating.
5. Schedule the review (see *Scheduling*) with the rating and **answered at** as `review_time`.
6. Write, before anything else happens:
   - The new state into `state`: overwrite the question's `state` row with the script's `row`,
     or append the `row` as a new row if the question has none.
   - One new row appended to `log`, in this column order: `timestamp` = **answered at**,
     `question_id`, `answer_text` = the learner's answer verbatim, `rating`, `judgement` = your
     short reason, `seconds_to_answer` = the whole seconds from **asked at** to **answered at**.

   Write every cell as plain text, exactly as given, so the sheet does not reformat it (choose
   raw input over user-entered input if your tools offer the choice). If a write fails, tell the
   learner and stop: the next session must not build on a missing row.
7. If the learner disputes or asks about the rating, discuss it so they understand the answer
   better next time. The rating and the rows you wrote stay as they are.
8. On rating `1`, continue with *Wrong answer*. Otherwise go to the next question.

## 4. Wrong answer

1. Explain the topic, building on the question's `explanation` and on what the learner's answer
   got wrong. Then ask whether it is clear now.
2. Answer the learner's questions and explain again, in other words or with an example, until
   the learner says it is clear.
3. Put the question back at the end of the queue. It is asked again later in this session, after
   the questions still waiting, and is judged, written and logged like any other question,
   including this section if it is rated `1` again. Read its current `state` row (the one you
   wrote) before scheduling the repeat.

## 5. End

1. The session ends when the queue is empty, or when the learner's number of questions has been
   asked and no repeats are waiting. The learner can stop at any time: everything answered so far
   is written already, so just end.
2. Show a summary: how many questions were asked (with the number of repeats), each question with
   its ratings, and when the next question is due, which is the earliest `due` among the `state`
   rows of the active questions after this session's writes.

## Scheduling

Run `python3 scripts/fsrs_review.py review` with a JSON request on standard input:

```json
{
  "question_id": "git-rebase",
  "state": {"fsrs_state": "review", "step": "", "stability": "5.2", "difficulty": "6.1",
            "due": "2026-10-20T10:00:00Z", "last_review": "2026-10-15T10:00:00Z",
            "reps": "4", "lapses": "0"},
  "rating": 3,
  "review_time": "2026-10-26T14:30:00Z",
  "config": {"desired_retention": "0.9", "enable_fuzzing": "FALSE"}
}
```

- `state` is the question's `state` row by column name, cell values as text, or `null` when the
  question has no row.
- `config` is the map of `config` keys to their value cells from *Start*.
- `rating` is `1` to `4`; `review_time` is a timestamp from `now`.

It prints the new state as JSON:

```json
{"state": {"question_id": "git-rebase", "fsrs_state": "review", ...},
 "row": ["git-rebase", "review", "", "22.184733118152856", "6.089128369296838",
         "2026-11-17T14:30:00Z", "2026-10-26T14:30:00Z", "5", "0"]}
```

`row` holds the `state` columns in sheet order, ready to write. On bad input the script prints an
error starting with `error:` and exits with status 2; tell the learner what it says and stop
without writing for that question.
