"""Puzzle types and their registry."""

from __future__ import annotations

from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.cipher import CaesarCipherPuzzle
from puzzcombinator.puzzles.crossword import CrosswordPuzzle
from puzzcombinator.puzzles.registry import build_puzzle, register_puzzle

__all__ = [
    "CaesarCipherPuzzle",
    "CrosswordPuzzle",
    "Puzzle",
    "build_puzzle",
    "register_puzzle",
]
