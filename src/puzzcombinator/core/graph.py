"""The puzzle-agnostic graph model.

A hunt is a directed graph of :class:`Node`s connected by :class:`Edge`s. Each
edge may carry :class:`Content` — the clue/data revealed downstream when its
source node is solved. The graph layer knows nothing about puzzles: a node holds
an *optional* puzzle payload by composition, so this module never imports
``puzzles``.

The model is stateless. Identity is by string ``id`` (never object identity and
never content), edges reference nodes by id, and per-node wiring
(``incoming_edge_ids`` / ``outgoing_edge_ids``) is *recomputed* from the edge
list rather than serialized. This keeps the object graph acyclic and gives clean
value-equality for serialization round-trips.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from puzzcombinator.errors import GraphError

if TYPE_CHECKING:
    from puzzcombinator.puzzles.base import Puzzle


class NodeKind(Enum):
    """The role a node plays in the hunt."""

    START = "START"
    PUZZLE = "PUZZLE"
    END = "END"
    STEP = "STEP"


@dataclass(frozen=True)
class Content:
    """The clue/data that flows along an edge (revealed downstream).

    ``text`` is human-readable; ``data`` is an optional JSON-safe structured
    payload for machine-consumed clues.
    """

    text: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Node:
    """One step in the hunt: a puzzle, a physical action, or a marker.

    ``payload`` is the optional :class:`~puzzcombinator.puzzles.base.Puzzle`. A
    physical/non-printable step is simply a node with ``payload=None`` whose edge
    :class:`Content` carries the instruction-in and object-out.
    """

    id: str
    payload: Puzzle | None = None
    kind: NodeKind = NodeKind.PUZZLE
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
    content: Content | None = None


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
        """Raise :class:`GraphError` on dangling edges or cycles."""
        for edge in self.edges.values():
            if edge.source not in self.nodes:
                raise GraphError(f"edge {edge.id!r} has unknown source node {edge.source!r}")
            if edge.target not in self.nodes:
                raise GraphError(f"edge {edge.id!r} has unknown target node {edge.target!r}")
        self._check_acyclic()

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

    def start_nodes(self) -> list[Node]:
        """Nodes with no incoming edges (or explicitly marked START)."""
        return [
            n for n in self.nodes.values() if not n.incoming_edge_ids or n.kind is NodeKind.START
        ]

    def end_nodes(self) -> list[Node]:
        """Nodes with no outgoing edges (or explicitly marked END)."""
        return [n for n in self.nodes.values() if not n.outgoing_edge_ids or n.kind is NodeKind.END]
