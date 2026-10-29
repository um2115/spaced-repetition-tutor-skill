#!/usr/bin/env python3
"""Tell the time and schedule a review with the FSRS scheduler of py-fsrs 6.3.2.

Runs with Python 3.10 or newer and the standard library only; py-fsrs is vendored in `vendor/`.

    python3 fsrs_review.py now
        Prints the current time in UTC, such as 2026-10-26T14:30:00Z.

    python3 fsrs_review.py review < request.json
        Reads one review as JSON from standard input and prints the new `state` row as JSON.

The request holds sheet cell values as strings, exactly as read from the sheet:

    {
      "question_id": "git-rebase",
      "state": {"fsrs_state": "learning", "step": "0", ..., "lapses": "0"},
      "rating": 3,
      "review_time": "2026-10-26T14:30:00Z",
      "config": {"desired_retention": "0.9", "learning_steps": "1,10"}
    }

`state` is the question's `state` row by column name, or null for a question without one.
`config` holds the `config` rows by key; a missing key takes its default. The answer is

    {"state": {"question_id": ..., ..., "lapses": ...}, "row": [...]}

with every `state` column as a cell string, `row` in column order. On bad input the script
prints the error to standard error and exits with status 2.

py-fsrs keeps no `reps` and `lapses`: a review adds one to `reps`, and an Again rating on a
question in the `review` state adds one to `lapses`, the way FSRS counts a lapse.
"""

import argparse
import json
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))

from fsrs import Card, Rating, Scheduler, State  # noqa: E402
from fsrs.scheduler import DEFAULT_PARAMETERS  # noqa: E402

COLUMNS = (
    "question_id",
    "fsrs_state",
    "step",
    "stability",
    "difficulty",
    "due",
    "last_review",
    "reps",
    "lapses",
)
STATES = {"learning": State.Learning, "review": State.Review, "relearning": State.Relearning}
CONFIG_KEYS = {
    "schema_version",
    "desired_retention",
    "fsrs_weights",
    "learning_steps",
    "relearning_steps",
    "maximum_interval",
    "enable_fuzzing",
}


class InputError(ValueError):
    """A request that does not follow the formats of the data schema."""


