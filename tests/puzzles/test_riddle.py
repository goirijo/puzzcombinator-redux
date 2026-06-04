from __future__ import annotations

import pytest

from puzzcombinator import Audience, RiddleLineArtifact, RiddlePuzzle
from puzzcombinator.errors import PuzzleError


def test_artifacts_unknown_name_raises() -> None:
    puzzle = RiddlePuzzle("r1", riddle=["a", "b"], answer="x")
    with pytest.raises(PuzzleError, match="no artifact named 'nope'"):
        puzzle.artifacts("nope")


parts = [
    "The person who built it sold it.",
    "The person who bought it never used it.",
    "The person who used it never saw it.",
]
answer = "coffin"


def test_construction() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    assert puzzle.answer == answer
    assert puzzle.parts == parts


def test_player_artifacts_one_per_part_for_scattering() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    artifacts = puzzle.artifacts()
    assert list(artifacts) == [f"line{i}" for i in range(len(parts))]
    # the answer must never leak onto a player sheet
    assert all(answer not in a.render().markup for a in artifacts.values())
    # each line is addressable on its own (the scatter idiom)
    assert puzzle.artifacts("line1").id == "r1-line1"


def test_game_master_set_adds_the_answer() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    gm = puzzle.artifacts(audience=Audience.GAME_MASTER)
    assert "answer" in gm
    assert answer in gm["answer"].render().markup


def test_line_artifact_payload_roundtrip() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    art = puzzle.artifacts("line0")
    rebuilt = RiddleLineArtifact.from_payload(
        name=art.name, audience=art.audience, id=art.id, payload=art.to_payload()
    )
    assert rebuilt == art


def test_line_artifact_eq_and_hash() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    a = puzzle.artifacts("line0")
    b = puzzle.artifacts("line0")
    assert a == b
    assert a != "not an artifact"
    assert len({a, b}) == 1
