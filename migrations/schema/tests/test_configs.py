import pytest

from migrations.schema.configs import CONFIG, DEFAULT_FSRS_WEIGHTS, Config
from migrations.schema.shared.tabs import RowError


def test_header_and_keys_match_the_spec():
    rows = CONFIG.to_rows(Config())
    assert rows[0] == ["key", "value"]
    assert [row[0] for row in rows[1:]] == [
        "schema_version",
        "desired_retention",
        "fsrs_weights",
        "learning_steps",
        "relearning_steps",
        "maximum_interval",
        "enable_fuzzing",
    ]


def test_defaults():
    config = Config()
    assert config.schema_version == 1
    assert config.desired_retention == 0.9
    assert config.fsrs_weights == list(DEFAULT_FSRS_WEIGHTS)
    assert len(config.fsrs_weights) == 21
    assert config.learning_steps == [1, 10]
    assert config.relearning_steps == [10]
    assert config.maximum_interval == 36500
    assert config.enable_fuzzing is True


@pytest.mark.parametrize(
    "config",
    [
        Config(),
        Config(schema_version=2, desired_retention=0.85, fsrs_weights=[0.5] * 21),
        Config(
            learning_steps=[0.5, 5, 30],
            relearning_steps=[],
            maximum_interval=30,
            enable_fuzzing=False,
        ),
    ],
)
def test_round_trip(config):
    assert CONFIG.from_rows(CONFIG.to_rows(config)) == config


def test_cell_formats():
    rows = CONFIG.to_rows(Config())
    assert rows[1:3] == [["schema_version", "1"], ["desired_retention", "0.9"]]
    assert rows[3][1].startswith("0.212,1.2931,")
    assert rows[4:] == [
        ["learning_steps", "1.0,10.0"],
        ["relearning_steps", "10.0"],
        ["maximum_interval", "36500"],
        ["enable_fuzzing", "TRUE"],
    ]


def test_scheduler_keys_read_the_documented_formats():
    rows = [
        ["key", "value"],
        ["learning_steps", "1, 10, 60"],
        ["relearning_steps", ""],
        ["maximum_interval", "365"],
        ["enable_fuzzing", "false"],
    ]
    config = CONFIG.from_rows(rows)
    assert config.learning_steps == [1, 10, 60]
    assert config.relearning_steps == []
    assert config.maximum_interval == 365
    assert config.enable_fuzzing is False


def test_missing_keys_take_their_defaults():
    assert CONFIG.from_rows([["key", "value"]]) == Config()


@pytest.mark.parametrize(
    ("rows", "row", "column", "message"),
    [
        ([["schema_version", "one"]], 2, "value", "not an integer"),
        ([["desired_retention", "1.0"]], 2, "value", "less than 1"),
        ([["fsrs_weights", "1,2,3"]], 2, "value", "at least 21"),
        ([["fsrs_weights", "1,x"]], 2, "value", "not a number"),
        ([["learning_steps", "1,0"]], 2, "value", "greater than 0"),
        ([["relearning_steps", "ten"]], 2, "value", "not a number"),
        ([["maximum_interval", "0"]], 2, "value", "greater than or equal to 1"),
        ([["maximum_interval", "1.5"]], 2, "value", "not an integer"),
        ([["enable_fuzzing", "yes"]], 2, "value", "not TRUE or FALSE"),
        ([["schema_version", "1"], ["colour", "red"]], 3, "key", "unknown key"),
        ([["schema_version", "1"], ["schema_version", "2"]], 3, "key", "duplicate key"),
        ([["schema_version", "1", "extra"]], 2, None, "3 cells, expected 2"),
    ],
)
def test_malformed_rows(rows, row, column, message):
    with pytest.raises(RowError) as raised:
        CONFIG.from_rows([["key", "value"], *rows])

    error = raised.value
    assert (error.tab, error.row, error.column) == ("config", row, column)
    assert message in error.message