def format_timestamp(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(cell, name):
    text = str(cell).strip()
    # Python 3.10 reads no trailing Z, so spell it as an offset.
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        raise InputError(f"{name}: not an ISO 8601 timestamp: {cell!r}") from None
    if value.tzinfo is None:
        raise InputError(f"{name}: timestamp has no time zone: {cell!r}")
    return value.astimezone(timezone.utc)


def parse_int(cell, name):
    try:
        return int(str(cell).strip())
    except ValueError:
        raise InputError(f"{name}: not an integer: {cell!r}") from None


def parse_float(cell, name):
    try:
        value = float(str(cell).strip())
    except ValueError:
        raise InputError(f"{name}: not a number: {cell!r}") from None
    if not math.isfinite(value):
        raise InputError(f"{name}: not a finite number: {cell!r}")
    return value


def parse_optional(parse, cell, name):
    if cell is None or str(cell).strip() == "":
        return None
    return parse(cell, name)


def parse_float_list(cell, name):
    text = str(cell).strip()
    if text == "":
        return []
    return [parse_float(item, name) for item in text.split(",")]


def parse_bool(cell, name):
    text = str(cell).strip().upper()
    if text in ("TRUE", "FALSE"):
        return text == "TRUE"
    raise InputError(f"{name}: not TRUE or FALSE: {cell!r}")


def format_optional(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return repr(value)
    return str(value)


def scheduler_from_config(config):
    """Build the scheduler from the `config` rows; keys that are missing take their defaults."""
    unknown = sorted(set(config) - CONFIG_KEYS)
    if unknown:
        raise InputError(f"config: unknown key {unknown[0]!r}")
    settings = {}
    if "desired_retention" in config:
        retention = parse_float(config["desired_retention"], "desired_retention")
        if not 0 < retention < 1:
            raise InputError("desired_retention: must be greater than 0 and less than 1")
        settings["desired_retention"] = retention
    if "fsrs_weights" in config:
        weights = parse_float_list(config["fsrs_weights"], "fsrs_weights")
        if len(weights) != len(DEFAULT_PARAMETERS):
            raise InputError(f"fsrs_weights: {len(weights)} numbers, expected 21")
        settings["parameters"] = weights
    for key in ("learning_steps", "relearning_steps"):
        if key in config:
            minutes = parse_float_list(config[key], key)
            if any(step <= 0 for step in minutes):
                raise InputError(f"{key}: every step must be greater than 0")
            settings[key] = [timedelta(minutes=step) for step in minutes]
    if "maximum_interval" in config:
        days = parse_int(config["maximum_interval"], "maximum_interval")
        if days < 1:
            raise InputError("maximum_interval: must be 1 or more")
        settings["maximum_interval"] = days
    if "enable_fuzzing" in config:
        settings["enable_fuzzing"] = parse_bool(config["enable_fuzzing"], "enable_fuzzing")
    try:
        return Scheduler(**settings)
    except ValueError as error:
        raise InputError(f"fsrs_weights: {error}") from None


def card_from_state(state, review_time):
    """Turn a `state` row into a py-fsrs card; no row, or `new`, is a card never reviewed."""
    if state is None or str(state.get("fsrs_state", "")).strip() == "new":
        return Card(card_id=1, due=review_time), 0, 0
    fsrs_state = str(state.get("fsrs_state", "")).strip()
    if fsrs_state not in STATES:
        raise InputError(f"fsrs_state: not one of new, learning, review, relearning: {fsrs_state!r}")
    card = Card(
        card_id=1,
        state=STATES[fsrs_state],
        step=parse_optional(parse_int, state.get("step"), "step"),
        stability=parse_optional(parse_float, state.get("stability"), "stability"),
        difficulty=parse_optional(parse_float, state.get("difficulty"), "difficulty"),
        due=parse_timestamp(state.get("due", ""), "due"),
        last_review=parse_optional(parse_timestamp, state.get("last_review"), "last_review"),
    )
    if card.state != State.Learning and (card.stability is None or card.difficulty is None):
        raise InputError(f"stability and difficulty: required in the {fsrs_state} state")
    if card.state == State.Relearning and card.step is None:
        raise InputError("step: required in the relearning state")
    reps = parse_optional(parse_int, state.get("reps"), "reps") or 0
    lapses = parse_optional(parse_int, state.get("lapses"), "lapses") or 0
    return card, reps, lapses


def review(request):
    """Return the new `state` row, by column name, for one review."""
    if not isinstance(request, dict):
        raise InputError("request: expected a JSON object")
    question_id = str(request.get("question_id", "")).strip()
    if not question_id:
        raise InputError("question_id: missing")
    try:
        rating = Rating(int(request.get("rating")))
    except (TypeError, ValueError):
        raise InputError(f"rating: not 1, 2, 3 or 4: {request.get('rating')!r}") from None
    review_time = parse_timestamp(request.get("review_time", ""), "review_time")
    config = request.get("config") or {}
    state = request.get("state")
    if not isinstance(config, dict) or not (state is None or isinstance(state, dict)):
        raise InputError("config and state: expected JSON objects")

    scheduler = scheduler_from_config(config)
    card, reps, lapses = card_from_state(state, review_time)
    lapsed = card.state == State.Review and rating == Rating.Again
    card, _ = scheduler.review_card(card, rating, review_datetime=review_time)
    return {
        "question_id": question_id,
        "fsrs_state": card.state.name.lower(),
        "step": format_optional(card.step),
        "stability": format_optional(card.stability),
        "difficulty": format_optional(card.difficulty),
        "due": format_timestamp(card.due),
        "last_review": format_timestamp(card.last_review),
        "reps": str(reps + 1),
        "lapses": str(lapses + 1 if lapsed else lapses),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("now", help="print the current time in UTC")
    review_parser = commands.add_parser("review", help="schedule one review read from stdin")
    review_parser.add_argument("--seed", type=int, help="seed the fuzzing, for tests")
    args = parser.parse_args(argv)

    if args.command == "now":
        print(format_timestamp(datetime.now(timezone.utc).replace(microsecond=0)))
        return 0
    if args.seed is not None:
        random.seed(args.seed)
    try:
        state = review(json.load(sys.stdin))
    except json.JSONDecodeError as error:
        print(f"error: request is not valid JSON: {error}", file=sys.stderr)
        return 2
    except InputError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"state": state, "row": [state[column] for column in COLUMNS]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
