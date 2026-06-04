"""Render an R4-decoder hunt to a bundle you can open in a browser.

Run it:

    python examples/puzzles/r4_demo.py

It writes a bundle into examples/puzzles/r4_out/:

    binder.html                  — the game master's document (answer key + checklist)
    players/decoder-grid.svg     — the letter grid, its own standalone printable
    players/decoder-decoder.svg  — the decoder, its own standalone printable (cut it out)

The .svg files are standalone documents: open one in a browser to "Save As" or
print it on its own page, or hand it to a print service. Cut the open squares
out of the decoder, lay it on the letter grid with the red triangles aligned,
read the open squares, rotate 90 degrees, and repeat four times.

Pass reveal_grid=False / reveal_decoder=False to the puzzle for the
"assembled during the game" variant, where players fill the grid / shade the
decoder from clues other puzzles reveal.
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import (
    GraphBuilder,
    R4DecoderPuzzle,
    hunt_bundle,
    write_bundle,
)

puzzle = R4DecoderPuzzle.from_message(
    "THE KEY IS UNDER THE THIRD FLOWERPOT", seed=1234, id="decoder"
)

# The grille rides the edge into the "solve" action.
builder = GraphBuilder()
start = builder.node(label="Welcome")
solve = builder.node(
    action="solve",
    label="The Grille",
    notes="Print the decoder on card stock; players cut out the open squares.",
)
end = builder.node(label="The Cache")
hunt = (
    builder.connect(start, solve, puzzle=puzzle)
    .connect(solve, end, text="Go to the third flowerpot.")
    .build()
)

out_dir = Path(__file__).parent / "r4_out"
for path in write_bundle(hunt_bundle(hunt), out_dir):
    print(f"wrote {path}")
