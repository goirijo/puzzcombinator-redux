"""End-to-end: author -> serialize -> reload -> order -> inspect I/O -> render.

The full loop a designer takes: build a graph, round-trip it through the hunt-document
envelope, confirm solve order and the artifacts flowing on each edge, then compose a
binder over the reloaded graph. There is no player-vs-game-master split anymore — a
binder is just the renderings the designer chose to collect, so the answer-key and the
prompt pieces both appear in a node-walk binder (the designer omits or separates pieces
by *which* binder they build, not by a tag on the artifact).
"""

from __future__ import annotations

from puzzcombinator import (
    Binder,
    CaesarCipherPuzzle,
    GraphBuilder,
    HuntDocument,
    TextArtifact,
    produced_outputs,
    topological_order,
)
from puzzcombinator.serialization import from_json, to_json


def test_full_flow() -> None:
    cipher = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    builder = GraphBuilder()
    start = builder.node("start", label="Welcome")
    solve = builder.node("solve", action="solve", label="Caesar gate", notes="leave on the bench")
    end = builder.node("end", label="Treasure")
    graph = (
        builder.connect(start, solve, *cipher.artifacts().values())
        .connect(solve, end, TextArtifact("Go to the fountain."))
        .build()
    )

    # Serialize and reload — value-equal (through the hunt-document envelope).
    reloaded = from_json(to_json(HuntDocument.single(graph))).main
    assert reloaded == graph

    # Solve order respects the chain.
    assert topological_order(reloaded) == ["start", "solve", "end"]

    # The solve action's output (the revealed clue) flows on its outgoing edge.
    assert [a.text for a in produced_outputs(reloaded, "solve")] == ["Go to the fountain."]

    # A node-walk binder renders the whole reloaded graph in solve order.
    walkthrough = Binder.of_nodes(reloaded, topological_order(reloaded)).render()
    assert "<!DOCTYPE html>" in walkthrough
    assert "IRXQWDLQ" in walkthrough  # the ciphertext piece (FOUNTAIN shifted by 3)
    assert "FOUNTAIN" in walkthrough  # the solution piece placed on the same edge
    assert "leave on the bench" in walkthrough  # designer notes
    assert "Go to the fountain." in walkthrough  # the revealed downstream clue

    # An answer-key binder is just the solution pieces collected on their own.
    answers = Binder.of_artifacts([cipher.artifacts("solution")], title="Answers").render()
    assert "FOUNTAIN" in answers
    assert "IRXQWDLQ" not in answers  # the ciphertext isn't in this collection
