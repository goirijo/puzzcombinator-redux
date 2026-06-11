"""R4 turning-grille demo — write every artifact this puzzle emits to its own file.

Run it:

    python examples/puzzles/r4/demo.py

A puzzle emits all of its pieces as one ``{name: Artifact}`` map. This script renders
each piece and writes it into ``out/`` — ``.svg`` for inline-SVG pieces, ``.html`` for
the rest — so you can open every artifact on its own in a browser.

The R4 decoder emits five pieces, named ``{role}_{form}``: two identical blank
inline-SVG grids the player works on — ``text_blank`` (write the letters in) and
``grille_blank`` (turn into the decoder) — plus the answer key ``solution_grille``
(which cells are open), ``solution_grid`` (the grid with its letters filled in), and
``solution_text`` (the decoded message and reading order).
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import R4DecoderPuzzle
from puzzcombinator.rendering.export import write_artifacts


def main() -> None:
    puzzle = R4DecoderPuzzle.from_message("MEET AT DAWN", seed=7, id="r4")

    out = Path(__file__).parent / "out"
    for path in write_artifacts(puzzle.artifacts(), out):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
