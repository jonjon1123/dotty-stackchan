#!/usr/bin/env python3
"""Bridge.py /api/voice/memory_log oracle — runs the *exact* Python body+INSERT
that the production endpoint does, then dumps the inserted row as JSON.

Usage:
    python3 turn_log_oracle.py <brain.db> <now-iso> <id-uuid> <user> <assistant>

Outputs a single JSON object on stdout matching the row written to
`memories`. The TS test consumes this and asserts the auto-log path
produces a byte-equal row when given the same (now, id, user, assistant)
seed.

Matches /api/voice/memory_log defaults exactly:
    user[:500], assistant[:1000] (both .strip() first)
    content = f"user: {u} | assistant: {a}"
    category=conversation, namespace=voice, importance=0.3
    session_id=None
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


USER_MAX = 500
ASSISTANT_MAX = 1000


def _voice_memory_log_blocking(
    db: Path, *, user: str, assistant: str, now: str, mem_id: str,
) -> dict | None:
    """Mirrors bridge.py:voice_memory_log + _voice_memory_store_blocking."""
    u = (user or "").strip()[:USER_MAX]
    a = (assistant or "").strip()[:ASSISTANT_MAX]
    if not u and not a:
        return None
    content = f"user: {u} | assistant: {a}"
    if not db.exists():
        return None
    category = "conversation"
    namespace = "voice"
    importance = 0.3
    base_key = f"voice_{category}_{now}_{mem_id[:8]}"
    try:
        conn = sqlite3.connect(str(db), timeout=5)
        try:
            conn.execute(
                """
                INSERT INTO memories
                  (id, key, content, category, namespace,
                   importance, created_at, updated_at, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mem_id, base_key, content.strip(), category, namespace,
                 importance, now, now, None),
            )
            conn.commit()
            cur = conn.execute(
                """
                SELECT id, key, content, category, namespace,
                       importance, created_at, updated_at, session_id
                FROM memories WHERE id = ?
                """,
                (mem_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            cols = ["id", "key", "content", "category", "namespace",
                    "importance", "created_at", "updated_at", "session_id"]
            return dict(zip(cols, row))
        finally:
            conn.close()
    except Exception as e:
        print(f"oracle error: {e}", file=sys.stderr)
        return None


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 5:
        print(
            "usage: turn_log_oracle.py <db> <now> <id> <user> <assistant>",
            file=sys.stderr,
        )
        return 2
    db = Path(args[0])
    row = _voice_memory_log_blocking(
        db, now=args[1], mem_id=args[2], user=args[3], assistant=args[4],
    )
    if row is None:
        print(json.dumps({"ok": False}))
        return 0
    print(json.dumps({"ok": True, "row": row}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
