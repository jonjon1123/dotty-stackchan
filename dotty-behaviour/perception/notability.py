"""Notability gate for idle photographer (and any future "should we
write this perception" check).

Cheap, FTS-friendly — token-set Jaccard similarity against the
previous saved description. Above the threshold ≈ same scene as last
time ≈ skip. Lifted from bridge.py's `_is_notable_perception` so the
consumer doesn't bundle its own filtering rules.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"\w+")


def is_notable_perception(
    description: str,
    last_description: str | None,
    *,
    jaccard_threshold: float,
) -> bool:
    """True when ``description`` is worth saving.

    Rules (in order):
      * empty / very-short descriptions are never notable
      * literal "same as before" → never notable
      * no prior description → always notable (first sample)
      * token-set Jaccard vs prior ≥ threshold → not notable
    """
    if not description or len(description) < 20:
        return False
    if "same as before" in description.lower():
        return False
    if not last_description:
        return True
    cur = {t.lower() for t in _TOKEN_RE.findall(description)}
    prev = {t.lower() for t in _TOKEN_RE.findall(last_description)}
    if not cur or not prev:
        return True
    union = cur | prev
    if not union:
        return True
    jaccard = len(cur & prev) / len(union)
    return jaccard < jaccard_threshold
