"""Caesar cipher demo — write every artifact this puzzle emits to its own file.

Run it:

    python examples/puzzles/cipher/demo.py

A puzzle emits all of its pieces as one ``{name: Artifact}`` map. This script renders
each piece and writes it into ``out/`` — ``.svg`` for inline-SVG pieces, ``.html`` for
the rest — so you can open every artifact on its own in a browser.

The cipher emits two pieces: ``cipher`` (the ciphertext to decode) and ``solution``
(the Caesar shift + the decoded answer).
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import CaesarCipherPuzzle
from puzzcombinator.rendering.export import dump_artifacts


def main() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="cipher")

    out = Path(__file__).parent / "out"
    for path in dump_artifacts(puzzle.artifacts(), out):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
