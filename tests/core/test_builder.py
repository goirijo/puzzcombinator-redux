from __future__ import annotations

import pytest

from puzzcombinator import GraphBuilder
from puzzcombinator.errors import GraphError


def test_fluent_build_returns_graph() -> None:
    graph = (
        GraphBuilder()
        .node("a", action="start")
        .node("b", action="finish")
        .connect("a", "b", text="hi")
        .build()
    )
    assert set(graph.nodes) == {"a", "b"}
    assert list(graph.edges) == ["a->b"]
    assert graph.nodes["a"].action == "start"
    assert graph.edges["a->b"].content is not None
    assert graph.edges["a->b"].content.text == "hi"


def test_auto_edge_id_disambiguates() -> None:
    graph = GraphBuilder().node("a").node("b").connect("a", "b").connect("a", "b").build()
    assert set(graph.edges) == {"a->b", "a->b#2"}


def test_auto_edge_id_disambiguates_three_times() -> None:
    graph = (
        GraphBuilder()
        .node("a")
        .node("b")
        .connect("a", "b")
        .connect("a", "b")
        .connect("a", "b")
        .build()
    )
    assert set(graph.edges) == {"a->b", "a->b#2", "a->b#3"}


def test_connect_puts_puzzle_on_edge() -> None:
    from puzzcombinator import CaesarCipherPuzzle

    cipher = CaesarCipherPuzzle.from_plaintext("c1", plaintext="HI", shift=1)
    graph = GraphBuilder().node("a").node("b").connect("a", "b", puzzle=cipher).build()
    content = graph.edges["a->b"].content
    assert content is not None
    assert content.puzzle is cipher


def test_explicit_edge_id_is_kept() -> None:
    graph = GraphBuilder().node("a").node("b").connect("a", "b", id="link").build()
    assert "link" in graph.edges


def test_duplicate_node_id_raises() -> None:
    builder = GraphBuilder().node("a")
    with pytest.raises(GraphError, match="duplicate node id"):
        builder.node("a")


def test_duplicate_edge_id_raises() -> None:
    builder = GraphBuilder().node("a").node("b").connect("a", "b", id="x")
    with pytest.raises(GraphError, match="duplicate edge id"):
        builder.connect("a", "b", id="x")


def test_dangling_edge_raises_on_build() -> None:
    builder = GraphBuilder().node("a").connect("a", "ghost")
    with pytest.raises(GraphError, match="unknown target node"):
        builder.build()
