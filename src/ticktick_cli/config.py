from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REDIRECT_URI = "http://localhost:8000/callback"
DEFAULT_TOKEN_PATH = "~/.config/ticktick/token.json"
DEFAULT_TIMEZONE = "Europe/Moscow"
DEFAULT_CACHE_TTL_SECONDS = 300


@dataclass(frozen=True)
class Settings:
    client_id: str | None
    client_secret: str | None
    redirect_uri: str
    token_path: Path
    default_tz: str
    cache_ttl_seconds: int

    @property
    def config_dir(self) -> Path:
        return self.token_path.expanduser().parent

    @property
    def cache_dir(self) -> Path:
        return self.config_dir / "cache"

    @property
    def projects_cache_path(self) -> Path:
        return self.cache_dir / "projects.json"

    @property
    def tasks_cache_path(self) -> Path:
        return self.cache_dir / "tasks.json"

    @staticmethod
    def from_env() -> "Settings":
        client_id = os.getenv("TICKTICK_CLIENT_ID")
        client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
        redirect_uri = os.getenv("TICKTICK_REDIRECT_URI", DEFAULT_REDIRECT_URI)
        token_path = Path(os.getenv("TICKTICK_TOKEN_PATH", DEFAULT_TOKEN_PATH)).expanduser()
        default_tz = os.getenv("TICKTICK_DEFAULT_TZ", DEFAULT_TIMEZONE)
        cache_ttl_seconds_raw = os.getenv("TICKTICK_CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL_SECONDS))
        try:
            cache_ttl_seconds = max(0, int(cache_ttl_seconds_raw))
        except ValueError:
            cache_ttl_seconds = DEFAULT_CACHE_TTL_SECONDS
        return Settings(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            token_path=token_path,
            default_tz=default_tz,
            cache_ttl_seconds=cache_ttl_seconds,
        )
