"""Read-only snapshot of Dotty's current perception.

Ported from bridge/perception/cache.py with no semantic changes. The
signature accepts the four cache dicts explicitly (rather than a
PerceptionState instance) so the function stays usable from unit
tests that construct synthetic caches without instantiating the full
state machine — same convention bridge/perception/cache.py already
established.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal


VISION_AGE_GATE_SEC = 60.0
AUDIO_AGE_GATE_SEC = 120.0
SCENE_SYNTH_AGE_GATE_SEC = 600.0
# Identification is "fresh" for this many seconds after the last
# face_recognized event. Spans the natural HuMan-detector flicker so a
# brief drop-out doesn't collapse the snapshot from "identified" to
# "detected" or "off". Mirrors FACE_IDENTITY_TTL_SEC in bridge.py.
FACE_IDENTITY_AGE_GATE_SEC = 30.0


FaceState = Literal["off", "detected", "identified"]


STORY_FRAMING_LINE = (
    "You are inside the story you're telling — not narrating from outside. "
    "Describe what you see, hear, and feel as a character in the story. "
    "Use rich sensory language. Save vivid moments to memory when they happen."
)


@dataclass(frozen=True)
class PerceptionSnapshot:
    state: str
    face: FaceState
    face_id: str | None
    face_mood: str | None
    listening: bool
    last_vision_desc: str | None
    last_vision_age_s: float | None
    last_audio_desc: str | None
    last_audio_age_s: float | None
    scene_synth: str | None
    scene_synth_age_s: float | None

    def to_prompt_block(self) -> str:
        """Format as a `[Current perception]` system-prompt addendum.

        Story mode always emits at least the framing line. Returns
        "" when nothing meaningful is cached and the state has no
        special framing.
        """
        lines: list[str] = []

        if (self.state or "").lower() == "story_time":
            lines.append(STORY_FRAMING_LINE)

        if self.face == "identified" and self.face_id:
            who_line = f"You see {self.face_id} in front of you."
            if self.face_mood:
                who_line += f" They look {self.face_mood}."
            lines.append(who_line)
        elif self.face == "detected":
            who_line = "You see an unrecognised face in front of you."
            if self.face_mood:
                who_line += f" They look {self.face_mood}."
            lines.append(who_line)

        # Prefer the synth sentence over raw vision/audio — the synth
        # loop already merged those signals.
        if self.scene_synth:
            lines.append(self.scene_synth.strip())
        else:
            if self.last_vision_desc:
                lines.append(f"You see: {self.last_vision_desc.strip()}")
            if self.last_audio_desc:
                lines.append(f"You hear: {self.last_audio_desc.strip()}")

        if not lines:
            return ""
        return "[Current perception] " + " ".join(lines) + "\n"


def _age_or_none(wall_ts: Any) -> float | None:
    if not isinstance(wall_ts, (int, float)):
        return None
    return max(0.0, time.time() - float(wall_ts))


def snapshot(
    device_id: str | None,
    *,
    perception_state: dict[str, dict[str, Any]],
    vision_cache: dict[str, dict[str, Any]],
    audio_cache: dict[str, dict[str, Any]],
    scene_synthesis_cache: dict[str, dict[str, Any]],
) -> PerceptionSnapshot:
    """Compose a frozen snapshot from the four perception caches."""
    pstate: dict[str, Any] = (
        perception_state.get(device_id, {}) if device_id else {}
    )

    face: FaceState = "off"
    face_id: str | None = None
    identity = (pstate.get("last_face_id") or "").strip()
    last_recog_age = _age_or_none(pstate.get("last_face_recognized_t"))
    identified_fresh = (
        identity
        and identity != "unknown"
        and last_recog_age is not None
        and last_recog_age <= FACE_IDENTITY_AGE_GATE_SEC
    )
    if identified_fresh:
        face = "identified"
        face_id = identity
    elif pstate.get("face_present"):
        face = "detected"

    raw_mood = (pstate.get("face_mood") or "").strip().lower()
    mood_age = _age_or_none(pstate.get("face_mood_t"))
    mood_fresh = (
        bool(raw_mood)
        and mood_age is not None
        and mood_age <= FACE_IDENTITY_AGE_GATE_SEC
    )
    face_mood = raw_mood if mood_fresh else None
    if face != "identified":
        face_mood = None

    listening = bool(pstate.get("listening"))
    state = pstate.get("current_state") or "idle"

    last_vision_desc: str | None = None
    last_vision_age_s: float | None = None
    if device_id:
        v = vision_cache.get(device_id) or {}
        age = _age_or_none(v.get("wall_ts"))
        desc = (v.get("description") or "").strip()
        if desc and age is not None and age <= VISION_AGE_GATE_SEC:
            last_vision_desc = desc
            last_vision_age_s = age

    last_audio_desc: str | None = None
    last_audio_age_s: float | None = None
    if device_id:
        a = audio_cache.get(device_id) or {}
        age = _age_or_none(a.get("wall_ts"))
        desc = (a.get("description") or "").strip()
        if desc and age is not None and age <= AUDIO_AGE_GATE_SEC:
            last_audio_desc = desc
            last_audio_age_s = age

    # NB: scene-synthesis cache uses `ts_wall` (not `wall_ts`) — both
    # spellings exist in the codebase for historical reasons.
    scene_synth: str | None = None
    scene_synth_age_s: float | None = None
    if device_id:
        s = scene_synthesis_cache.get(device_id) or {}
        age = _age_or_none(s.get("ts_wall"))
        text = (s.get("text") or "").strip()
        if text and age is not None and age <= SCENE_SYNTH_AGE_GATE_SEC:
            scene_synth = text
            scene_synth_age_s = age

    return PerceptionSnapshot(
        state=state,
        face=face,
        face_id=face_id,
        face_mood=face_mood,
        listening=listening,
        last_vision_desc=last_vision_desc,
        last_vision_age_s=last_vision_age_s,
        last_audio_desc=last_audio_desc,
        last_audio_age_s=last_audio_age_s,
        scene_synth=scene_synth,
        scene_synth_age_s=scene_synth_age_s,
    )
