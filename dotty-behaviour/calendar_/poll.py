"""Background refresh loop for weather + calendar caches.

Runs alongside the perception consumers; lifespan starts it and
cancels on shutdown. Lazy callers can also trigger a refresh on demand
via `refresh_if_stale` — that's what the HTTP route does so the cache
is always at most one TTL window stale on the request path.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from time import perf_counter
from zoneinfo import ZoneInfo

from .cache import CalendarCache
from .fetch import fetch_calendar_events, fetch_weather

log = logging.getLogger("dotty-behaviour.calendar.poll")


# Exponential-backoff schedule (seconds) on consecutive failures.
# After exhaustion the loop sits at the last entry until a success
# resets the counter.
BACKOFF_SCHEDULE_SEC = (60.0, 120.0, 300.0, 600.0)


async def refresh_if_stale(
    cache: CalendarCache,
    *,
    weather_location: str,
    weather_ttl_sec: float,
    calendar_ids: tuple[str, ...],
    calendar_ttl_sec: float,
    calendar_sa_path: str,
    gws_bin: str,
    local_tz: ZoneInfo,
    household_bucket: str,
    person_prefix_re: re.Pattern[str],
) -> None:
    """Lazy refresh — re-fetches weather + calendar if either has aged
    past its TTL or the local day has rolled."""
    now = perf_counter()
    if now - cache.weather_fetched_perf > weather_ttl_sec:
        text = await fetch_weather(location=weather_location)
        cache.set_weather(text, now_perf=now)

    if not calendar_ids:
        return

    today = datetime.now(local_tz).strftime("%Y-%m-%d")
    date_rolled = cache.calendar_date != today
    ttl_expired = now - cache.calendar_fetched_perf > calendar_ttl_sec
    if date_rolled:
        cache.flush_for_new_day(date_str=today)
    if date_rolled or ttl_expired:
        try:
            events = await fetch_calendar_events(
                calendar_ids=calendar_ids,
                sa_path=calendar_sa_path,
                gws_bin=gws_bin,
                local_tz=local_tz,
                household_bucket=household_bucket,
                person_prefix_re=person_prefix_re,
            )
            cache.set_events(events, date_str=today, now_perf=now)
        except Exception:
            cache.calendar_failures += 1
            log.warning(
                "calendar refresh failed (consecutive=%d)",
                cache.calendar_failures,
                exc_info=True,
            )


class CalendarPollLoop:
    """Periodic background poller. Backoff escalates on consecutive
    failures; reset to base interval on the next successful fetch."""

    def __init__(
        self,
        cache: CalendarCache,
        *,
        weather_location: str,
        weather_ttl_sec: float,
        calendar_ids: tuple[str, ...],
        calendar_ttl_sec: float,
        calendar_sa_path: str,
        gws_bin: str,
        local_tz: ZoneInfo,
        household_bucket: str,
        person_prefix_re: re.Pattern[str],
        base_interval_sec: float = 60.0,
    ) -> None:
        self._cache = cache
        self._weather_location = weather_location
        self._weather_ttl_sec = weather_ttl_sec
        self._calendar_ids = calendar_ids
        self._calendar_ttl_sec = calendar_ttl_sec
        self._calendar_sa_path = calendar_sa_path
        self._gws_bin = gws_bin
        self._local_tz = local_tz
        self._household_bucket = household_bucket
        self._person_prefix_re = person_prefix_re
        self._base_interval_sec = base_interval_sec

    def _sleep_seconds(self) -> float:
        failures = self._cache.calendar_failures
        if failures <= 0:
            return self._base_interval_sec
        idx = min(failures - 1, len(BACKOFF_SCHEDULE_SEC) - 1)
        return BACKOFF_SCHEDULE_SEC[idx]

    async def run(self) -> None:
        log.info(
            "calendar poll loop started "
            "(weather=%s calendars=%d base_interval=%.0fs)",
            self._weather_location,
            len(self._calendar_ids),
            self._base_interval_sec,
        )
        try:
            while True:
                try:
                    await refresh_if_stale(
                        self._cache,
                        weather_location=self._weather_location,
                        weather_ttl_sec=self._weather_ttl_sec,
                        calendar_ids=self._calendar_ids,
                        calendar_ttl_sec=self._calendar_ttl_sec,
                        calendar_sa_path=self._calendar_sa_path,
                        gws_bin=self._gws_bin,
                        local_tz=self._local_tz,
                        household_bucket=self._household_bucket,
                        person_prefix_re=self._person_prefix_re,
                    )
                except Exception:
                    log.exception("calendar poll loop iteration failed")
                await asyncio.sleep(self._sleep_seconds())
        except asyncio.CancelledError:
            log.info("calendar poll loop cancelled")
            raise
