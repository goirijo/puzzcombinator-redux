"""Shared fixtures."""

from __future__ import annotations

import pytest

from puzzcombinator import (
    CaesarCipherPuzzle,
    Graph,
    GraphBuilder,
)


@pytest.fixture
def converging_hunt() -> Graph:
    """A two-path hunt that merges:  start -> A -> merge ; start -> B -> merge -> end."""
    return (
        GraphBuilder()
        .node("start")
        .node("A", action="find")
        .node("B", action="find")
        .node("merge", action="combine")
        .node("end")
        .connect("start", "A", text="path A")
        .connect("start", "B", text="path B")
        .connect("A", "merge", text="half one")
        .connect("B", "merge", text="half two")
        .connect("merge", "end", text="the treasure")
        .build()
    )


@pytest.fixture
def cipher_hunt() -> Graph:
    """A linear hunt: start -> solve -> end, with a Caesar puzzle on the first edge."""
    cipher = CaesarCipherPuzzle.from_plaintext("c1", plaintext="FOUNTAIN", shift=3)
    return (
        GraphBuilder()
        .node("start", label="Welcome")
        .node("solve", action="solve", label="Caesar gate", notes="hide under the doormat")
        .node("end", label="Treasure")
        .connect("start", "solve", puzzle=cipher)
        .connect("solve", "end", text="Go to the fountain.")
        .build()
    )
