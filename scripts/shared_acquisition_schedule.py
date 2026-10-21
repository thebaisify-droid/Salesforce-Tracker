"""Deterministic prospective Tue/Fri 07:15 UK single-acquisition schedule.

Always read-only and independent of GitHub runners' actual start time. The
planned crons are NOT installed as scheduled jobs before safe activation.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
SUMMER = "15 6 * * 2,5"
WINTER = "15 7 * * 2,5"
MAX_DELAY_MINUTES = 120


def due_slot(now: datetime, *, cron: str, attempt: int = 1):
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("Timezone-aware execution time required")
    local = now.astimezone(LONDON)
    if type(attempt) is not int or attempt != 1:
        return {"due": False, "reason": "RETRY_NOT_PERMITTED"}
    if local.weekday() not in (1, 4):
        return {"due": False, "reason": "WRONG_LOCAL_WEEKDAY"}
    intended_local = datetime(local.year, local.month, local.day, 7, 15, tzinfo=LONDON)
    intended_utc = intended_local.astimezone(timezone.utc)
    expected = SUMMER if intended_utc.hour == 6 else WINTER
    if cron != expected:
        return {"due": False, "reason": "WRONG_DST_CRON", "expected": expected}
    delay = now.astimezone(timezone.utc) - intended_utc
    if not timedelta(0) <= delay <= timedelta(minutes=MAX_DELAY_MINUTES):
        return {"due": False, "reason": "OUTSIDE_EXECUTION_WINDOW"}
    slot = sum(date(local.year, local.month, d).weekday() in (1, 4)
               for d in range(1, local.day + 1))
    total = sum(date(local.year, local.month, d).weekday() in (1, 4)
                for d in range(1, monthrange(local.year, local.month)[1] + 1))
    if total > 9 or slot > 9:
        return {"due": False, "reason": "MONTHLY_SCHEDULE_LIMIT"}
    return {"due": True, "status": "PLANNED_ONLY_NO_ACTOR_LAUNCH",
            "slot": slot, "local_time": intended_local.isoformat(),
            "cron": cron, "delayed_minutes": round(delay.total_seconds() / 60, 2)}
