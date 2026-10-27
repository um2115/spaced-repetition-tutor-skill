from datetime import UTC, datetime

import pytest

from migrations.schema.applied_steps import APPLIED_STEPS, AppliedStep
from migrations.schema.shared.tabs import RowError

STEP = AppliedStep(
    version=2, name="add_hints", applied_at=datetime(2026, 10, 26, 14, 30, tzinfo=UTC)
)


def test_header_matches_the_spec():
    assert APPLIED_STEPS.name == "migrations"
    assert APPLIED_STEPS.header == ["version", "name", "applied_at"]


def test_row_round_trip():
    row = APPLIED_STEPS.to_row(STEP)

    assert row == ["2", "add_hints", "2026-10-26T14:30:00Z"]
    assert APPLIED_STEPS.from_rows(APPLIED_STEPS.to_rows([STEP])) == [STEP]


@pytest.mark.parametrize(
    ("row", "column", "message"),
    [
        (["1", "base", "2026-10-26T14:30:00Z"], "version", "greater than or equal to 2"),
        (["2", " ", "2026-10-26T14:30:00Z"], "name", "must not be empty"),
        (["2", "x", "yesterday"], "applied_at", "not an ISO 8601 timestamp"),
    ],
)
def test_malformed_row(row, column, message):
    with pytest.raises(RowError) as raised:
        APPLIED_STEPS.from_rows([APPLIED_STEPS.header, row])

    assert (raised.value.tab, raised.value.row, raised.value.column) == ("migrations", 2, column)
    assert message in raised.value.message
