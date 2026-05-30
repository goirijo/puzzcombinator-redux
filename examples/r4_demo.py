"""Render an R4-decoder hunt to HTML so you can open it in a browser.

Run it:

    python examples/r4_demo.py

It writes three files next to this script:

    r4_player.html        — the standalone puzzle: letter grid + decoder to cut out
    r4_player_blank.html  — the "assembled during the game" variant: blank templates
    r4_gamemaster.html    — the answer key (filled grid, shaded decoder, message)

Open them in a browser (and print to PDF). Cut the open squares out of the
decoder, lay it on the letter grid with the red triangles aligned, read the open
squares, rotate 90 degrees, and repeat four times.
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import (
    Audience,
    Content,
    GraphBuilder,
    NodeKind,
    R4DecoderPuzzle,
    render_binder,
)

MESSAGE = "THE KEY IS UNDER THE THIRD FLOWERPOT"
SEED = 1234  # fixed seed -> reproducible grid/grille


def hunt(*, reveal: bool) -> object:
    puzzle = R4DecoderPuzzle.from_message(
        "decoder",
        MESSAGE,
        seed=SEED,
        reveal_grid=reveal,
        reveal_decoder=reveal,
    )
    return (
        GraphBuilder()
        .node("start", kind=NodeKind.START, label="Welcome")
        .node(
            "decoder",
            payload=puzzle,
            label="The Grille",
            notes="Print the decoder on card stock; the players cut out the open squares.",
        )
        .node("end", kind=NodeKind.END, label="The Cache")
        .connect(
            "start",
            "decoder",
            content=Content(text="Overlay the decoder and rotate to read the message."),
        )
        .connect(
            "decoder",
            "end",
            content=Content(text="Go to the third flowerpot."),
        )
        .build()
    )


here = Path(__file__).parent
outputs = [
    ("r4_player.html", hunt(reveal=True), Audience.PLAYER),
    ("r4_player_blank.html", hunt(reveal=False), Audience.PLAYER),
    ("r4_gamemaster.html", hunt(reveal=True), Audience.GAME_MASTER),
]
for name, graph, audience in outputs:
    path = here / name
    path.write_text(render_binder(graph, audience=audience), encoding="utf-8")
    print(f"wrote {path}")
