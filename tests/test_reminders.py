import unittest

from ticktick_openapi_cli.reminders import parse_reminders


class TestReminders(unittest.TestCase):
    def test_duration_defaults_to_before(self) -> None:
        r = parse_reminders(["10m"], due="2026-03-01T10:00:00", tzname="Europe/Moscow")
        self.assertEqual(r, ["TRIGGER:-PT10M"])

    def test_duration_explicit_plus(self) -> None:
        r = parse_reminders(["+10m"], due="2026-03-01T10:00:00", tzname="Europe/Moscow")
        self.assertEqual(r, ["TRIGGER:PT10M"])

    def test_at_datetime(self) -> None:
        r = parse_reminders(
            ["at:2026-03-01T09:50:00"],
            due="2026-03-01T10:00:00",
            tzname="Europe/Moscow",
        )
        self.assertEqual(r, ["TRIGGER:-PT10M"])


if __name__ == "__main__":
    unittest.main()
