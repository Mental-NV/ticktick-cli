from __future__ import annotations

import json
import random
import time
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
    max_retries: int = 3
    backoff_base_s: float = 0.5

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

        retriable_status = {429, 500, 502, 503, 504}
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    data=json.dumps(json_body) if json_body is not None else None,
                    timeout=30,
                )
            except requests.RequestException as exc:  # network / timeout
                last_exc = exc
                if attempt >= self.max_retries:
                    raise
                sleep_s = self.backoff_base_s * (2**attempt) + random.random() * 0.2
                time.sleep(sleep_s)
                continue

            if response.status_code == 401:
                raise UnauthorizedError("Access token rejected. Run: tt auth login")

            if response.status_code in retriable_status and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        sleep_s = float(retry_after)
                    except ValueError:
                        sleep_s = self.backoff_base_s * (2**attempt)
                else:
                    sleep_s = self.backoff_base_s * (2**attempt) + random.random() * 0.2
                time.sleep(sleep_s)
                continue

            response.raise_for_status()
            if response.text:
                return response.json()
            return None

        # Should be unreachable
        if last_exc:
            raise last_exc
        raise RuntimeError("Request failed after retries")

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
