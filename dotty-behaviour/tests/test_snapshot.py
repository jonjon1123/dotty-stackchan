"""Smoke tests for snapshot() — equivalent in shape to the existing
bridge/perception tests, just rewritten against the ported module so a
regression in the lift surfaces here rather than in bridge land."""

from __future__ import annotations

import time

from perception.snapshot import (
    FACE_IDENTITY_AGE_GATE_SEC,
    PerceptionSnapshot,
    snapshot,
)


def _empty_caches():
    return {"state": {}, "vision": {}, "audio": {}, "scene": {}}


def test_snapshot_empty_returns_idle_off() -> None:
    c = _empty_caches()
    s = snapshot(
        "dev-1",
        perception_state=c["state"],
        vision_cache=c["vision"],
        audio_cache=c["audio"],
        scene_synthesis_cache=c["scene"],
    )
    assert s.state == "idle"
    assert s.face == "off"
    assert s.to_prompt_block() == ""


def test_snapshot_identified_when_recent_recognition() -> None:
    now = time.time()
    pstate = {
        "dev-1": {
            "last_face_id": "brett",
            "last_face_recognized_t": now - 5.0,
            "face_present": True,
            "current_state": "idle",
        }
    }
    s = snapshot(
        "dev-1",
        perception_state=pstate,
        vision_cache={},
        audio_cache={},
        scene_synthesis_cache={},
    )
    assert s.face == "identified"
    assert s.face_id == "brett"
    assert "brett" in s.to_prompt_block()


def test_snapshot_falls_back_to_detected_when_stale() -> None:
    pstate = {
        "dev-1": {
            "last_face_id": "brett",
            "last_face_recognized_t": time.time() - (
                FACE_IDENTITY_AGE_GATE_SEC + 10.0
            ),
            "face_present": True,
        }
    }
    s = snapshot(
        "dev-1",
        perception_state=pstate,
        vision_cache={},
        audio_cache={},
        scene_synthesis_cache={},
    )
    assert s.face == "detected"
    assert s.face_id is None


def test_snapshot_story_mode_emits_framing_even_when_otherwise_empty() -> None:
    pstate = {"dev-1": {"current_state": "story_time"}}
    s = snapshot(
        "dev-1",
        perception_state=pstate,
        vision_cache={},
        audio_cache={},
        scene_synthesis_cache={},
    )
    block = s.to_prompt_block()
    assert block.startswith("[Current perception] ")
    assert "story" in block.lower()


def test_snapshot_prefers_scene_synth_over_raw_vision_audio() -> None:
    now = time.time()
    s = snapshot(
        "dev-1",
        perception_state={"dev-1": {"current_state": "idle"}},
        vision_cache={
            "dev-1": {"description": "a chair", "wall_ts": now}
        },
        audio_cache={
            "dev-1": {"description": "music", "wall_ts": now}
        },
        scene_synthesis_cache={
            "dev-1": {"text": "you are in a quiet room", "ts_wall": now}
        },
    )
    block = s.to_prompt_block()
    assert "quiet room" in block
    assert "chair" not in block
    assert "music" not in block


def test_snapshot_drops_stale_vision_audio() -> None:
    old = time.time() - 9_999.0
    s = snapshot(
        "dev-1",
        perception_state={"dev-1": {}},
        vision_cache={"dev-1": {"description": "a chair", "wall_ts": old}},
        audio_cache={"dev-1": {"description": "music", "wall_ts": old}},
        scene_synthesis_cache={},
    )
    assert s.last_vision_desc is None
    assert s.last_audio_desc is None


def test_snapshot_is_frozen_dataclass() -> None:
    s = PerceptionSnapshot(
        state="idle", face="off", face_id=None, face_mood=None,
        listening=False, last_vision_desc=None, last_vision_age_s=None,
        last_audio_desc=None, last_audio_age_s=None,
        scene_synth=None, scene_synth_age_s=None,
    )
    try:
        s.state = "talk"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("PerceptionSnapshot should be frozen")
