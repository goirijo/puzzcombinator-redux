from __future__ import annotations

import pytest

from puzzcombinator import Content, GraphBuilder, NodeKind
from puzzcombinator.errors import GraphError


def test_fluent_build_returns_graph() -> None:
    graph = (
        GraphBuilder()
        .node("a", kind=NodeKind.START)
        .node("b", kind=NodeKind.END)
        .connect("a", "b", content=Content(text="hi"))
        .build()
    )
    assert set(graph.nodes) == {"a", "b"}
    assert list(graph.edges) == ["a->b"]


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
