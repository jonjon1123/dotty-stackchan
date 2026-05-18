"""is_notable_perception — Jaccard-similarity notability check."""

from __future__ import annotations

from perception import is_notable_perception


def test_empty_and_short_descriptions_are_not_notable() -> None:
    assert is_notable_perception("", None, jaccard_threshold=0.7) is False
    assert is_notable_perception("a chair", None, jaccard_threshold=0.7) is False


def test_same_as_before_phrase_is_not_notable() -> None:
    assert (
        is_notable_perception(
            "The room is essentially the same as before with the same furniture.",
            "anything",
            jaccard_threshold=0.7,
        )
        is False
    )


def test_first_description_is_always_notable() -> None:
    assert (
        is_notable_perception(
            "A red chair sits in front of a wooden bookshelf.",
            None,
            jaccard_threshold=0.7,
        )
        is True
    )


def test_identical_descriptions_are_not_notable() -> None:
    desc = "A red chair sits in front of a wooden bookshelf."
    assert (
        is_notable_perception(desc, desc, jaccard_threshold=0.7) is False
    )


def test_very_different_descriptions_are_notable() -> None:
    a = "A red chair sits in front of a wooden bookshelf."
    b = "A grey cat sleeps curled on the blue rug under the window."
    assert is_notable_perception(b, a, jaccard_threshold=0.7) is True


def test_threshold_inversely_affects_strictness() -> None:
    a = "A red chair sits in front of a wooden bookshelf."
    b = "A red chair sits in front of a wooden table."
    # Most tokens overlap → above strict 0.5 threshold → notable False
    assert is_notable_perception(b, a, jaccard_threshold=0.5) is False
    # Loose 0.9 threshold → most pairs notable
    assert is_notable_perception(b, a, jaccard_threshold=0.9) is True
