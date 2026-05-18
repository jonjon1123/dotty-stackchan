"""Environment-driven configuration.

Mirrors the env-var surface bridge.py reads, minus the variables tied
to obsolete code paths (ZEROCLAW_BIN, VOICE_LOCAL_PROFILE_KEY, the
smart-mode model-swap inputs, etc.). Loaded once at import time; tests
that need to override should set os.environ before importing
dotty_behaviour.config or use the helpers in tests/.
"""

from __future__ import annotations

import os
from pathlib import Path

# Version stamp surfaced on /health and in startup logs.
VERSION: str = "0.1.0"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# HTTP server
HOST: str = os.environ.get("DOTTY_BEHAVIOUR_HOST", "0.0.0.0")
PORT: int = _env_int("DOTTY_BEHAVIOUR_PORT", 8090)

# Outbound: xiaozhi-server admin endpoints (same-host loopback under
# Unraid's network_mode: host). Empty XIAOZHI_HOST disables dispatch
# the same way bridge.py does today.
XIAOZHI_HOST: str = os.environ.get("XIAOZHI_HOST", "")
XIAOZHI_HTTP_PORT: int = _env_int("XIAOZHI_OTA_PORT", 8003)

# Outbound: llama-swap for narrative LLM (dreams, dance reflections,
# scene synthesis). Mirrors bridge.py's NARRATIVE_LLM_URL.
NARRATIVE_LLM_URL: str = os.environ.get(
    "NARRATIVE_LLM_URL", "http://127.0.0.1:8080/v1"
)
NARRATIVE_MODEL: str = os.environ.get("NARRATIVE_MODEL", "qwen3.6:27b-think")
NARRATIVE_TIMEOUT_SEC: float = _env_float("NARRATIVE_TIMEOUT_SEC", 90.0)

# Filesystem roots — bind-mounted under /var/lib/dotty-behaviour/ in
# the container, /mnt/user/appdata/dotty-behaviour/ on the Unraid host.
STATE_DIR: Path = Path(
    os.environ.get("DOTTY_STATE_DIR", "/var/lib/dotty-behaviour/state")
)
LOG_DIR: Path = Path(
    os.environ.get("CONVO_LOG_DIR", "/var/lib/dotty-behaviour/logs")
)
SECRETS_DIR: Path = Path(
    os.environ.get("DOTTY_SECRETS_DIR", "/var/lib/dotty-behaviour/secrets")
)

# Per-cache TTLs — identical to bridge.py so the snapshot semantics
# don't drift across the cutover.
VISION_CACHE_TTL_SEC: float = _env_float("VISION_CACHE_TTL_SEC", 60.0)
AUDIO_CACHE_TTL_SEC: float = _env_float("AUDIO_CACHE_TTL_SEC", 120.0)
SCENE_SYNTHESIS_AGE_GATE_SEC: float = _env_float(
    "SCENE_SYNTHESIS_AGE_GATE_SEC", 600.0
)

# Perception bus tuning — match bridge.py's tuned defaults.
PERCEPTION_QUEUE_MAX: int = _env_int("PERCEPTION_QUEUE_MAX", 200)
PERCEPTION_RECENT_MAX: int = _env_int("PERCEPTION_RECENT_MAX", 50)
PERCEPTION_STALE_THRESHOLD_SEC: float = _env_float(
    "PERCEPTION_STALE_THRESHOLD_SEC", 300.0
)
