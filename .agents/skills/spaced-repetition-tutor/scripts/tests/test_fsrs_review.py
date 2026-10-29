"""Check the skill's FSRS script against py-fsrs 6.3.2, the dev dependency it vendors.

The script runs as a subprocess with `-I -S`, so it sees neither the installed py-fsrs nor any
other site package: a passing test also shows that it needs the standard library only.
"""

import json
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fsrs
import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "fsrs_review.py"
REVIEW_TIME = "2026-10-26T14:30:00Z"
WEIGHTS = [*fsrs.scheduler.DEFAULT_PARAMETERS[:20], 0.2]
WEIGHTS[0], WEIGHTS[8] = 0.5, 1.5


def run(*args, request=None):
    return subprocess.run(
        [sys.executable, "-I", "-S", str(SCRIPT), *args],
        input=None if request is None else json.dumps(request),
        capture_output=True,
        text=True,
        check=False,
    )


def review(request, seed=None):
    result = run("review", *([] if seed is None else ["--seed", str(seed)]), request=request)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def utc(text):
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def cell(value):
    if value is None:
        return ""
    return repr(value) if isinstance(value, float) else str(value)


def expected(card, rating, scheduler, seed=None):
    if seed is not None:
        random.seed(seed)
    card, _ = scheduler.review_card(card, rating, review_datetime=utc(REVIEW_TIME))
    return {
        "fsrs_state": card.state.name.lower(),
        "step": cell(card.step),
        "stability": cell(card.stability),
        "difficulty": cell(card.difficulty),
        "due": card.due.isoformat().replace("+00:00", "Z"),
        "last_review": card.last_review.isoformat().replace("+00:00", "Z"),
    }


STATES = {
    "new": (None, fsrs.Card(card_id=1, due=utc(REVIEW_TIME))),
    "learning step 1": (
        {"fsrs_state": "learning", "step": "1", "stability": "2.3065", "difficulty": "2.1181",
         "due": "2026-10-26T14:20:00Z", "last_review": "2026-10-26T14:10:00Z",
         "reps": "1", "lapses": "0"},
        fsrs.Card(card_id=1, state=fsrs.State.Learning, step=1, stability=2.3065,
                  difficulty=2.1181, due=utc("2026-10-26T14:20:00Z"),
                  last_review=utc("2026-10-26T14:10:00Z")),
    ),
    "review, overdue": (
        {"fsrs_state": "review", "step": "", "stability": "5.2", "difficulty": "6.1",
         "due": "2026-10-20T10:00:00+02:00", "last_review": "2026-10-15T10:00:00Z",
         "reps": "4", "lapses": "1"},
        fsrs.Card(card_id=1, state=fsrs.State.Review, stability=5.2, difficulty=6.1,
                  due=utc("2026-10-20T08:00:00Z"), last_review=utc("2026-10-15T10:00:00Z")),
    ),
    "relearning": (
        {"fsrs_state": "relearning", "step": "0", "stability": "1.06", "difficulty": "8.7",
         "due": "2026-10-26T14:20:00Z", "last_review": "2026-10-26T14:10:00Z",
         "reps": "5", "lapses": "1"},
        fsrs.Card(card_id=1, state=fsrs.State.Relearning, step=0, stability=1.06,
                  difficulty=8.7, due=utc("2026-10-26T14:20:00Z"),
                  last_review=utc("2026-10-26T14:10:00Z")),
    ),
}  # fmt: skip

CONFIGS = {
    "defaults": ({}, fsrs.Scheduler()),
    "every key": (
        {"desired_retention": "0.85", "fsrs_weights": ",".join(map(repr, WEIGHTS)),
         "learning_steps": "0.5, 5, 30", "relearning_steps": "", "maximum_interval": "30",
         "enable_fuzzing": "FALSE", "schema_version": "1"},
        fsrs.Scheduler(parameters=WEIGHTS, desired_retention=0.85,
                       learning_steps=[timedelta(minutes=0.5), timedelta(minutes=5),
                                       timedelta(minutes=30)],
                       relearning_steps=[], maximum_interval=30, enable_fuzzing=False),
    ),
}  # fmt: skip


