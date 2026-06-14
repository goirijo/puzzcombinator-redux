"""Fluent authoring API for assembling a hunt graph in Python."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from puzzcombinator.core.graph import Edge, Graph, Node
from puzzcombinator.errors import GraphError

if TYPE_CHECKING:
    from puzzcombinator.rendering.fragment import Artifact


class GraphBuilder:
    """Collects nodes and edges, then materializes an immutable :class:`Graph`.

    Author by capturing node handles and connecting them as you go::

        b = GraphBuilder()
        start = b.node(label="Kickoff")
        solve = b.node(action="solve", label="Opening cipher")
        b.connect(start, solve, *cipher.artifacts().values())
        hunt = b.build()

    :meth:`node` returns the new node's id (the handle for :meth:`connect`);
    :meth:`connect` returns ``self`` so edges can still be chained. :meth:`build`
    is the single place that wires and validates the graph.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, Edge] = {}
        self._node_seq = 0

    def node(
        self,
        id: str | None = None,
        *,
        action: str | None = None,
        label: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Add an action node and return its **id** — the handle you pass to
        :meth:`connect`.

        ``id`` is optional: omit it and the builder assigns a unique internal id,
        so you never have to invent one. Pass an explicit id only when you want a
        stable, readable handle. ``action`` is a free-form label ("solve",
        "find", …); ``notes`` is free-form designer text printed in the binder.
        """
        if id is None:
            id = self._auto_node_id()
        if id in self._nodes:
            raise GraphError(f"duplicate node id {id!r}")
        self._nodes[id] = Node(id=id, action=action, label=label, notes=notes)
        return id

    def connect(
        self,
        source: str,
        target: str,
        *artifacts: Artifact | Iterable[Artifact],
        id: str | None = None,
    ) -> GraphBuilder:
        """Add an edge from ``source`` to ``target`` carrying ``artifacts``.

        Each argument may be a single :class:`Artifact` or any iterable of them;
        iterables are flattened, so all of these place the same content::

            connect(a, b, art1, art2)                 # individual artifacts
            connect(a, b, *cw.artifacts().values())    # an unpacked iterable
            connect(a, b, tiles)                       # an iterable, as-is
            connect(a, b, prompt, tiles)               # mixed

        Many artifacts flowing from one action into another belong on **one**
        edge like this — an edge *is* that flow. Use separate edges only for
        genuinely distinct branches (a different ``source`` or ``target``), which
        is what the branch/merge gating in :mod:`~puzzcombinator.core.ordering`
        reads. An edge may carry no artifacts (a pure structural link).
        """
        edge_id = id if id is not None else self._auto_edge_id(source, target)
        if edge_id in self._edges:
            raise GraphError(f"duplicate edge id {edge_id!r}")
        content: list[Artifact] = []
        for item in artifacts:
            if isinstance(item, Iterable):
                content.extend(item)
            else:
                content.append(item)
        self._edges[edge_id] = Edge(
            id=edge_id, source=source, target=target, content=tuple(content)
        )
        return self

    def build(self) -> Graph:
        """Assemble, wire, and structurally validate the graph."""
        return Graph.assemble(list(self._nodes.values()), list(self._edges.values()))

    def _auto_node_id(self) -> str:
        """A unique ``n1``/``n2``/… id, skipping any explicitly-taken id."""
        while True:
            candidate = f"n{self._node_seq}"
            self._node_seq += 1
            if candidate not in self._nodes:
                return candidate

    def _auto_edge_id(self, source: str, target: str) -> str:
        base = f"{source}->{target}"
        if base not in self._edges:
            return base
        n = 2
        while f"{base}#{n}" in self._edges:
            n += 1
        return f"{base}#{n}"
