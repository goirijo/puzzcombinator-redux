"""The top-level hunt-data container: a :class:`HuntDocument` of named graphs.

A document is the *whole* treasure-hunt source of truth — currently one or more
:class:`~puzzcombinator.core.graph.Graph`\\ s keyed by id, with room to grow
additively (floating artifacts, geo-coordinates, types not yet invented) as new
fields without a schema migration. Identity lives here, on the map key, not on the
``Graph`` (which stays pure structure with value-equality intact).

This is **only the hunt data**. The canvas/visualization state — where nodes are
drawn, which view, collapsed/expanded — is a *separate* channel (see
``app/canvas.py``) and is deliberately kept out of this container so it can never
affect hunt-data round-trip equality.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from puzzcombinator.core.graph import Graph

#: The id used for the single graph in the common "one hunt, one graph" case.
DEFAULT_GRAPH_ID = "main"


@dataclass
class HuntDocument:
    """A whole hunt: one or more :class:`Graph`\\ s keyed by id.

    Value-equality is inherited from the dataclass and from ``Graph`` (and
    ``dict[str, Graph]``) comparing by value, which is what keeps the
    ``from_dict(to_dict(doc)) == doc`` round-trip invariant intact.
    """

    graphs: dict[str, Graph] = field(default_factory=dict)

    @classmethod
    def single(cls, graph: Graph, graph_id: str = DEFAULT_GRAPH_ID) -> HuntDocument:
        """Wrap one graph as a document (the common single-graph case)."""
        return cls(graphs={graph_id: graph})

    @property
    def main(self) -> Graph:
        """The default graph (``DEFAULT_GRAPH_ID``). For single-graph documents."""
        return self.graphs[DEFAULT_GRAPH_ID]

    def graph(self, graph_id: str) -> Graph:
        """The graph with the given id."""
        return self.graphs[graph_id]
