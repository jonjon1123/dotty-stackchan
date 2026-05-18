"""Async fetchers for weather (wttr.in via curl) and calendar (Google
Calendar via the `gws` CLI). Both side-effect free wrt the cache —
callers (the poll loop) own where the result lands.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo

from .cache import Event, format_event_time

log = logging.getLogger("dotty-behaviour.calendar.fetch")


async def fetch_weather(*, location: str) -> str:
    """Fetch a short weather line from wttr.in. Empty string on failure."""
    if not location:
        return ""
    try:
        proc = await asyncio.create_subprocess_exec(
            "curl", "-s", "-m", "10",
            f"wttr.in/{location}?format=%C+%t+%h+%w",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        text = stdout.decode("utf-8").strip()
        if text and "Unknown" not in text and "Sorry" not in text:
            return text
    except Exception:
        log.warning("weather fetch failed", exc_info=True)
    return ""


async def fetch_calendar_events(
    *,
    calendar_ids: Iterable[str],
    sa_path: str,
    gws_bin: str,
    local_tz: ZoneInfo,
    household_bucket: str,
    person_prefix_re: re.Pattern[str],
) -> list[Event]:
    """Fetch today's events across `calendar_ids` via the `gws` CLI.

    Raises RuntimeError if every configured calendar errors so the
    polling loop can apply exponential backoff. Per-calendar failures
    only log; an empty list is still a valid success.
    """
    cal_ids = [c for c in calendar_ids if c]
    if not cal_ids or not os.path.isfile(sa_path):
        return []
    now = datetime.now(local_tz)
    time_min = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    time_max = now.replace(
        hour=23, minute=59, second=59, microsecond=0
    ).isoformat()
    env = {**os.environ, "GOOGLE_APPLICATION_CREDENTIALS": sa_path}
    all_events: list[Event] = []
    failures = 0
    for cal_id in cal_ids:
        try:
            params = json.dumps({
                "calendarId": cal_id,
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": True,
                "orderBy": "startTime",
                "maxResults": 10,
            })
            proc = await asyncio.create_subprocess_exec(
                gws_bin, "calendar", "events", "list",
                "--params", params,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=env,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            data = json.loads(stdout.decode("utf-8"))
            for item in data.get("items", []):
                raw_summary = item.get("summary", "")
                start_obj = item.get("start", {})
                start_iso = start_obj.get(
                    "dateTime", start_obj.get("date", "")
                )
                if not raw_summary:
                    continue
                m = person_prefix_re.match(raw_summary)
                if m:
                    person = m.group("person")
                    rest = m.group("rest").strip()
                else:
                    person = household_bucket
                    rest = raw_summary.strip()
                all_events.append(Event(
                    person=person,
                    time=format_event_time(start_iso, local_tz=local_tz),
                    summary=rest,
                    start_iso=start_iso,
                    calendar_id=cal_id,
                ))
        except Exception:
            failures += 1
            log.warning(
                "calendar fetch failed cal=%s", cal_id, exc_info=True
            )
    if cal_ids and failures == len(cal_ids):
        raise RuntimeError("all calendar fetches failed")
    all_events.sort(key=lambda e: e["start_iso"])
    return all_events
