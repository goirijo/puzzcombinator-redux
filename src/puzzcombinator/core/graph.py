"""The artifact-agnostic graph model.

A hunt is a directed graph of :class:`Node`s (actions) connected by
:class:`Edge`s. Each edge carries a tuple of :class:`Artifact`\\ s — the
information flowing from one action to the next (a clue, a cipher, a grid, a pair
of coordinates). A node is a pure *action* (solve, find, move, …); it consumes its
incoming edges and produces its outgoing edges. Artifacts live on edges, not
nodes, so this module references the ``Artifact`` ABC only for typing.

The model is stateless. Identity is by string ``id`` (never object identity and
never content), edges reference nodes by id, and per-node wiring
(``incoming_edge_ids`` / ``outgoing_edge_ids``) is *recomputed* from the edge
list rather than serialized. This keeps the object graph acyclic and gives clean
value-equality for serialization round-trips.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from puzzcombinator.errors import GraphError

if TYPE_CHECKING:
    from puzzcombinator.rendering.fragment import Artifact


@dataclass
class Node:
    """A pure action in the hunt: an abstract bundle of inputs and outputs.

    A node consumes its incoming edges and produces its outgoing edges. ``action``
    is a free-form label for what the action is ("solve", "find", "move", …) —
    extensible, with no fixed set. There is no payload and no node "kind": artifacts
    live on edges, and start/end are simply the nodes that lack incoming/outgoing
    edges.
    """

    id: str
    action: str | None = None
    label: str | None = None
    notes: str | None = None
    # Recomputed from the edge list by Graph; never serialized.
    incoming_edge_ids: tuple[str, ...] = ()
    outgoing_edge_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Edge:
    """A directed connection from ``source`` node to ``target`` node.

    Stores only node ids (never object references), so the object graph stays
    acyclic and serialization is trivial.
    """

    id: str
    source: str
    target: str
    content: tuple[Artifact, ...] = ()


@dataclass
class Graph:
    """A whole hunt: nodes and edges keyed by id."""

    nodes: dict[str, Node]
    edges: dict[str, Edge]

    @classmethod
    def assemble(cls, nodes: list[Node], edges: list[Edge]) -> Graph:
        """Build a validated graph from node/edge lists.

        Computes each node's wiring from the edges, then runs
        :meth:`validate_structure`. This is the single entry point used by both
        the builder and the deserializer, so a loaded graph is wired identically
        to a freshly built one (key to round-trip equality).
        """
        graph = cls(
            nodes={n.id: n for n in nodes},
            edges={e.id: e for e in edges},
        )
        graph.validate_structure()
        graph._rewire()
        return graph

    def _rewire(self) -> None:
        """Recompute every node's incoming/outgoing edge ids from the edges.

        Edges are visited in sorted-id order so the resulting tuples are
        deterministic regardless of insertion order.
        """
        incoming: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        outgoing: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for edge_id in sorted(self.edges):
            edge = self.edges[edge_id]
            outgoing[edge.source].append(edge_id)
            incoming[edge.target].append(edge_id)
        for node_id, node in self.nodes.items():
            node.incoming_edge_ids = tuple(incoming[node_id])
            node.outgoing_edge_ids = tuple(outgoing[node_id])

    def validate_structure(self) -> None:
        """Raise :class:`GraphError` on dangling edges, a repeated artifact id within
        one edge, or cycles."""
        for edge in self.edges.values():
            if edge.source not in self.nodes:
                raise GraphError(f"edge {edge.id!r} has unknown source node {edge.source!r}")
            if edge.target not in self.nodes:
                raise GraphError(f"edge {edge.id!r} has unknown target node {edge.target!r}")
        self._check_no_duplicate_ids_within_edge()
        self._check_acyclic()

    def _check_no_duplicate_ids_within_edge(self) -> None:
        """Reject an artifact id appearing more than once on a single edge.

        The same artifact may be *reused* across multiple edges (one piece used in
        several places — e.g. a combination unlocking several locks); ids are unique
        by construction, so cross-edge repeats are intentional reuse, not collisions.
        Within one edge a repeat is just redundant, so it is rejected. (This stays
        artifact-agnostic — it only reads the ``Artifact`` ABC's ``id``.) Edges are
        visited in order for a deterministic message.
        """
        for edge_id in sorted(self.edges):
            seen: set[str] = set()
            for artifact in self.edges[edge_id].content:
                if artifact.id in seen:
                    raise GraphError(
                        f"duplicate artifact id {artifact.id!r} within edge {edge_id!r}"
                    )
                seen.add(artifact.id)

    def _check_acyclic(self) -> None:
        indegree: dict[str, int] = dict.fromkeys(self.nodes, 0)
        for edge in self.edges.values():
            indegree[edge.target] += 1
        ready = [nid for nid, deg in indegree.items() if deg == 0]
        seen = 0
        while ready:
            node_id = ready.pop()
            seen += 1
            for edge in self.edges.values():
                if edge.source == node_id:
                    indegree[edge.target] -= 1
                    if indegree[edge.target] == 0:
                        ready.append(edge.target)
        if seen != len(self.nodes):
            stuck = sorted(nid for nid, deg in indegree.items() if deg > 0)
            raise GraphError(f"graph has a cycle involving: {stuck}")

    def node(self, node_id: str) -> Node:
        return self.nodes[node_id]

    def edge(self, edge_id: str) -> Edge:
        return self.edges[edge_id]

    def incoming(self, node_id: str) -> list[Edge]:
        """Edges entering ``node_id`` (its inputs)."""
        return [self.edges[eid] for eid in self.nodes[node_id].incoming_edge_ids]

    def outgoing(self, node_id: str) -> list[Edge]:
        """Edges leaving ``node_id`` (its outputs)."""
        return [self.edges[eid] for eid in self.nodes[node_id].outgoing_edge_ids]

    def start_node_ids(self) -> list[str]:
        """Ids of nodes with no incoming edges (the hunt's entry points).

        Returns ids, not :class:`Node` objects — ids are the currency every
        query speaks; call :meth:`node` to materialize one.
        """
        return [nid for nid, n in self.nodes.items() if not n.incoming_edge_ids]

    def end_node_ids(self) -> list[str]:
        """Ids of nodes with no outgoing edges (the hunt's terminal points)."""
        return [nid for nid, n in self.nodes.items() if not n.outgoing_edge_ids]
