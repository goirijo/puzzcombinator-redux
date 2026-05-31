"""Fluent authoring API for assembling a hunt graph in Python."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from puzzcombinator.core.graph import Content, Edge, Graph, Node
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
        action: str | None = None,
        label: str | None = None,
        notes: str | None = None,
    ) -> GraphBuilder:
        """Add an action node. ``action`` is a free-form label ("solve", "find", …);
        ``notes`` is free-form designer text printed in the binder."""
        if id in self._nodes:
            raise GraphError(f"duplicate node id {id!r}")
        self._nodes[id] = Node(id=id, action=action, label=label, notes=notes)
        return self

    def connect(
        self,
        source: str,
        target: str,
        *,
        text: str | None = None,
        data: dict[str, Any] | None = None,
        puzzle: Puzzle | None = None,
        content: Content | None = None,
        id: str | None = None,
    ) -> GraphBuilder:
        """Add an edge from ``source`` to ``target``.

        Pass ``content`` directly, or any of ``text`` / ``data`` / ``puzzle`` as a
        shorthand to build the :class:`Content` (e.g. ``connect(a, b, puzzle=cw)``
        or ``connect(a, b, text="go to the kitchen")``).
        """
        if content is None and (text is not None or data is not None or puzzle is not None):
            content = Content(text=text, data=data or {}, puzzle=puzzle)
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
