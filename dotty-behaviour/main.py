"""dotty-behaviour FastAPI app entrypoint.

Run via uvicorn (`python -m uvicorn main:app …`). The Dockerfile pins
the invocation; in dev tests use ``fastapi.testclient.TestClient(app)``.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

import config
from perception import PerceptionState
from routes import health as health_routes
from routes import perception as perception_routes


# Configure root logger early — uvicorn replaces handlers, this is just
# a fallback for direct-import contexts (pytest, REPL).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
log = logging.getLogger("dotty-behaviour")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("dotty-behaviour starting (version=%s)", config.VERSION)
    log.info(
        "config: port=%d xiaozhi=%s narrative_model=%s state_dir=%s log_dir=%s",
        config.PORT,
        config.XIAOZHI_HOST or "(disabled)",
        config.NARRATIVE_MODEL,
        config.STATE_DIR,
        config.LOG_DIR,
    )

    # Singleton perception state — bus + caches + per-device dicts.
    # Stored on app.state so routes/consumers can retrieve it via
    # FastAPI's Request.app.state.
    app.state.perception = PerceptionState()

    # Filesystem prep — best-effort; missing bind mounts are an
    # operator error but the daemon should not crash before logging it.
    for path in (config.STATE_DIR, config.LOG_DIR):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning("failed to create %s: %s", path, exc)

    log.info("dotty-behaviour ready on port %d", config.PORT)
    try:
        yield
    finally:
        log.info("dotty-behaviour shutting down")


app = FastAPI(
    title="dotty-behaviour",
    version=config.VERSION,
    description=(
        "Unraid-resident behaviour daemon for Dotty: perception event "
        "bus, 9 consumers, vision/audio explain, dashboard, greeter. "
        "Successor to RPi zeroclaw-bridge."
    ),
    lifespan=lifespan,
)
app.include_router(health_routes.router)
app.include_router(perception_routes.router)
