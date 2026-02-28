from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

from .config import Settings

AUTH_URL = "https://ticktick.com/oauth/authorize"
TOKEN_URL = "https://ticktick.com/oauth/token"


@dataclass
class Token:
    access_token: str
    token_type: str | None
    refresh_token: str | None
    scope: str | None
    expires_in: int | None
    obtained_at: int

    @staticmethod
    def from_response(data: dict[str, Any]) -> "Token":
        return Token(
            access_token=data.get("access_token"),
            token_type=data.get("token_type"),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            expires_in=data.get("expires_in"),
            obtained_at=int(time.time()),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
            "expires_in": self.expires_in,
            "obtained_at": self.obtained_at,
        }


class AuthCallbackHandler(BaseHTTPRequestHandler):
    server_version = "TickTickOAuth/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        self.server.code = code  # type: ignore[attr-defined]
        self.server.state = state  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h3>Authorization received.</h3>You can close this window.</body></html>"
        )

    def log_message(self, format: str, *args: Any) -> None:
        return


class OAuthCallbackServer:
    def __init__(self, redirect_uri: str):
        parsed = urlparse(redirect_uri)
        if not parsed.hostname or not parsed.port:
            raise ValueError("Redirect URI must include host and port.")
        self.host = parsed.hostname
        self.port = parsed.port
        self.path = parsed.path or "/"
        self._server = HTTPServer((self.host, self.port), AuthCallbackHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def wait_for_code(self, timeout: int = 300) -> tuple[str | None, str | None]:
        start = time.time()
        while time.time() - start < timeout:
            code = getattr(self._server, "code", None)
            state = getattr(self._server, "state", None)
            if code:
                return code, state
            time.sleep(0.2)
        return None, None

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def build_auth_url(settings: Settings, state: str) -> str:
    scope = "tasks:read tasks:write"
    return (
        f"{AUTH_URL}?response_type=code&client_id={settings.client_id}"
        f"&redirect_uri={settings.redirect_uri}&scope={scope}&state={state}"
    )


def exchange_code(settings: Settings, code: str) -> Token:
    if not settings.client_id or not settings.client_secret:
        raise RuntimeError("Missing TICKTICK_CLIENT_ID or TICKTICK_CLIENT_SECRET.")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.redirect_uri,
    }
    response = requests.post(
        TOKEN_URL,
        data=data,
        auth=(settings.client_id, settings.client_secret),
        timeout=30,
    )
    response.raise_for_status()
    token_data = response.json()
    token = Token.from_response(token_data)
    if not token.access_token:
        raise RuntimeError("Token response missing access_token.")
    return token


def save_token(path: Path, token: Token) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(token.to_json(), handle, indent=2)


def load_token(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def delete_token(path: Path) -> bool:
    if path.exists():
        path.unlink()
        return True
    return False


def login(settings: Settings, timeout: int = 300) -> Token:
    if not settings.client_id:
        raise RuntimeError("Missing TICKTICK_CLIENT_ID.")
    state = secrets.token_urlsafe(16)
    server = OAuthCallbackServer(settings.redirect_uri)
    server.start()
    auth_url = build_auth_url(settings, state)
    print("Open the following URL in your browser to authorize:")
    print(auth_url)
    code = None
    try:
        code, returned_state = server.wait_for_code(timeout=timeout)
        if not code:
            raise RuntimeError("Timed out waiting for authorization code.")
        if returned_state and returned_state != state:
            raise RuntimeError("State mismatch in OAuth response.")
    finally:
        server.stop()
    token = exchange_code(settings, code)
    save_token(settings.token_path, token)
    return token
