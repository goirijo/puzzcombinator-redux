"""Riddle demo — write every artifact this puzzle emits to its own file.

Run it:

    python examples/puzzles/riddle/demo.py

A puzzle emits all of its pieces as one ``{name: Artifact}`` map. This script renders
each piece and writes it into ``out/`` — ``.svg`` for inline-SVG pieces, ``.html`` for
the rest — so you can open every artifact on its own in a browser.

The riddle emits one ``line{N}`` piece per line (each on its own sheet, so the lines
can be scattered across a hunt and reassembled), a ``full_text`` piece with the lines
joined into the assembled riddle, plus an ``answer`` piece.
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import RiddlePuzzle
from puzzcombinator.rendering.export import write_artifacts

PUZZLE = RiddlePuzzle(
    "riddle",
    riddle=[
        "The person who built it sold it.",
        "The person who bought it never used it.",
        "The person who used it never saw it.",
    ],
    answer="A coffin.",
)


def main() -> None:
    out = Path(__file__).parent / "out"
    for path in write_artifacts(PUZZLE.artifacts(), out):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
