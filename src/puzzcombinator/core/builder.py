"""Fluent authoring API for assembling a hunt graph in Python."""

from __future__ import annotations

from typing import TYPE_CHECKING

from puzzcombinator.core.graph import Content, Edge, Graph, Node, NodeKind
from puzzcombinator.errors import GraphError

if TYPE_CHECKING:
    from puzzcombinator.puzzles.base import Puzzle


class GraphBuilder:
    """Collects nodes and edges, then materializes an immutable :class:`Graph`.

    Every method returns ``self`` for chaining. :meth:`build` is the single
    place that wires and validates the graph.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, Edge] = {}

    def node(
        self,
        id: str,
        *,
        payload: Puzzle | None = None,
        kind: NodeKind = NodeKind.PUZZLE,
        label: str | None = None,
        notes: str | None = None,
    ) -> GraphBuilder:
        """Add a node. ``notes`` is free-form designer text printed in the binder."""
        if id in self._nodes:
            raise GraphError(f"duplicate node id {id!r}")
        self._nodes[id] = Node(id=id, payload=payload, kind=kind, label=label, notes=notes)
        return self

    def connect(
        self,
        source: str,
        target: str,
        *,
        content: Content | None = None,
        id: str | None = None,
    ) -> GraphBuilder:
        """Add an edge carrying optional ``content`` from ``source`` to ``target``."""
        edge_id = id if id is not None else self._auto_edge_id(source, target)
        if edge_id in self._edges:
            raise GraphError(f"duplicate edge id {edge_id!r}")
        self._edges[edge_id] = Edge(id=edge_id, source=source, target=target, content=content)
        return self

    def build(self) -> Graph:
        """Assemble, wire, and structurally validate the graph."""
        return Graph.assemble(list(self._nodes.values()), list(self._edges.values()))

    def _auto_edge_id(self, source: str, target: str) -> str:
        base = f"{source}->{target}"
        if base not in self._edges:
            return base
        n = 2
        while f"{base}#{n}" in self._edges:
            n += 1
        return f"{base}#{n}"
