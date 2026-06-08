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
from puzzcombinator.rendering.export import html_document


def main() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="cipher")

    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    for name, artifact in puzzle.artifacts().items():
        fragment = artifact.render()
        if fragment.kind == "svg":
            path = out / f"{name}.svg"
            path.write_text(fragment.markup, encoding="utf-8")
        else:
            path = out / f"{name}.html"
            path.write_text(html_document(name, fragment.markup, fragment.styles), encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
