from __future__ import annotations

import pytest

from puzzcombinator import Graph
from puzzcombinator.errors import GraphError


def test_incoming_and_outgoing(converging_hunt: Graph) -> None:
    merge_in = {e.source for e in converging_hunt.incoming("merge")}
    assert merge_in == {"A", "B"}
    start_out = {e.target for e in converging_hunt.outgoing("start")}
    assert start_out == {"A", "B"}


def test_start_and_end_node_ids(converging_hunt: Graph) -> None:
    assert set(converging_hunt.start_node_ids()) == {"start"}
    assert set(converging_hunt.end_node_ids()) == {"end"}


def test_wiring_is_deterministic(converging_hunt: Graph) -> None:
    merge = converging_hunt.nodes["merge"]
    assert merge.incoming_edge_ids == tuple(sorted(merge.incoming_edge_ids))


def test_node_and_edge_accessors(cipher_hunt: Graph) -> None:
    assert cipher_hunt.node("solve").id == "solve"
    assert cipher_hunt.edge("start->solve").source == "start"


def test_unknown_source_edge_raises() -> None:
    from puzzcombinator import Edge, Node

    with pytest.raises(GraphError, match="unknown source node"):
        Graph.assemble([Node(id="b")], [Edge(id="x", source="ghost", target="b")])


def test_same_artifact_reused_across_edges_is_allowed() -> None:
    # The same artifact is a single puzzle piece the designer may reuse in several
    # places (e.g. one combination unlocking several locks), so it may ride more
    # than one edge. Cross-edge id repeats are intentional reuse, not collisions.
    from puzzcombinator import GraphBuilder, TextArtifact

    combo = TextArtifact("1-2-3-4", id="combo")
    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    c = builder.node("c")
    builder.connect(a, b, combo)
    builder.connect(b, c, combo)
    graph = builder.build()

    assert graph.edge("a->b").content == (combo,)
    assert graph.edge("b->c").content == (combo,)


def test_duplicate_artifact_id_within_one_edge_is_rejected() -> None:
    from puzzcombinator import GraphBuilder, TextArtifact

    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    builder.connect(a, b, TextArtifact("one", id="dup"), TextArtifact("two", id="dup"))
    with pytest.raises(GraphError, match="duplicate artifact id"):
        builder.build()


def test_cycle_is_rejected() -> None:
    nodes = [n for n in _two_node_cycle()[0]]
    edges = _two_node_cycle()[1]
    with pytest.raises(GraphError, match="cycle"):
        Graph.assemble(nodes, edges)


def _two_node_cycle() -> tuple[list, list]:
    from puzzcombinator import Edge, Node

    nodes = [Node(id="a"), Node(id="b")]
    edges = [
        Edge(id="a->b", source="a", target="b"),
        Edge(id="b->a", source="b", target="a"),
    ]
    return nodes, edges
