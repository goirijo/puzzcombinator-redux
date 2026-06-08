from __future__ import annotations

import pytest

from puzzcombinator import RiddleLineArtifact, RiddlePuzzle
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


def test_line_artifacts_one_per_part_for_scattering() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    artifacts = puzzle.artifacts()
    # One artifact per line (scatterable), then the assembled full text, then the answer.
    assert list(artifacts) == [f"line{i}" for i in range(len(parts))] + ["full_text", "answer"]
    # the answer appears only on the answer piece, never on a line sheet
    lines = [a for name, a in artifacts.items() if name.startswith("line")]
    assert all(answer not in a.render().markup for a in lines)
    # each line is addressable on its own (the scatter idiom)
    assert puzzle.artifacts("line1").id == "r1-line1"


def test_full_text_joins_every_line() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    full = puzzle.artifacts("full_text")
    assert full.id == "r1-full_text"
    assert full.text == "\n".join(parts)
    # the assembled riddle carries every line but not the answer
    assert all(part in full.text for part in parts)
    assert answer not in full.render().markup


def test_artifacts_include_the_answer() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    artifacts = puzzle.artifacts()
    assert "answer" in artifacts
    assert answer in artifacts["answer"].render().markup
    assert artifacts["answer"].id == "r1-answer"


def test_line_artifact_payload_roundtrip() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    art = puzzle.artifacts("line0")
    rebuilt = RiddleLineArtifact.from_payload(name=art.name, id=art.id, payload=art.to_payload())
    assert rebuilt == art


def test_line_artifact_eq_and_hash() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    a = puzzle.artifacts("line0")
    b = puzzle.artifacts("line0")
    assert a == b
    assert a != "not an artifact"
    assert len({a, b}) == 1
