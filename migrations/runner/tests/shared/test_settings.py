import argparse
from pathlib import Path

import pytest

from migrations.runner.shared.errors import Abort
from migrations.runner.shared.settings import Settings, add_arguments, resolve

ENV = {
    "SRT_SHEET_ID": "env-sheet",
    "SRT_OAUTH_CLIENT_SECRET": "env-secret.json",
    "SRT_OAUTH_TOKEN": "env-token.json",
}


def parse(*argv: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    return parser.parse_args(argv)


def test_settings_come_from_the_environment():
    assert resolve(parse(), ENV) == Settings(
        "env-sheet", Path("env-secret.json"), Path("env-token.json")
    )


def test_flags_override_the_environment():
    args = parse("--sheet-id", "flag-sheet", "--token", "flag-token.json")

    settings = resolve(args, ENV)

    assert settings.sheet_id == "flag-sheet"
    assert settings.client_secret == Path("env-secret.json")
    assert settings.token == Path("flag-token.json")


@pytest.mark.parametrize(
    ("variable", "flag"),
    [
        ("SRT_SHEET_ID", "--sheet-id"),
        ("SRT_OAUTH_CLIENT_SECRET", "--client-secret"),
        ("SRT_OAUTH_TOKEN", "--token"),
    ],
)
def test_missing_setting_names_variable_and_flag(variable: str, flag: str):
    environ = {**ENV, variable: ""}

    with pytest.raises(Abort) as raised:
        resolve(parse(), environ)

    assert str(raised.value).endswith(f"set {variable} or pass {flag}")
