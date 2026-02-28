from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REDIRECT_URI = "http://localhost:8000/callback"
DEFAULT_TOKEN_PATH = "~/.config/ticktick/token.json"
DEFAULT_TIMEZONE = "Europe/Moscow"


@dataclass(frozen=True)
class Settings:
    client_id: str | None
    client_secret: str | None
    redirect_uri: str
    token_path: Path
    default_tz: str

    @staticmethod
    def from_env() -> "Settings":
        client_id = os.getenv("TICKTICK_CLIENT_ID")
        client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
        redirect_uri = os.getenv("TICKTICK_REDIRECT_URI", DEFAULT_REDIRECT_URI)
        token_path = Path(os.getenv("TICKTICK_TOKEN_PATH", DEFAULT_TOKEN_PATH)).expanduser()
        default_tz = os.getenv("TICKTICK_DEFAULT_TZ", DEFAULT_TIMEZONE)
        return Settings(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            token_path=token_path,
            default_tz=default_tz,
        )
