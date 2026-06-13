from __future__ import annotations

import pytest

from puzzcombinator import (
    Graph,
    GraphBuilder,
    produced_outputs,
    required_inputs,
    topological_order,
)


def _index(order: list, node_id: str) -> int:
    return [n.id for n in order].index(node_id)


def test_linear_order(cipher_hunt: Graph) -> None:
    order = [n.id for n in topological_order(cipher_hunt)]
    assert order == ["start", "solve", "end"]


def test_merge_gated_after_both_paths(converging_hunt: Graph) -> None:
    order = topological_order(converging_hunt)
    assert _index(order, "merge") > _index(order, "A")
    assert _index(order, "merge") > _index(order, "B")
    assert _index(order, "end") == len(order) - 1


@pytest.mark.parametrize("flip", [False, True])
def test_order_is_insertion_independent(flip: bool) -> None:
    builder = GraphBuilder()
    start = builder.node("start")
    a = builder.node("A")
    b = builder.node("B")
    merge = builder.node("merge")
    if flip:
        builder.connect(start, b).connect(start, a)
        builder.connect(b, merge).connect(a, merge)
    else:
        builder.connect(start, a).connect(start, b)
        builder.connect(a, merge).connect(b, merge)
    order = [n.id for n in topological_order(builder.build())]
    assert order == ["start", "A", "B", "merge"]


def test_start_argument_is_preferred_seed() -> None:
    # Two independent roots; passing start= biases which is emitted first.
    builder = GraphBuilder()
    builder.node("x")
    builder.node("y")
    graph = builder.build()
    assert [n.id for n in topological_order(graph, start="y")][0] == "y"
    assert [n.id for n in topological_order(graph, start="x")][0] == "x"


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
        topological_order(graph)


def test_required_inputs(converging_hunt: Graph) -> None:
    texts = {a.text for a in required_inputs(converging_hunt, "merge")}
    assert texts == {"half one", "half two"}


def test_produced_outputs(converging_hunt: Graph) -> None:
    texts = {a.text for a in produced_outputs(converging_hunt, "start")}
    assert texts == {"path A", "path B"}


def test_produced_outputs_for_physical_step() -> None:
    # A pure action node carries a plain text artifact; its output flows on the edge.
    from puzzcombinator import TextArtifact

    builder = GraphBuilder()
    s = builder.node("s")
    t = builder.node("t")
    graph = builder.connect(s, t, TextArtifact("key under the mat")).build()
    assert [a.text for a in produced_outputs(graph, "s")] == ["key under the mat"]
