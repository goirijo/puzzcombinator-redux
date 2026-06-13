"""A small in-code hunt so the editor always has something to draw.

This keeps the read-only milestone self-contained: the server can render *something*
with zero setup and no dependency on the example scripts (whose binder step is still
stale). The shape is deliberately branchy — a cipher gate, then two parallel
search-paths that merge before the finale — so the layered layout is visibly
non-trivial.
"""

from __future__ import annotations

from puzzcombinator import CaesarCipherPuzzle, GraphBuilder, TextArtifact
from puzzcombinator.core.graph import Graph


def build_demo_graph() -> Graph:
    """Build the demo hunt: start -> solve -> (garden, shed) -> combine -> end."""
    gate = CaesarCipherPuzzle.from_plaintext(plaintext="GARDEN AND SHED", shift=3, id="gate")
    b = GraphBuilder()
    start = b.node("start", label="Kickoff")
    solve = b.node("solve", action="solve", label="Opening cipher")
    garden = b.node("garden", action="find", label="The garden")
    shed = b.node("shed", action="find", label="The shed")
    combine = b.node("combine", action="combine", label="Assemble the key")
    end = b.node("end", label="Treasure")
    return (
        b.connect(start, solve, *gate.artifacts().values())
        .connect(solve, garden, TextArtifact("Search the GARDEN.", id="to-garden"))
        .connect(solve, shed, TextArtifact("Also check the SHED.", id="to-shed"))
        .connect(garden, combine, TextArtifact("first half of the code", id="half-1"))
        .connect(shed, combine, TextArtifact("second half of the code", id="half-2"))
        .connect(combine, end, TextArtifact("Dig beneath the old oak.", id="final"))
        .build()
    )
