"""Tests for the pure layered-layout function.

These exercise the layering logic directly — no server, no browser — which is why
this is the first thing we build and the component we can trust most.
"""

from __future__ import annotations

from puzzcombinator import Graph, GraphBuilder
from puzzcombinator.visualization.layout import (
    COLUMN_WIDTH,
    MARGIN_X,
    MARGIN_Y,
    ROW_HEIGHT,
    layered_layout,
)


def test_linear_chain_increments_layers(cipher_hunt: Graph) -> None:
    # start -> solve -> end  =>  one node per column, all in row 0.
    pos = layered_layout(cipher_hunt)
    assert pos["start"].layer == 0
    assert pos["solve"].layer == 1
    assert pos["end"].layer == 2
    assert {p.row for p in pos.values()} == {0}


def test_linear_chain_pixel_coordinates(cipher_hunt: Graph) -> None:
    pos = layered_layout(cipher_hunt)
    assert (pos["start"].x, pos["start"].y) == (MARGIN_X, MARGIN_Y)
    assert pos["solve"].x == MARGIN_X + COLUMN_WIDTH
    assert pos["end"].x == MARGIN_X + 2 * COLUMN_WIDTH


def test_branch_then_merge(converging_hunt: Graph) -> None:
    # start -> A,B (layer 1) -> merge (layer 2) -> end (layer 3).
    pos = layered_layout(converging_hunt)
    assert pos["start"].layer == 0
    assert pos["A"].layer == 1
    assert pos["B"].layer == 1
    assert pos["merge"].layer == 2
    assert pos["end"].layer == 3


def test_branch_siblings_get_distinct_rows(converging_hunt: Graph) -> None:
    # A and B share layer 1, so they must occupy different vertical slots.
    pos = layered_layout(converging_hunt)
    assert {pos["A"].row, pos["B"].row} == {0, 1}
    assert pos["A"].y != pos["B"].y
    # Rows step down by exactly ROW_HEIGHT.
    assert abs(pos["A"].y - pos["B"].y) == ROW_HEIGHT


def test_merge_layer_is_max_of_paths() -> None:
    # A long path and a short path into the same merge node: the merge sits past
    # the *longer* path, never overlapping it.
    b = GraphBuilder()
    start = b.node("start")
    mid = b.node("mid")  # only on the long path
    short_target = b.node("merge")
    b.connect(start, mid)
    b.connect(mid, short_target)  # long path: start -> mid -> merge  (merge at layer 2)
    b.connect(start, short_target)  # short path: start -> merge directly
    pos = layered_layout(b.build())
    assert pos["merge"].layer == 2


def test_disconnected_roots_share_layer_zero() -> None:
    b = GraphBuilder()
    b.node("x")
    b.node("y")
    pos = layered_layout(b.build())
    assert pos["x"].layer == 0
    assert pos["y"].layer == 0
    assert {pos["x"].row, pos["y"].row} == {0, 1}


def test_empty_graph_yields_empty_layout() -> None:
    empty = Graph(nodes={}, edges={})
    assert layered_layout(empty) == {}
