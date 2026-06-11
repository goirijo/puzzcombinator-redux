"""Crossword demo — write every artifact this puzzle emits to its own file.

Run it:

    python examples/puzzles/crossword/demo.py

A puzzle emits all of its pieces as one ``{name: Artifact}`` map. This script renders
each piece and writes it into ``out/`` — ``.svg`` for inline-SVG pieces, ``.html`` for
the rest — so you can open every artifact on its own in a browser.

The crossword emits two pieces: ``crossword`` (the blank numbered grid + clues) and
``solution`` (the filled grid, answers, and the emergent word the shaded cells spell).
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import CrosswordPuzzle
from puzzcombinator.rendering.export import write_artifacts

# Solution grid (# = black square):
#   S T A R
#   H . . A
#   O . . I
#   P L O D
# Across: 1 STAR, 3 PLOD.  Down: 1 SHOP, 2 RAID.
# The shaded cells spell the emergent clue: ROAD.
PUZZLE = CrosswordPuzzle(
    solution=["STAR", "H##A", "O##I", "PLOD"],
    across={1: "Celestial body", 3: "Walk heavily"},
    down={1: "Place to buy things", 2: "Sudden attack"},
    highlight=[(0, 3), (2, 0), (0, 2), (3, 3)],  # R, O, A, D -> "ROAD"
    id="crossword",
)


def main() -> None:
    out = Path(__file__).parent / "out"
    for path in write_artifacts(PUZZLE.artifacts(), out):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
