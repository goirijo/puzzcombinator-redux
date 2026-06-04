"""A complete mock treasure hunt, generated start to finish.

Run it:

    python examples/hunts/mock_hunt/hunt.py

Writes a full bundle into examples/hunts/mock_hunt/out/:

    binder.html   — the game master's document: a page per action (in solve order)
                    showing what it receives and produces, plus a production
                    checklist of what to print and stage.
    players/      — one standalone printable per puzzle, to print and place.

The hunt is non-linear and uses all five puzzle types plus a physical step.
Puzzles ride the edges *into* the action that solves them; nodes are pure actions
(solve / find / combine / unlock):

    start
      -> [gate cipher] -> solve gate  (reveals: library, attic AND garden)
           -> find (library) -> [crossword]    -> solve -> "ROAD" -------.
           -> find (attic)   -> [R4 grille]     -> solve -> "FIFTH STEP" -+
           -> find (garden)  -> [riddle]        -> solve -> "SUNDIAL" ----+
                                                                          |
                                  combine "ROAD" + "FIFTH STEP" + "SUNDIAL" <'
                                    -> [photo] -> examine the photo
                                      -> unlock the cabinet (physical)
                                        -> treasure
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from puzzcombinator import (
    CaesarCipherPuzzle,
    CrosswordPuzzle,
    GraphBuilder,
    ImagePuzzle,
    R4DecoderPuzzle,
    RiddlePuzzle,
    hunt_bundle,
    write_bundle,
)


def _demo_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """A valid solid-colour PNG built with the stdlib — stands in for a photo."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        crc = struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + body + crc

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


# Puzzle ids are optional and only name the printable output files; we pass
# explicit, readable ones here so the players/ filenames stay legible.
gate = CaesarCipherPuzzle.from_plaintext(plaintext="LIBRARY ATTIC AND GARDEN", shift=4, id="gate")
crossword = CrosswordPuzzle(
    solution=["STAR", "H##A", "O##I", "PLOD"],
    across={1: "Celestial body", 3: "Walk heavily"},
    down={1: "Place to buy things", 2: "Sudden attack"},
    highlight=[(0, 3), (2, 0), (0, 2), (3, 3)],  # R, O, A, D -> "ROAD"
    id="crossword",
)
grille = R4DecoderPuzzle.from_message("FIFTH STEP", seed=7, id="grille")
riddle = RiddlePuzzle(
    riddle=[
        "I have a face but never a frown,",
        "I mark the hours but hold no gears,",
        "and I speak only while the sun is up.",
    ],
    answer="SUNDIAL",
    id="riddle",
)
# Uses this hunt's assets/patio.<ext> if present, else a generated placeholder PNG.
_assets = Path(__file__).parent / "assets"
_photo_file = next(_assets.glob("patio.*"), None) if _assets.is_dir() else None
if _photo_file is not None:
    photo = ImagePuzzle.from_file(
        _photo_file,
        prompt="Which flagstone in this patio is loose?",
        answer="the cracked stone right beside the sundial",
        alt="the garden patio by the sundial",
        id="photo",
    )
else:
    photo = ImagePuzzle.from_bytes(
        _demo_png(48, 32, (90, 140, 90)),
        mime="image/png",
        prompt="Which flagstone in this patio is loose?",
        answer="the cracked stone right beside the sundial",
        alt="the garden patio by the sundial",
        id="photo",
    )

# Nodes are pure actions; node() hands back a handle we wire with (no ids to
# invent). The bracketed puzzles ride the edge *into* the action that solves them.
builder = GraphBuilder()
start = builder.node(label="Kickoff")
solve_gate = builder.node(action="solve", label="Opening cipher")
find_library = builder.node(
    action="find",
    label="The library",
    notes="Tape the crossword inside the red book in the 800s.",
)
find_attic = builder.node(
    action="find",
    label="The attic",
    notes="Hide the grille pieces in the steamer trunk.",
)
find_garden = builder.node(
    action="find",
    label="The garden",
    notes="Scatter the three riddle slips: shed, planter, birdbath.",
)
solve_cw = builder.node(action="solve", label="Library crossword")
solve_grille = builder.node(action="solve", label="Attic grille")
solve_riddle = builder.node(action="solve", label="Garden riddle")
combine = builder.node(action="combine", label="Put it together")
examine = builder.node(
    action="examine",
    label="The patio photo",
    notes="Clip the printed photo to the garden gate.",
)
vault = builder.node(
    action="unlock",
    label="The cabinet",
    notes="Tape the cabinet key under the loose flagstone.",
)
end = builder.node(label="Treasure")

hunt = (
    # opening cipher
    builder.connect(start, solve_gate, puzzle=gate)
    # it sends them three places (branch)
    .connect(solve_gate, find_library, text="Search the LIBRARY.")
    .connect(solve_gate, find_attic, text="Search the ATTIC.")
    .connect(solve_gate, find_garden, text="Search the GARDEN.")
    # each location yields a puzzle, carried on the edge into its solve action
    .connect(find_library, solve_cw, puzzle=crossword)
    .connect(find_attic, solve_grille, puzzle=grille)
    .connect(find_garden, solve_riddle, puzzle=riddle)
    # the three solutions converge (merge)
    .connect(solve_cw, combine, text="ROAD")
    .connect(solve_grille, combine, text="FIFTH STEP")
    .connect(solve_riddle, combine, text="SUNDIAL")
    # combined, they point to the patio; a photo pins the exact spot
    .connect(
        combine,
        examine,
        text="By the SUNDIAL, pace the ROAD to its FIFTH STEP. Study the photo.",
        puzzle=photo,
    )
    # examine -> a physical step -> the prize
    .connect(examine, vault, text="Lift the loose flagstone for the cabinet key.")
    .connect(vault, end, text="Open the cabinet — you found the treasure!")
    .build()
)

out_dir = Path(__file__).parent / "out"
for path in write_bundle(hunt_bundle(hunt), out_dir):
    print(f"wrote {path}")
