"""The settings both commands need, and the OAuth user login to the Google Sheets API.

Each setting comes from its environment variable, and its command line flag overrides it.
"""

import argparse
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .errors import Abort
from .sheets import GoogleSheetsClient

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Setting name: (environment variable, flag, description)
SETTINGS = {
    "sheet_id": ("SRT_SHEET_ID", "--sheet-id", "the id of the Google Sheet"),
    "client_secret": (
        "SRT_OAUTH_CLIENT_SECRET",
        "--client-secret",
        "the OAuth client secret file of a desktop app",
    ),
    "token": ("SRT_OAUTH_TOKEN", "--token", "where the OAuth token is cached"),
}


@dataclass(frozen=True)
class Settings:
    sheet_id: str
    client_secret: Path
    token: Path


def add_arguments(parser: argparse.ArgumentParser) -> None:
    for name, (variable, flag, description) in SETTINGS.items():
        parser.add_argument(flag, dest=name, help=f"{description} (default: ${variable})")


def resolve(args: argparse.Namespace, environ: Mapping[str, str]) -> Settings:
    """Read the settings from the flags, else the environment. Report every missing one."""
    values, missing = {}, []
    for name, (variable, flag, _) in SETTINGS.items():
        value = getattr(args, name, None) or environ.get(variable, "")
        if not value:
            missing.append(f"missing {name.replace('_', ' ')}: set {variable} or pass {flag}")
        values[name] = value
    if missing:
        raise Abort("\n".join(missing))
    return Settings(values["sheet_id"], Path(values["client_secret"]), Path(values["token"]))


def connect(settings: Settings) -> GoogleSheetsClient:
    """Log in and return a client for the sheet."""
    from googleapiclient.discovery import build

    service = build("sheets", "v4", credentials=login(settings), cache_discovery=False)
    return GoogleSheetsClient(service, settings.sheet_id)


def login(settings: Settings):
    """Reuse the cached token, refresh it, or open the browser for the Google login."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    credentials = None
    if settings.token.exists():
        credentials = Credentials.from_authorized_user_file(str(settings.token), SCOPES)
    if credentials and credentials.valid:
        return credentials
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    else:
        if not settings.client_secret.exists():
            raise Abort(f"OAuth client secret file not found: {settings.client_secret}")
        flow = InstalledAppFlow.from_client_secrets_file(str(settings.client_secret), SCOPES)
        credentials = flow.run_local_server(port=0)
    settings.token.parent.mkdir(parents=True, exist_ok=True)
    settings.token.write_text(credentials.to_json())
    os.chmod(settings.token, 0o600)
    return credentials
