"""GET /api/calendar/today — lift of bridge.py's calendar_today.

Routes through summarize_for_prompt so the response carries the same
privacy guarantees as prompt injection (no ISO timestamps, no email
addresses, no raw calendar IDs).
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Request

import config
from calendar_ import CalendarCache, summarize_for_prompt
from calendar_.poll import refresh_if_stale


def get_calendar_cache(request: Request) -> CalendarCache:
    cache = getattr(request.app.state, "calendar_cache", None)
    if cache is None:
        raise RuntimeError("CalendarCache not attached to app.state")
    return cache


def get_person_prefix_re(request: Request) -> re.Pattern[str]:
    rx = getattr(request.app.state, "calendar_person_prefix_re", None)
    if rx is None:
        raise RuntimeError(
            "calendar_person_prefix_re not attached to app.state"
        )
    return rx


router = APIRouter()


@router.get("/api/calendar/today")
async def calendar_today(
    person: str | None = None,
    include_household: bool = True,
    cache: CalendarCache = Depends(get_calendar_cache),
    rx: re.Pattern[str] = Depends(get_person_prefix_re),
) -> dict:
    """LAN endpoint for today's calendar events.

    Triggers a lazy refresh if cache is stale or the day rolled.
    Returns the same shape as bridge.py so existing callers see no
    difference across the cutover.
    """
    await refresh_if_stale(
        cache,
        weather_location=config.WEATHER_LOCATION,
        weather_ttl_sec=config.WEATHER_TTL_SEC,
        calendar_ids=config.CALENDAR_IDS,
        calendar_ttl_sec=config.CALENDAR_TTL_SEC,
        calendar_sa_path=config.CALENDAR_SA_PATH,
        gws_bin=config.GWS_BIN,
        local_tz=config.LOCAL_TZ,
        household_bucket=config.CALENDAR_HOUSEHOLD_BUCKET,
        person_prefix_re=rx,
    )
    cleaned = summarize_for_prompt(
        cache.events,
        person=person,
        include_household=include_household,
        household_bucket=config.CALENDAR_HOUSEHOLD_BUCKET,
    )
    return {
        "ok": True,
        "date": cache.calendar_date,
        "fetched": cache.calendar_fetched_perf,
        "consecutive_failures": cache.calendar_failures,
        "person": person,
        "include_household": include_household,
        "events": cleaned,
        "count": len(cleaned),
    }