@pytest.mark.parametrize("config_name", CONFIGS)
@pytest.mark.parametrize("state_name", STATES)
@pytest.mark.parametrize("rating", [1, 2, 3, 4])
def test_review_matches_py_fsrs(state_name, rating, config_name):
    row, card = STATES[state_name]
    config, scheduler = CONFIGS[config_name]
    request = {"question_id": "git-rebase", "state": row, "rating": rating,
               "review_time": REVIEW_TIME, "config": config}  # fmt: skip

    answer = review(request, seed=7)

    want = expected(card, fsrs.Rating(rating), scheduler, seed=7)
    got = {key: answer["state"][key] for key in want}
    assert got == want
    assert answer["state"]["question_id"] == "git-rebase"


def test_fuzzed_intervals_match_py_fsrs():
    row, card = STATES["review, overdue"]
    request = {"question_id": "q", "state": row, "rating": 3, "review_time": REVIEW_TIME}
    for seed in range(5):
        want = expected(card, fsrs.Rating.Good, fsrs.Scheduler(), seed=seed)
        assert review(request, seed=seed)["state"]["due"] == want["due"]


@pytest.mark.parametrize(
    ("state_name", "rating", "reps", "lapses"),
    [
        ("new", 1, "1", "0"),
        ("learning step 1", 1, "2", "0"),
        ("review, overdue", 1, "5", "2"),
        ("review, overdue", 3, "5", "1"),
        ("relearning", 1, "6", "1"),
    ],
)
def test_reps_and_lapses(state_name, rating, reps, lapses):
    row, _ = STATES[state_name]
    request = {"question_id": "q", "state": row, "rating": rating, "review_time": REVIEW_TIME}
    state = review(request)["state"]
    assert (state["reps"], state["lapses"]) == (reps, lapses)


def test_row_is_in_column_order():
    answer = review({"question_id": "q", "state": None, "rating": 3, "review_time": REVIEW_TIME})
    columns = ["question_id", "fsrs_state", "step", "stability", "difficulty", "due",
               "last_review", "reps", "lapses"]  # fmt: skip
    assert list(answer["state"]) == columns
    assert answer["row"] == [answer["state"][column] for column in columns]


def test_new_state_row_is_a_question_never_reviewed():
    new_row = {"fsrs_state": "new", "due": REVIEW_TIME, "reps": "0", "lapses": "0"}
    with_row = {"question_id": "q", "state": new_row, "rating": 3, "review_time": REVIEW_TIME}
    without_row = {**with_row, "state": None}
    assert review(with_row) == review(without_row)


def test_now_prints_utc_without_fraction():
    result = run("now")
    assert result.returncode == 0
    now = result.stdout.strip()
    assert now.endswith("Z") and "." not in now
    assert abs(datetime.now(timezone.utc) - utc(now.replace("Z", "+00:00"))) < timedelta(minutes=1)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"rating": 5}, "rating: not 1, 2, 3 or 4"),
        ({"question_id": ""}, "question_id: missing"),
        ({"review_time": "2026-10-26T14:30:00"}, "review_time: timestamp has no time zone"),
        ({"config": {"colour": "red"}}, "config: unknown key 'colour'"),
        ({"config": {"desired_retention": "1"}}, "desired_retention: must be greater than 0"),
        ({"config": {"fsrs_weights": "1,2"}}, "fsrs_weights: 2 numbers, expected 21"),
        ({"config": {"fsrs_weights": ",".join(["0.5"] * 21)}}, "fsrs_weights: One or more"),
        ({"config": {"learning_steps": "1,0"}}, "learning_steps: every step must be greater"),
        ({"config": {"maximum_interval": "0"}}, "maximum_interval: must be 1 or more"),
        ({"config": {"enable_fuzzing": "yes"}}, "enable_fuzzing: not TRUE or FALSE"),
        ({"state": {"fsrs_state": "done"}}, "fsrs_state: not one of"),
        ({"state": {"fsrs_state": "review", "due": REVIEW_TIME}}, "required in the review state"),
    ],
)
def test_bad_requests_exit_2_with_a_message(change, message):
    request = {"question_id": "q", "state": None, "rating": 3, "review_time": REVIEW_TIME}
    result = run("review", request={**request, **change})
    assert result.returncode == 2
    assert message in result.stderr
    assert result.stdout == ""


def test_invalid_json_exits_2():
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(SCRIPT), "review"],
        input="{", capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert result.returncode == 2
    assert "not valid JSON" in result.stderr
