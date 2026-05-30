"""Shared fixtures."""

from __future__ import annotations

import pytest

from puzzcombinator import (
    CaesarCipherPuzzle,
    Content,
    Graph,
    GraphBuilder,
    NodeKind,
)


@pytest.fixture
def converging_hunt() -> Graph:
    """A two-path hunt that merges:  start -> A -> merge ; start -> B -> merge -> end."""
    return (
        GraphBuilder()
        .node("start", kind=NodeKind.START)
        .node("A")
        .node("B")
        .node("merge")
        .node("end", kind=NodeKind.END)
        .connect("start", "A", content=Content(text="path A"))
        .connect("start", "B", content=Content(text="path B"))
        .connect("A", "merge", content=Content(text="half one"))
        .connect("B", "merge", content=Content(text="half two"))
        .connect("merge", "end", content=Content(text="the treasure"))
        .build()
    )


@pytest.fixture
def cipher_hunt() -> Graph:
    """A linear hunt: start -> cipher -> end, gated by a Caesar puzzle."""
    cipher = CaesarCipherPuzzle.from_plaintext("c1", plaintext="FOUNTAIN", shift=3)
    return (
        GraphBuilder()
        .node("start", kind=NodeKind.START, label="Welcome")
        .node("c1", payload=cipher, label="Caesar gate", notes="hide under the doormat")
        .node("end", kind=NodeKind.END, label="Treasure")
        .connect("start", "c1", content=Content(text="Your first clue is encoded."))
        .connect("c1", "end", content=Content(text="Go to the fountain."))
        .build()
    )
