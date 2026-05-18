"""Perception subsystem — event bus, per-device state, caches, snapshot.

The bus accepts events from xiaozhi-server (which relays firmware
`event` frames) and fans them out to subscribers (the 9 consumer
loops + the dashboard SSE feed). Per-device state is mutated in place
by the bus dispatcher based on the event's `name`. Caches store the
output of vision / audio / scene-synthesis loops with TTLs.

The PerceptionState class is the single source of truth for all of
the above. Routes and consumers take it as a dependency rather than
reaching into module globals — keeps the daemon testable in isolation
the same way `bridge/perception/cache.py` already does for snapshots.
"""

from .notability import is_notable_perception
from .state import PerceptionEvent, PerceptionState
from .snapshot import PerceptionSnapshot, snapshot

__all__ = [
    "PerceptionEvent",
    "PerceptionState",
    "PerceptionSnapshot",
    "is_notable_perception",
    "snapshot",
]
