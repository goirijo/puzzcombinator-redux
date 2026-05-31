"""Render a small crossword hunt to a bundle you can open in a browser.

Run it:

    python examples/crossword_demo.py

It writes a bundle into examples/crossword_out/:

    binder.html            — the game master's document (answer key + checklist)
    players/grid-puzzle.html — the player printable (blank grid + clues)

Open them in any browser (and print to PDF to see the page layout).
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import (
    CrosswordPuzzle,
    GraphBuilder,
    hunt_bundle,
    write_bundle,
)

# Solution grid (# = black square):
#   S T A R
#   H . . A
#   O . . I
#   P L O D
# Across: 1 STAR, 3 PLOD.  Down: 1 SHOP, 2 RAID.
# Shaded cells spell the emergent clue: ROAD.
crossword = CrosswordPuzzle(
    "grid",
    solution=["STAR", "H##A", "O##I", "PLOD"],
    across={1: "Celestial body", 3: "Walk heavily"},
    down={1: "Place to buy things", 2: "Sudden attack"},
    highlight=[(0, 3), (2, 0), (0, 2), (3, 3)],  # R, O, A, D -> "ROAD"
)

# The crossword rides the edge into the "solve" action; solving yields "ROAD".
hunt = (
    GraphBuilder()
    .node("start", label="Welcome")
    .node(
        "solve",
        action="solve",
        label="The Grid",
        notes="Tape the crossword inside the front cover of the red library book.",
    )
    .node("end", label="The Cache")
    .connect("start", "solve", puzzle=crossword)
    .connect("solve", "end", text="Follow the ROAD to the old oak at its end.")
    .build()
)

out_dir = Path(__file__).parent / "crossword_out"
for path in write_bundle(hunt_bundle(hunt), out_dir):
    print(f"wrote {path}")
