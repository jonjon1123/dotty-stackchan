"""Calendar + weather subsystem — fetch loop + privacy chokepoint.

Lifted from bridge.py with the same privacy contract:
``summarize_for_prompt`` is the *single* place calendar data crosses
into prompt-injection territory, and it strips every ISO timestamp,
email address, and raw calendar id before returning.

The directory is named ``calendar_`` (not ``calendar``) to avoid
shadowing Python's stdlib ``calendar`` module on direct import.
"""

from .cache import (
    CalendarCache,
    Event,
    bucket_by_person,
    format_event_time,
    summarize_for_prompt,
)
from .fetch import fetch_calendar_events, fetch_weather

__all__ = [
    "CalendarCache",
    "Event",
    "bucket_by_person",
    "fetch_calendar_events",
    "fetch_weather",
    "format_event_time",
    "summarize_for_prompt",
]
