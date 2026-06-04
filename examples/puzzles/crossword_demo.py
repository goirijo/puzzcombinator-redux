"""Render a small crossword hunt to a bundle you can open in a browser.

Run it:

    python examples/puzzles/crossword_demo.py

It writes a bundle into examples/puzzles/crossword_out/:

    binder.html                  — the game master's document (answer key + checklist)
    players/grid-crossword.html  — the player printable (blank grid + clues)

Open them in any browser (and print to PDF to see the page layout).
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import (
    Audience,
    CrosswordPuzzle,
    GraphBuilder,
    TextArtifact,
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
    solution=["STAR", "H##A", "O##I", "PLOD"],
    across={1: "Celestial body", 3: "Walk heavily"},
    down={1: "Place to buy things", 2: "Sudden attack"},
    highlight=[(0, 3), (2, 0), (0, 2), (3, 3)],  # R, O, A, D -> "ROAD"
    id="grid",  # optional; just prefixes the printable filename so it stays readable
)

# The crossword's artifacts ride the edge into the "solve" action; the player sheet
# shows the blank grid + clues, and the game-master artifact reveals the answers and
# the emergent word "ROAD".
builder = GraphBuilder()
start = builder.node(label="Welcome")
solve = builder.node(
    action="solve",
    label="The Grid",
    notes="Tape the crossword inside the front cover of the red library book.",
)
end = builder.node(label="The Cache")
hunt = (
    builder.connect(
        start,
        solve,
        crossword.artifacts("crossword"),
        crossword.artifacts("crossword", audience=Audience.GAME_MASTER),
    )
    .connect(solve, end, TextArtifact("Follow the ROAD to the old oak at its end.", id="to-oak"))
    .build()
)

if __name__ == "__main__":
    out_dir = Path(__file__).parent / "crossword_out"
    for path in write_bundle(hunt_bundle(hunt), out_dir):
        print(f"wrote {path}")
