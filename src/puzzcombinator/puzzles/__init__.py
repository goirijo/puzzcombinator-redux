"""Puzzle types and their registry."""

from __future__ import annotations

from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.cipher import CaesarCipherPuzzle
from puzzcombinator.puzzles.crossword import CrosswordPuzzle
from puzzcombinator.puzzles.image import ImagePuzzle
from puzzcombinator.puzzles.r4 import R4DecoderPuzzle
from puzzcombinator.puzzles.registry import build_puzzle, register_puzzle

__all__ = [
    "CaesarCipherPuzzle",
    "CrosswordPuzzle",
    "ImagePuzzle",
    "Puzzle",
    "R4DecoderPuzzle",
    "build_puzzle",
    "register_puzzle",
]
