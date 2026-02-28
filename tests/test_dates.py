import unittest
from datetime import datetime

from ticktick_cli.dates import format_ticktick_datetime, parse_iso_datetime


class TestDates(unittest.TestCase):
    def test_format_ticktick_datetime_with_tz(self) -> None:
        formatted, tz_used = format_ticktick_datetime("2026-03-01T09:00:00-05:00")
        self.assertEqual(formatted, "2026-03-01T09:00:00-0500")
        self.assertIsNone(tz_used)

    def test_format_ticktick_datetime_apply_tz(self) -> None:
        formatted, tz_used = format_ticktick_datetime("2026-03-01T09:00:00", tzname="America/New_York")
        self.assertEqual(formatted, "2026-03-01T09:00:00-0500")
        self.assertEqual(tz_used, "America/New_York")

    def test_parse_iso_datetime(self) -> None:
        dt = parse_iso_datetime("2026-03-01T09:00:00Z")
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.tzinfo.utcoffset(dt).total_seconds(), 0)


if __name__ == "__main__":
    unittest.main()
