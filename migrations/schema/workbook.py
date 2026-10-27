"""All tabs of the sheet in the latest schema version, in the order they are created."""

from .applied_steps import APPLIED_STEPS
from .configs import CONFIG
from .fsrs_states import STATE
from .logs import LOG
from .managed_questions import MANAGED_QUESTIONS
from .questions import QUESTIONS

TABS = (QUESTIONS, STATE, LOG, CONFIG, APPLIED_STEPS, MANAGED_QUESTIONS)


def header(name: str) -> list[str]:
    """The header row of the tab called `name`."""
    return next(list(tab.header) for tab in TABS if tab.name == name)
