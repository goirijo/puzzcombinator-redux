"""Render a small crossword hunt to HTML so you can open it in a browser.

Run it:

    python examples/crossword_demo.py

It writes two files next to this script:

    crossword_player.html       — what players see (blank grid + clues)
    crossword_gamemaster.html   — the answer key (filled grid + emergent word)

Open them in any browser (and print to PDF to see the page layout).
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import (
    Audience,
    Content,
    CrosswordPuzzle,
    GraphBuilder,
    NodeKind,
    render_binder,
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

hunt = (
    GraphBuilder()
    .node("start", kind=NodeKind.START, label="Welcome")
    .node(
        "crossword",
        payload=crossword,
        label="The Grid",
        notes="Tape this inside the front cover of the red library book.",
    )
    .node("end", kind=NodeKind.END, label="The Cache")
    .connect(
        "start",
        "crossword",
        content=Content(text="Solve the crossword, then read the shaded squares."),
    )
    .connect(
        "crossword",
        "end",
        content=Content(text="Follow the ROAD to the old oak at its end."),
    )
    .build()
)

here = Path(__file__).parent
for audience, name in [
    (Audience.PLAYER, "crossword_player.html"),
    (Audience.GAME_MASTER, "crossword_gamemaster.html"),
]:
    path = here / name
    path.write_text(render_binder(hunt, audience=audience), encoding="utf-8")
    print(f"wrote {path}")
