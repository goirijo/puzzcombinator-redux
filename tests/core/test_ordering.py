from __future__ import annotations

import pytest

from puzzcombinator import (
    Content,
    Graph,
    GraphBuilder,
    NodeKind,
    chronological_order,
    required_inputs,
    unlocked_outputs,
)


def _index(order: list, node_id: str) -> int:
    return [n.id for n in order].index(node_id)


def test_linear_order(cipher_hunt: Graph) -> None:
    order = [n.id for n in chronological_order(cipher_hunt)]
    assert order == ["start", "c1", "end"]


def test_merge_gated_after_both_paths(converging_hunt: Graph) -> None:
    order = chronological_order(converging_hunt)
    assert _index(order, "merge") > _index(order, "A")
    assert _index(order, "merge") > _index(order, "B")
    assert _index(order, "end") == len(order) - 1


@pytest.mark.parametrize("flip", [False, True])
def test_order_is_insertion_independent(flip: bool) -> None:
    builder = GraphBuilder().node("start", kind=NodeKind.START)
    builder.node("A").node("B").node("merge")
    if flip:
        builder.connect("start", "B").connect("start", "A")
        builder.connect("B", "merge").connect("A", "merge")
    else:
        builder.connect("start", "A").connect("start", "B")
        builder.connect("A", "merge").connect("B", "merge")
    order = [n.id for n in chronological_order(builder.build())]
    assert order == ["start", "A", "B", "merge"]


def test_start_argument_is_preferred_seed() -> None:
    # Two independent roots; passing start= biases which is emitted first.
    builder = GraphBuilder().node("x", kind=NodeKind.START).node("y", kind=NodeKind.START)
    graph = builder.build()
    assert [n.id for n in chronological_order(graph, start="y")][0] == "y"
    assert [n.id for n in chronological_order(graph, start="x")][0] == "x"


def test_cycle_raises() -> None:
    from puzzcombinator import Edge, Node

    graph = Graph(
        nodes={"a": Node(id="a"), "b": Node(id="b")},
        edges={
            "a->b": Edge(id="a->b", source="a", target="b"),
            "b->a": Edge(id="b->a", source="b", target="a"),
        },
    )
    graph._rewire()
    with pytest.raises(Exception, match="cycle"):
        chronological_order(graph)


def test_required_inputs(converging_hunt: Graph) -> None:
    texts = {c.text for c in required_inputs(converging_hunt, "merge")}
    assert texts == {"half one", "half two"}


def test_unlocked_outputs_gated_by_validation(cipher_hunt: Graph) -> None:
    assert unlocked_outputs(cipher_hunt, "c1", "fountain")
    assert unlocked_outputs(cipher_hunt, "c1", "FOUNTAIN")
    assert unlocked_outputs(cipher_hunt, "c1", "wrong") == []


def test_unlocked_outputs_for_payloadless_step() -> None:
    graph = (
        GraphBuilder()
        .node("s", kind=NodeKind.START)
        .node("t", kind=NodeKind.END)
        .connect("s", "t", content=Content(text="key"))
        .build()
    )
    # No puzzle to solve -> outputs flow unconditionally.
    out = unlocked_outputs(graph, "s", "anything")
    assert [c.text for c in out] == ["key"]
