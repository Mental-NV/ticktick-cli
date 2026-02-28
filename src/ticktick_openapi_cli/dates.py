from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from dateutil import parser, tz

TICKTICK_DT_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def parse_iso_datetime(value: str) -> datetime:
    return parser.isoparse(value)


def ensure_tz(dt: datetime, tzname: str | None) -> datetime:
    if dt.tzinfo is None:
        if tzname:
            tzinfo = tz.gettz(tzname)
        else:
            tzinfo = tz.tzlocal()
        if tzinfo is None:
            raise ValueError(f"Unknown timezone: {tzname}")
        return dt.replace(tzinfo=tzinfo)

    if tzname:
        tzinfo = tz.gettz(tzname)
        if tzinfo is None:
            raise ValueError(f"Unknown timezone: {tzname}")
        return dt.astimezone(tzinfo)

    return dt


def format_ticktick_datetime(
    value: str,
    *,
    tzname: str | None = None,
    force_tz: bool = False,
) -> tuple[str, str | None]:
    """Format date/time to TickTick OpenAPI format.

    - If `value` includes a timezone offset (aware datetime) and `force_tz=False`, we keep it.
    - If `value` is naive and `tzname` is provided, we attach that timezone.
    - If `force_tz=True` and `tzname` is provided, we convert to that timezone.

    Returns: (formatted_datetime, tz_used_for_payload)
    """

    dt = parse_iso_datetime(value)

    tz_used: str | None = None
    if dt.tzinfo is None:
        # Apply tz when input is naive.
        dt = ensure_tz(dt, tzname)
        tz_used = tzname
    else:
        # Input already has tz info.
        if force_tz and tzname:
            dt = ensure_tz(dt, tzname)
            tz_used = tzname

    return dt.strftime(TICKTICK_DT_FORMAT), tz_used


def is_today(dt: datetime, now: datetime) -> bool:
    return dt.date() == now.date()


def is_overdue(dt: datetime, now: datetime) -> bool:
    return dt < now


def is_within_next_days(dt: datetime, now: datetime, days: int) -> bool:
    return now <= dt <= (now + timedelta(days=days))


def parse_due_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return parser.isoparse(value)
    except (ValueError, TypeError):
        return None


def normalize_due_for_compare(dt: datetime, now: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=now.tzinfo or timezone.utc)
    return dt.astimezone(now.tzinfo or timezone.utc)


def filter_tasks_by_due(
    tasks: Iterable[dict],
    *,
    today: bool = False,
    overdue: bool = False,
    next_days: int | None = None,
    now: datetime | None = None,
) -> list[dict]:
    if not any([today, overdue, next_days is not None]):
        return list(tasks)

    now = now or datetime.now(tz.tzlocal())
    filtered: list[dict] = []
    for task in tasks:
        due_raw = task.get("dueDate")
        due_dt = parse_due_date(due_raw) if due_raw else None
        if due_dt is None:
            continue
        due_dt = normalize_due_for_compare(due_dt, now)
        if today and is_today(due_dt, now):
            filtered.append(task)
            continue
        if overdue and is_overdue(due_dt, now):
            filtered.append(task)
            continue
        if next_days is not None and is_within_next_days(due_dt, now, next_days):
            filtered.append(task)
    return filtered
