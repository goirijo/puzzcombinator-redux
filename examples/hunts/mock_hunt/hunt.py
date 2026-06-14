"""A complete mock treasure hunt, generated start to finish.

Run it:

    python examples/hunts/mock_hunt/hunt.py

Writes several composed binders into examples/hunts/mock_hunt/out/. A "binder" is just
a collection of renderings the designer chose to put together — there is no fixed
"the output" — so this example builds a few:

    binder.html      — a page per action in solve order, each showing what it receives
                       and produces (Binder.of_nodes over topological_order).
    solutions.html   — every puzzle's answer-key piece collected on its own
                       (Binder.of_artifacts).
    by_chapter.html  — the same node walk, grouped into chapters (one per hunt branch),
                       to show chapters + page breaks.
    players/         — one standalone native file per artifact (write_artifacts).

The hunt is non-linear and uses all four puzzle types, a standalone image artifact,
and a physical step. A puzzle is a *generator* of artifacts; the designer places those
artifacts on edges. An image has no puzzle behind it, so it is built directly as an
artifact. The garden branch shows the payoff: the riddle's three lines are
**scattered** onto three different edges, found at three spots, and assembled at the
solve. Nodes are pure actions (solve / find / combine / unlock):

    start
      -> [gate cipher] -> solve gate  (reveals: library, attic AND garden)
           -> find (library) -> [crossword]  -> solve -> "ROAD" -----------.
           -> find (attic)   -> [R4 grille]   -> solve -> "FIFTH STEP" -----+
           -> find (garden)                                                 |
                -> shed     -> [riddle line 1] .                            |
                -> planter  -> [riddle line 2] -+-> solve -> "SUNDIAL" -----+
                -> birdbath -> [riddle line 3] '                            |
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
    Binder,
    CaesarCipherPuzzle,
    Chapter,
    CrosswordPuzzle,
    GraphBuilder,
    ImageArtifact,
    R4DecoderPuzzle,
    RiddlePuzzle,
    TextArtifact,
    topological_order,
    write_artifacts,
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


# Puzzle ids are optional and only prefix the ids of the artifacts they emit (which
# name the printable output files); we pass explicit, readable ones here so the
# players/ filenames stay legible.
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
# An image is a standalone artifact — there is no puzzle to generate, so the designer
# builds it directly (unlike the cipher/crossword/grille/riddle above). An ImageArtifact
# is just the picture; the question that goes with it and its answer are separate text
# artifacts the designer places on the edge (the prompt) and collects into the answer
# key (the answer). Make the player picture from this hunt's assets/patio.<ext> if
# present, else a generated placeholder PNG.
_assets = Path(__file__).parent / "assets"
_photo_file = next(_assets.glob("patio.*"), None) if _assets.is_dir() else None
_alt = "the garden patio by the sundial"
if _photo_file is not None:
    photo = ImageArtifact.from_file(_photo_file, alt=_alt, id="photo")
else:
    photo = ImageArtifact.from_bytes(
        _demo_png(48, 32, (90, 140, 90)), mime="image/png", alt=_alt, id="photo"
    )
photo_prompt = TextArtifact("Which flagstone in this patio is loose?", id="patio-prompt")
photo_answer = TextArtifact("the cracked stone right beside the sundial", id="patio-answer")

# Nodes are pure actions; node() hands back a handle we wire with (no ids to
# invent). A puzzle's artifacts ride the edge *into* the action that solves them.
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
    notes="The garden has three hiding spots; one riddle line in each.",
)
find_shed = builder.node(action="find", label="The shed", notes="Riddle line 1 under a flowerpot.")
find_planter = builder.node(action="find", label="The planter", notes="Riddle line 2 in the soil.")
find_birdbath = builder.node(action="find", label="The birdbath", notes="Riddle line 3 underneath.")
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
    # opening cipher — every piece (player ciphertext + the shift/solution answer key)
    # rides the edge into the solve; which pieces end up in which binder is decided
    # later, by what the designer collects, not by a tag on the artifact.
    builder.connect(start, solve_gate, *gate.artifacts().values())
    # it sends them three places (branch)
    .connect(solve_gate, find_library, TextArtifact("Search the LIBRARY.", id="to-library"))
    .connect(solve_gate, find_attic, TextArtifact("Search the ATTIC.", id="to-attic"))
    .connect(solve_gate, find_garden, TextArtifact("Search the GARDEN.", id="to-garden"))
    # library and attic each yield one whole puzzle on the edge into its solve
    .connect(find_library, solve_cw, *crossword.artifacts().values())
    .connect(find_attic, solve_grille, *grille.artifacts().values())
    # the garden fans out to three spots, each hiding ONE scattered riddle line
    .connect(find_garden, find_shed, TextArtifact("Check the shed.", id="to-shed"))
    .connect(find_garden, find_planter, TextArtifact("Check the planter.", id="to-planter"))
    .connect(find_garden, find_birdbath, TextArtifact("Check the birdbath.", id="to-birdbath"))
    .connect(find_shed, solve_riddle, riddle.artifacts("line0"))
    .connect(find_planter, solve_riddle, riddle.artifacts("line1"))
    .connect(find_birdbath, solve_riddle, riddle.artifacts("line2"))
    # the three solutions converge (merge)
    .connect(solve_cw, combine, TextArtifact("ROAD", id="word-road"))
    .connect(solve_grille, combine, TextArtifact("FIFTH STEP", id="word-fifth-step"))
    .connect(
        solve_riddle,
        combine,
        TextArtifact("SUNDIAL", id="word-sundial"),
        riddle.artifacts("answer"),
    )
    # combined, they point to the patio; a photo + its question pin the exact spot, and
    # the answer rides along for the answer key.
    .connect(
        combine,
        examine,
        TextArtifact(
            "By the SUNDIAL, pace the ROAD to its FIFTH STEP. Study the photo.", id="to-patio"
        ),
        photo,
        photo_prompt,
        photo_answer,
    )
    # examine -> a physical step -> the prize
    .connect(
        examine, vault, TextArtifact("Lift the loose flagstone for the cabinet key.", id="to-vault")
    )
    .connect(vault, end, TextArtifact("Open the cabinet — you found the treasure!", id="to-end"))
    .build()
)

if __name__ == "__main__":
    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. A page-per-node walkthrough in solve order.
    walkthrough = Binder.of_nodes(hunt, topological_order(hunt), title="Mock Hunt — walkthrough")

    # 2. The answer key: every puzzle's solution piece collected on its own. Just a
    #    different choice of what to put together — the same model, no special tag.
    answers = Binder.of_artifacts(
        [
            gate.artifacts("solution"),
            crossword.artifacts("solution"),
            grille.artifacts("solution_text"),
            riddle.artifacts("answer"),
            photo_answer,
        ],
        title="Mock Hunt — answer key",
    )

    # 3. The same walk, hand-grouped into chapters (one per hunt branch) to show chapters
    #    and the page break between them. The node handles are already ids, so they go
    #    straight into of_nodes — no Node materialization needed.
    by_chapter = Binder(
        (
            Chapter.of_nodes(hunt, [start, solve_gate], title="Opening"),
            Chapter.of_nodes(hunt, [find_library, solve_cw], title="Library branch"),
            Chapter.of_nodes(hunt, [find_attic, solve_grille], title="Attic branch"),
            Chapter.of_nodes(
                hunt,
                [find_garden, find_shed, find_planter, find_birdbath, solve_riddle],
                title="Garden branch",
            ),
            Chapter.of_nodes(hunt, [combine, examine, vault, end], title="Finale"),
        ),
        title="Mock Hunt — by branch",
    )

    for name, binder in (
        ("binder.html", walkthrough),
        ("solutions.html", answers),
        ("by_chapter.html", by_chapter),
    ):
        path = out_dir / name
        _ = path.write_text(binder.render(), encoding="utf-8")
        print(f"wrote {path}")

    # 4. One standalone native file per artifact (dedup by id; the same piece may ride
    #    several edges).
    pieces = {a.id: a for edge in hunt.edges.values() for a in edge.content}
    for path in write_artifacts(pieces, out_dir / "players"):
        print(f"wrote {path}")
