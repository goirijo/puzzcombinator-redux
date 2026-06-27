"""The top-level hunt-data container: a :class:`HuntDocument` of named graphs.

A document is the *whole* treasure-hunt source of truth — currently one or more
:class:`~puzzcombinator.core.graph.Graph`\\ s keyed by id, with room to grow
additively (floating artifacts, geo-coordinates, types not yet invented) as new
fields without a schema migration. Identity lives here, on the map key, not on the
``Graph`` (which stays pure structure with value-equality intact).

This is **only the hunt data**. The editor's visual state — where nodes are drawn,
which views and tabs are open — is a *separate* channel living outside the core
library (in ``visualization``) and is deliberately kept out of this container so it can
never affect hunt-data round-trip equality. Core stays UI-ignorant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from puzzcombinator.core.graph import Graph

if TYPE_CHECKING:
    from puzzcombinator.rendering.fragment import Artifact

#: The id used for the single graph in the common "one hunt, one graph" case.
DEFAULT_GRAPH_ID = "main"


@dataclass
class HuntDocument:
    """A whole hunt: one or more :class:`Graph`\\ s keyed by id.

    Value-equality is inherited from the dataclass and from ``Graph`` (and
    ``dict[str, Graph]``) comparing by value, which is what keeps the
    ``from_dict(to_dict(doc)) == doc`` round-trip invariant intact.

    ``unplaced`` is the **scratch pool of loose artifacts** — ones the designer has
    created but not yet dropped onto an edge — keyed by the graph id they belong to.
    It lives here, at the document level, rather than on :class:`Graph`, which stays
    pure structure (nodes + edges) so its value-equality stays clean. A pooled
    artifact propagates to *every view* of its graph (just like a node does);
    placing it moves it out of the pool and into an ``edge.content``. This is real
    hunt data (lose it and you lose authoring work), so it is kept out of the UI-only
    workspace channel — only the artifacts' per-view *positions* live there.

    (A flatter, view-selected pool is the eventual normalized shape; keying by graph
    id now is the straightforward route, and the move to it is a bounded reshape.)
    """

    graphs: dict[str, Graph] = field(default_factory=dict)
    unplaced: dict[str, tuple[Artifact, ...]] = field(default_factory=dict)

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
