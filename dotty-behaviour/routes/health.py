"""Health endpoint — Docker healthcheck target."""

from __future__ import annotations

from fastapi import APIRouter

from config import VERSION

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "dotty-behaviour", "version": VERSION}
