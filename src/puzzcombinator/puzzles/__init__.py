"""Puzzle generators and the concrete artifact types they emit.

A :class:`Puzzle` is an authoring-time generator; each concrete puzzle lives here
beside the artifact type(s) it produces. The standalone *orphan* artifacts that
have no puzzle behind them (``TextArtifact``, ``ImageArtifact``) and the artifact
registry live in the sibling :mod:`puzzcombinator.artifacts` package.
"""

from __future__ import annotations

from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.cipher import CaesarCipherPuzzle, CipherArtifact
from puzzcombinator.puzzles.crossword import CrosswordArtifact, CrosswordPuzzle
from puzzcombinator.puzzles.r4 import R4DecoderPuzzle, R4PieceArtifact
from puzzcombinator.puzzles.riddle import RiddleLineArtifact, RiddlePuzzle

__all__ = [
    "CaesarCipherPuzzle",
    "CipherArtifact",
    "CrosswordArtifact",
    "CrosswordPuzzle",
    "Puzzle",
    "R4DecoderPuzzle",
    "R4PieceArtifact",
    "RiddleLineArtifact",
    "RiddlePuzzle",
]
