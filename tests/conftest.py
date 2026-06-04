"""Shared fixtures."""

from __future__ import annotations

import pytest

from puzzcombinator import (
    Audience,
    CaesarCipherPuzzle,
    Graph,
    GraphBuilder,
    TextArtifact,
)


@pytest.fixture
def converging_hunt() -> Graph:
    """A two-path hunt that merges:  start -> A -> merge ; start -> B -> merge -> end.

    Uses explicit ids because the tests reference these nodes by id, but still
    threads the handles ``node()`` returns into ``connect`` (never re-typing them).
    Each edge carries a single :class:`TextArtifact` clue.
    """
    builder = GraphBuilder()
    start = builder.node("start")
    a = builder.node("A", action="find")
    b = builder.node("B", action="find")
    merge = builder.node("merge", action="combine")
    end = builder.node("end")
    return (
        builder.connect(start, a, TextArtifact("path A", id="path-a"))
        .connect(start, b, TextArtifact("path B", id="path-b"))
        .connect(a, merge, TextArtifact("half one", id="half-one"))
        .connect(b, merge, TextArtifact("half two", id="half-two"))
        .connect(merge, end, TextArtifact("the treasure", id="treasure"))
        .build()
    )


@pytest.fixture
def cipher_hunt() -> Graph:
    """A linear hunt: start -> solve -> end, with a Caesar puzzle on the first edge.

    The first edge carries the cipher's player artifact *and* its game-master
    artifact (the revealed answer); the second carries a plain text clue.
    """
    cipher = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    builder = GraphBuilder()
    start = builder.node("start", label="Welcome")
    solve = builder.node(
        "solve", action="solve", label="Caesar gate", notes="hide under the doormat"
    )
    end = builder.node("end", label="Treasure")
    return (
        builder.connect(
            start,
            solve,
            cipher.artifacts("cipher"),
            cipher.artifacts("cipher", audience=Audience.GAME_MASTER),
        )
        .connect(solve, end, TextArtifact("Go to the fountain.", id="fountain"))
        .build()
    )
