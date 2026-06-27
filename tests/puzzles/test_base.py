"""Tests for the Puzzle base class — the artifacts() name dispatch and guards."""

from __future__ import annotations

import pytest

from puzzcombinator import TextArtifact
from puzzcombinator.errors import PuzzleError
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.rendering.fragment import Artifact


class _DupNamePuzzle(Puzzle):
    """A deliberately-broken puzzle that emits two artifacts sharing a name."""

    type_name = "dup"

    def _artifacts(self) -> list[Artifact]:
        return [
            TextArtifact("first", name="clue"),
            TextArtifact("second", name="clue"),
        ]


def test_duplicate_artifact_names_raise() -> None:
    puzzle = _DupNamePuzzle(id="d1")
    with pytest.raises(PuzzleError, match=r"duplicate artifact names.*clue"):
        puzzle.artifacts()
