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
    """A two-path hunt that merges:  start -> A -> merge ; start -> B -> merge -> end.

    Uses explicit ids because the tests reference these nodes by id, but still
    threads the handles ``node()`` returns into ``connect`` (never re-typing them).
    """
    builder = GraphBuilder()
    start = builder.node("start")
    a = builder.node("A", action="find")
    b = builder.node("B", action="find")
    merge = builder.node("merge", action="combine")
    end = builder.node("end")
    return (
        builder.connect(start, a, text="path A")
        .connect(start, b, text="path B")
        .connect(a, merge, text="half one")
        .connect(b, merge, text="half two")
        .connect(merge, end, text="the treasure")
        .build()
    )


@pytest.fixture
def cipher_hunt() -> Graph:
    """A linear hunt: start -> solve -> end, with a Caesar puzzle on the first edge."""
    cipher = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    builder = GraphBuilder()
    start = builder.node("start", label="Welcome")
    solve = builder.node(
        "solve", action="solve", label="Caesar gate", notes="hide under the doormat"
    )
    end = builder.node("end", label="Treasure")
    return (
        builder.connect(start, solve, puzzle=cipher)
        .connect(solve, end, text="Go to the fountain.")
        .build()
    )
