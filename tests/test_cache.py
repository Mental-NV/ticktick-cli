import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ticktick_cli.cli import app


class _TaskListClient:
    def __init__(self) -> None:
        self.list_projects_calls = 0
        self.get_project_data_calls: list[str] = []

    def list_projects(self) -> list[dict]:
        self.list_projects_calls += 1
        return [
            {"id": "proj-1", "name": "Inbox", "closed": False},
            {"id": "proj-2", "name": "Work", "closed": False},
        ]

    def get_project_data(self, project_id: str) -> dict:
        self.get_project_data_calls.append(project_id)
        return {
            "tasks": [
                {
                    "id": f"task-{project_id}",
                    "title": f"Task {project_id}",
                    "projectId": project_id,
                    "status": 0,
                }
            ]
        }


class _WriteClient:
    def __init__(self) -> None:
        self.created_payloads: list[dict] = []
        self.list_projects_calls = 0

    def list_projects(self) -> list[dict]:
        self.list_projects_calls += 1
        return []

    def create_task(self, payload: dict) -> dict:
        self.created_payloads.append(payload)
        return {"id": "created-1", **payload}


class _CacheOnlyProjectClient:
    def __init__(self) -> None:
        self.created_payloads: list[dict] = []
        self.list_projects_calls = 0

    def list_projects(self) -> list[dict]:
        self.list_projects_calls += 1
        raise AssertionError("project lookup should have been served from cache")

    def create_task(self, payload: dict) -> dict:
        self.created_payloads.append(payload)
        return {"id": "created-1", **payload}


class TestCacheBehavior(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config_dir = Path(self.temp_dir.name)
        self.token_path = self.config_dir / "token.json"
        self.env = {
            "TICKTICK_TOKEN_PATH": str(self.token_path),
            "TICKTICK_CACHE_TTL_SECONDS": "300",
        }

    def _cache_file(self, name: str) -> Path:
        return self.config_dir / "cache" / name

    def _write_cache(self, name: str, data: object, *, fetched_at: float | None = None) -> None:
        path = self._cache_file(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"fetched_at": fetched_at if fetched_at is not None else time.time(), "data": data}),
            encoding="utf-8",
        )

    def test_tasks_list_uses_fresh_cache_on_second_read(self) -> None:
        client = _TaskListClient()
        with patch.dict(os.environ, self.env, clear=False):
            with patch("ticktick_cli.cli.TickTickClient", return_value=client):
                first = self.runner.invoke(app, ["tasks", "list", "--json"])
                second = self.runner.invoke(app, ["tasks", "list", "--json"])

        self.assertEqual(first.exit_code, 0, first.stdout)
        self.assertEqual(second.exit_code, 0, second.stdout)
        self.assertEqual(client.list_projects_calls, 1)
        self.assertEqual(client.get_project_data_calls, ["proj-1", "proj-2"])

    def test_tasks_list_refreshes_stale_cache(self) -> None:
        stale_snapshot = {
            "tasks": [{"id": "stale-task", "title": "Stale", "projectId": "proj-1", "status": 0}],
            "project_names": {"proj-1": "Inbox"},
        }
        self._write_cache("tasks.json", stale_snapshot, fetched_at=time.time() - 301)
        self._write_cache("projects.json", [{"id": "proj-1", "name": "Inbox"}], fetched_at=time.time() - 301)

        client = _TaskListClient()
        with patch.dict(os.environ, self.env, clear=False):
            with patch("ticktick_cli.cli.TickTickClient", return_value=client):
                result = self.runner.invoke(app, ["tasks", "list", "--json"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload[0]["id"], "task-proj-1")
        self.assertEqual(client.list_projects_calls, 1)
        self.assertEqual(client.get_project_data_calls, ["proj-1", "proj-2"])

    def test_tasks_list_recovers_from_corrupt_cache(self) -> None:
        corrupt_path = self._cache_file("tasks.json")
        corrupt_path.parent.mkdir(parents=True, exist_ok=True)
        corrupt_path.write_text("{not valid json", encoding="utf-8")

        client = _TaskListClient()
        with patch.dict(os.environ, self.env, clear=False):
            with patch("ticktick_cli.cli.TickTickClient", return_value=client):
                result = self.runner.invoke(app, ["tasks", "list", "--json"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload[0]["id"], "task-proj-1")
        rebuilt = json.loads(self._cache_file("tasks.json").read_text(encoding="utf-8"))
        self.assertIn("data", rebuilt)

    def test_task_write_invalidates_task_cache(self) -> None:
        self._write_cache("tasks.json", {"tasks": [], "project_names": {}})
        client = _WriteClient()

        with patch.dict(os.environ, self.env, clear=False):
            with patch("ticktick_cli.cli.TickTickClient", return_value=client):
                result = self.runner.invoke(app, ["tasks", "create", "--project", "proj-1", "--title", "Test"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertFalse(self._cache_file("tasks.json").exists())

    def test_project_name_resolution_uses_project_cache(self) -> None:
        self._write_cache(
            "projects.json",
            [{"id": "proj-1", "name": "Work", "closed": False}],
        )
        client = _CacheOnlyProjectClient()

        with patch.dict(os.environ, self.env, clear=False):
            with patch("ticktick_cli.cli.TickTickClient", return_value=client):
                result = self.runner.invoke(app, ["tasks", "create", "--project", "Work", "--title", "From cache"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertEqual(client.list_projects_calls, 0)
        self.assertEqual(client.created_payloads[0]["projectId"], "proj-1")


if __name__ == "__main__":
    unittest.main()
