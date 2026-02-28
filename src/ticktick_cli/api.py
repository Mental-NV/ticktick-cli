from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from .auth import load_token
from .config import Settings

API_BASE_URL = "https://api.ticktick.com/open/v1"


class UnauthorizedError(RuntimeError):
    pass


@dataclass
class TickTickClient:
    settings: Settings

    def _access_token(self) -> str:
        token_data = load_token(self.settings.token_path)
        if not token_data or not token_data.get("access_token"):
            raise UnauthorizedError("Not logged in. Run: tt auth login")
        return token_data["access_token"]

    def request(self, method: str, path: str, *, json_body: dict | None = None) -> Any:
        token = self._access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        url = f"{API_BASE_URL}{path}"
        response = requests.request(
            method,
            url,
            headers=headers,
            data=json.dumps(json_body) if json_body is not None else None,
            timeout=30,
        )
        if response.status_code == 401:
            raise UnauthorizedError("Access token rejected. Run: tt auth login")
        response.raise_for_status()
        if response.text:
            return response.json()
        return None

    def list_projects(self) -> list[dict]:
        return self.request("GET", "/project")

    def get_project_data(self, project_id: str) -> dict:
        return self.request("GET", f"/project/{project_id}/data")

    def create_task(self, payload: dict) -> dict:
        return self.request("POST", "/task", json_body=payload)

    def update_task(self, task_id: str, payload: dict) -> dict:
        return self.request("POST", f"/task/{task_id}", json_body=payload)

    def complete_task(self, project_id: str, task_id: str) -> dict | None:
        return self.request("POST", f"/project/{project_id}/task/{task_id}/complete")

    def delete_task(self, project_id: str, task_id: str) -> dict | None:
        return self.request("DELETE", f"/project/{project_id}/task/{task_id}")
