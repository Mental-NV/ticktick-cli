from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from dateutil import parser

from .dates import ensure_tz


_DURATION_RE = re.compile(r"^(?P<sign>[+-])?(?P<num>\d+)(?P<unit>[smhdw])$", re.IGNORECASE)


@dataclass(frozen=True)
class ReminderParseOptions:
    """How to interpret friendly reminder specs."""

    # If user writes "10m" without sign, assume they mean *before* due time.
    default_before: bool = True


def _to_iso_duration(delta: timedelta) -> str:
    """Convert timedelta to an ISO8601 duration without months/years."""

    total_seconds = int(delta.total_seconds())
    if total_seconds == 0:
        return "PT0S"

    seconds = total_seconds
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    # Prefer weeks when cleanly divisible.
    if days and days % 7 == 0 and hours == minutes == seconds == 0:
        weeks = days // 7
        return f"P{weeks}W"

    parts: list[str] = []
    if days:
        parts.append(f"{days}D")

    time_parts: list[str] = []
    if hours:
        time_parts.append(f"{hours}H")
    if minutes:
        time_parts.append(f"{minutes}M")
    if seconds:
        time_parts.append(f"{seconds}S")

    if time_parts:
        return "P" + "".join(parts) + "T" + "".join(time_parts)
    return "P" + "".join(parts)


def _duration_spec_to_trigger(spec: str, *, options: ReminderParseOptions) -> str:
    m = _DURATION_RE.match(spec.strip())
    if not m:
        raise ValueError(f"Invalid reminder duration spec: '{spec}'")

    sign = m.group("sign")
    num = int(m.group("num"))
    unit = m.group("unit").lower()

    if sign is None:
        sign = "-" if options.default_before else ""
    elif sign == "+":
        sign = ""

    if num == 0:
        duration = "PT0S"
    elif unit == "s":
        duration = f"PT{num}S"
    elif unit == "m":
        duration = f"PT{num}M"
    elif unit == "h":
        duration = f"PT{num}H"
    elif unit == "d":
        duration = f"P{num}D"
    elif unit == "w":
        duration = f"P{num}W"
    else:
        raise ValueError(f"Unknown reminder unit: '{unit}'")

    return f"TRIGGER:{sign}{duration}"


def parse_reminders(
    specs: Iterable[str] | None,
    *,
    due: str | None,
    tzname: str | None,
    options: ReminderParseOptions | None = None,
) -> list[str] | None:
    """Parse reminder specs to TickTick reminder triggers.

    Supported formats:
    - "TRIGGER:..." (passed through)
    - "10m" / "-10m" / "+10m" / "2h" / "1d" / "1w"
        - by default, no-sign means "before" (e.g. 10m -> TRIGGER:-PT10M)
    - "at:2026-03-01T08:50" (absolute time)
        - requires `due` to be provided; converted to relative TRIGGER

    Returns None if `specs` is None.
    """

    if specs is None:
        return None

    options = options or ReminderParseOptions()

    parsed: list[str] = []

    # Pre-parse due datetime if needed for "at:" specs
    due_dt: datetime | None = None
    if any(str(s).strip().lower().startswith("at:") for s in specs):
        if not due:
            raise ValueError("'at:' reminder requires --due")
        due_dt = parser.isoparse(due)
        due_dt = ensure_tz(due_dt, tzname)

    for raw in specs:
        s = str(raw).strip()
        if not s:
            continue

        if s.upper().startswith("TRIGGER:"):
            parsed.append(s)
            continue

        if s.lower().startswith("at:"):
            if due_dt is None:
                raise ValueError("'at:' reminder requires --due")
            when_str = s.split(":", 1)[1].strip()
            when_dt = ensure_tz(parser.isoparse(when_str), tzname)
            delta = when_dt - due_dt

            sign = "" if delta.total_seconds() >= 0 else "-"
            duration = _to_iso_duration(abs(delta))
            parsed.append(f"TRIGGER:{sign}{duration}")
            continue

        parsed.append(_duration_spec_to_trigger(s, options=options))

    return parsed
