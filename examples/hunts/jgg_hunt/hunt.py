"""A complete mock treasure hunt, generated start to finish, written by yours truly.
At this stage I think I have the artifact and puzzle definitions down, so I'm making
a graph now to force any remaining decisions before I move onto how the binder is
going to generate everything.

At the time of writing this, there's not really any way to split the graph into
different teams, or assign locations or solve times to nodes. I don't think any
of that should be part of the "core" classes. I'll ask Claude later what it thinks.
I'm imagining another layer on top of the graph that assigns additional data to nodes
and artifacts (like which team they're meant for), but there could also be some
kind of "properties" class that just gets shoved in.

Anyway, this hunt is basically start with instructions and the two blank R4 grids.
Each team gets one grid.
    * Team L gets a (lat,long) clue, they find the place, find tiles to fill the
    grid and another (lat,long), find the place, find the rest of the tiles.
    They assemble the tiles, and complete the grid.
    * Team R gets a riddle, the solution yields a location. There they find tiles
    to fill the grille and crossword. Solved crossword gives a location, where they find
    more tiles and an image. Image is the final location, where they find the remaining
    tiles.
    * L + R reveals hidden message, which gives final location. The location has a cash
    prize. The end.
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator import (
    Binder,
    Chapter,
    CrosswordPuzzle,
    GraphBuilder,
    HuntDocument,
    ImageArtifact,
    R4DecoderPuzzle,
    RiddlePuzzle,
    TextArtifact,
    topological_order,
)
from puzzcombinator.serialization import (
    to_json,
)


def make_fake_letter_coords_artifacts():
    tiles = ["{},{},{}".format(i, j, "X") for i in range(4) for j in range(4)]
    return [TextArtifact(t) for t in tiles]


def make_fake_block_coords_artifacts():
    tiles = [f"{i},{j}" for i in range(3) for j in range(4)]
    return [TextArtifact(t) for t in tiles]


if __name__ == "__main__":
    out_dir = Path(__file__).parent / "out"
    assets_dir = Path(__file__).parent / "assets"

    builder = GraphBuilder()

    n_start = builder.node(action="kickoff")
    e_instructions = TextArtifact(
        "This is how you play. Two teams. Here's grids you'll need, etc.",
        name="instructions",
    )

    ##############START############

    n_tutorial = builder.node(action="learn", notes="Read instructions, get starting materials")
    builder = builder.connect(n_start, n_tutorial, e_instructions)

    r4 = R4DecoderPuzzle.from_message("MONEY IN THE FRIDGE", seed=7)

    ##############LEFT############

    e_Lcoords1 = TextArtifact("lat1,long1", title="Coordinates 1 (L)")

    n_Lfind1 = builder.node(action="find", notes="Go to coords1, find tiles and coords2")
    builder = builder.connect(n_tutorial, n_Lfind1, e_Lcoords1)

    e_Lcoords2 = TextArtifact("lat2,long2", title="Coordinates 2")
    n_Lfind2 = builder.node(
        action="find", notes="Go to coords2, find remaining tiles to complete grid"
    )
    builder = builder.connect(n_Lfind1, n_Lfind2, e_Lcoords2)

    Ltiles = make_fake_letter_coords_artifacts()
    n_Lgrid_assemble = builder.node(action="assemble", notes="Write in each letter in the grid")
    builder = builder.connect(n_Lfind1, n_Lgrid_assemble, Ltiles[0:8])
    builder = builder.connect(n_Lfind2, n_Lgrid_assemble, Ltiles[8:16])

    e_Lgrid = r4.artifacts("text_blank")
    builder = builder.connect(n_tutorial, n_Lgrid_assemble, e_Lgrid)

    ##############RIGHT############

    riddle = RiddlePuzzle(riddle=["Where childhood monsters dwell"], answer="Under the bed")
    e_Rriddle = riddle.artifacts("full_text")
    n_Rfind1 = builder.node(action="find", notes="Go under the bed, find tiles and crossword")
    builder = builder.connect(n_tutorial, n_Rfind1, e_Rriddle)

    # ......BEAUTY
    # ....GRASS...
    # ......TIME..
    # SCRATCH.....
    cw = CrosswordPuzzle(
        solution=["######BEAUTY", "####GRASS###", "######TIME##", "SCRATCH#####"],
        across={
            1: "Comes after age",
            4: "Touch it",
            5: "You're running out of it",
            6: "When you have an itch",
        },
        down={},
        highlight=[(0, 6), (1, 6), (2, 6), (3, 6)],
    )

    e_Rcw = cw.artifacts("crossword")
    n_Rsolve_cw = builder.node(action="solve", notes="Solve the crossword for next location")
    builder = builder.connect(n_Rfind1, n_Rsolve_cw, e_Rcw)

    e_Rcw_sol = cw.artifacts("solution")
    n_Rfind2 = builder.node(action="find", notes="Find picture in the bathroom")
    builder = builder.connect(n_Rsolve_cw, n_Rfind2, e_Rcw_sol)

    e_Rpic = ImageArtifact.from_file(assets_dir / "doormat.jpg")
    n_Rfind3 = builder.node(action="find", notes="Find tiles under mat")
    builder = builder.connect(n_Rfind2, n_Rfind3, e_Rpic)

    Rtiles = make_fake_block_coords_artifacts()
    n_Rgrid_assemble = builder.node(action="assemble", notes="Fill in bocks in the grid")
    builder = builder.connect(n_Rfind1, n_Rgrid_assemble, Rtiles[0:6])
    builder = builder.connect(n_Rfind2, n_Rgrid_assemble, Rtiles[6:9])
    builder = builder.connect(n_Rfind3, n_Rgrid_assemble, Rtiles[9:12])

    e_Rgrid = r4.artifacts("grille_blank")
    builder = builder.connect(n_tutorial, n_Rgrid_assemble, e_Rgrid)

    ##############RE-MERGE############

    e_Lgrid_sol = r4.artifacts("solution_grid")
    e_Rgrid_sol = r4.artifacts("solution_grille")
    n_grid_merge = builder.node(
        action="combine", notes="Combine grid and grille for secret message"
    )
    builder = builder.connect(n_Rgrid_assemble, n_grid_merge, e_Rgrid_sol)
    builder = builder.connect(n_Lgrid_assemble, n_grid_merge, e_Lgrid_sol)

    e_final = r4.artifacts("solution_text")
    n_find_final = builder.node(action="find", notes="find money in the refrigerator")
    builder = builder.connect(n_grid_merge, n_find_final, e_final)

    e_prize = TextArtifact("A bunch of money")
    n_end = builder.node(action="celebrate", notes="The end")
    builder = builder.connect(n_find_final, n_end, e_prize)

    graph = builder.build()
    doc = HuntDocument.single(graph)
    doc_jsons = to_json(doc)

    with open(Path.joinpath(out_dir, "jgg_hunt.json"), "w", encoding="utf-8") as f:
        f.write(doc_jsons)

    n_all = topological_order(graph)

    by_nodes_all = Binder.of_nodes(graph, n_all)
    with open(Path.joinpath(out_dir, "by_nodes_all.html"), "w", encoding="utf-8") as f:
        f.write(by_nodes_all.render())

    by_artifacts_r4 = Binder.of_artifacts(r4.artifacts().values())
    with open(Path.joinpath(out_dir, "by_artifacts_r4.html"), "w", encoding="utf-8") as f:
        f.write(by_artifacts_r4.render())

    n_Right = [
        n_start,
        n_tutorial,
        n_Rfind1,
        n_Rsolve_cw,
        n_Rfind2,
        n_Rfind3,
        n_Rgrid_assemble,
        n_grid_merge,
        n_find_final,
        n_end,
    ]

    n_Left = [
        n_start,
        n_tutorial,
        n_Lfind1,
        n_Lfind2,
        n_Lgrid_assemble,
        n_grid_merge,
        n_find_final,
        n_end,
    ]

    e_solutions = [
        riddle.artifacts("answer"),
        r4.artifacts("solution_grille"),
        r4.artifacts("solution_grid"),
        r4.artifacts("solution_text"),
        cw.artifacts("solution"),
    ]

    right_chapter = Chapter.of_nodes(graph, n_Right, title="The RIGHT path")
    left_chapter = Chapter.of_nodes(graph, n_Left, title="The LEFT path")
    solution_chapter = Chapter.of_artifacts(e_solutions)

    by_chapters = Binder((right_chapter, left_chapter, solution_chapter), "The big Dog")
    with open(Path.joinpath(out_dir, "by_chapters.html"), "w", encoding="utf-8") as f:
        f.write(by_chapters.render())
