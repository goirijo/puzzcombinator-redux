"""A complete mock treasure hunt, generated start to finish.

Run it:

    python examples/mock_hunt.py

Writes a full bundle into examples/mock_hunt_out/:

    binder.html   — the game master's document: a page per action (in solve order)
                    showing what it receives and produces, plus a production
                    checklist of what to print and stage.
    players/      — one standalone printable per puzzle, to print and place.

The hunt is non-linear and uses all three puzzle types plus a physical step.
Puzzles ride the edges *into* the action that solves them; nodes are pure actions
(solve / find / combine / unlock):

    start
      -> [gate cipher] -> solve gate  (reveals: library AND attic)
           -> find (library) -> [crossword] -> solve  -> "ROAD" ----.
           -> find (attic)   -> [R4 grille] -> solve  -> "FIFTH STEP" --+
                                                                        |
                                          combine "ROAD" + "FIFTH STEP" <'
                                            -> unlock the cabinet (physical)
                                              -> treasure
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import (
    CaesarCipherPuzzle,
    CrosswordPuzzle,
    GraphBuilder,
    R4DecoderPuzzle,
    hunt_bundle,
    write_bundle,
)

gate = CaesarCipherPuzzle.from_plaintext("gate", plaintext="LIBRARY AND ATTIC", shift=4)
crossword = CrosswordPuzzle(
    "crossword",
    solution=["STAR", "H##A", "O##I", "PLOD"],
    across={1: "Celestial body", 3: "Walk heavily"},
    down={1: "Place to buy things", 2: "Sudden attack"},
    highlight=[(0, 3), (2, 0), (0, 2), (3, 3)],  # R, O, A, D -> "ROAD"
)
grille = R4DecoderPuzzle.from_message("grille", "FIFTH STEP", seed=7)

hunt = (
    GraphBuilder()
    .node("start", label="Kickoff")
    .node("solve_gate", action="solve", label="Opening cipher")
    .node(
        "find_library",
        action="find",
        label="The library",
        notes="Tape the crossword inside the red book in the 800s.",
    )
    .node(
        "find_attic",
        action="find",
        label="The attic",
        notes="Hide the grille pieces in the steamer trunk.",
    )
    .node("solve_cw", action="solve", label="Library crossword")
    .node("solve_grille", action="solve", label="Attic grille")
    .node("combine", action="combine", label="Put it together")
    .node(
        "vault",
        action="unlock",
        label="The cabinet",
        notes="Tape the cabinet key under the front doormat.",
    )
    .node("end", label="Treasure")
    # opening cipher
    .connect("start", "solve_gate", puzzle=gate)
    # it sends them two places (branch)
    .connect("solve_gate", "find_library", text="Search the LIBRARY.")
    .connect("solve_gate", "find_attic", text="Search the ATTIC.")
    # each location yields a puzzle, carried on the edge into its solve action
    .connect("find_library", "solve_cw", puzzle=crossword)
    .connect("find_attic", "solve_grille", puzzle=grille)
    # the two solutions converge (merge)
    .connect("solve_cw", "combine", text="ROAD")
    .connect("solve_grille", "combine", text="FIFTH STEP")
    # combine -> a physical step -> the prize
    .connect("combine", "vault", text="Under the doormat at the road's fifth step.")
    .connect("vault", "end", text="Open the cabinet — you found the treasure!")
    .build()
)

out_dir = Path(__file__).parent / "mock_hunt_out"
for path in write_bundle(hunt_bundle(hunt), out_dir):
    print(f"wrote {path}")
