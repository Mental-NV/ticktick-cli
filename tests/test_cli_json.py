import json
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from ticktick_cli.cli import app


class _DummyClient:
    def list_projects(self) -> list[dict]:
        return [
            {
                "id": "proj-1",
                "name": "bad\x00name\x1fline\nnext\tcol\x7f",
                "closed": False,
            }
        ]


class TestCliJsonOutput(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_projects_list_json_escapes_control_characters(self) -> None:
        with patch("ticktick_cli.cli._client", return_value=_DummyClient()):
            result = self.runner.invoke(app, ["projects", "list", "--json"])

        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertIn("\\u0000", result.stdout)
        self.assertIn("\\u001f", result.stdout)
        self.assertIn("\\n", result.stdout)
        self.assertIn("\\t", result.stdout)
        self.assertIn("\\u007f", result.stdout)
        self.assertNotIn("\x00", result.stdout)
        self.assertNotIn("\x1f", result.stdout)
        self.assertNotIn("\x7f", result.stdout)

        parsed = json.loads(result.stdout)
        self.assertEqual(parsed[0]["name"], "bad\x00name\x1fline\nnext\tcol\x7f")


if __name__ == "__main__":
    unittest.main()
