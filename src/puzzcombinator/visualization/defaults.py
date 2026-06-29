"""Bridge between auto-layout and the workspace channel.

This is the one place in ``visualization`` that touches *both* the hunt-data model (it
needs a :class:`~puzzcombinator.core.graph.Graph` to compute positions) and the
workspace model. Keeping it here — not in :mod:`workspace` — is deliberate:
``workspace.py`` must stay graph-free (it references nodes by opaque id only), so the
graph-aware glue lives in its own module.

Two jobs, both used by the ``app`` layer when serving a hunt:

* :func:`default_workspace` — synthesize a starting workspace for a hunt that has never
  been opened in the editor: one auto-arranged view per graph, plus a single tab on the
  main graph's view.
* :func:`resolve_workspace` — given whatever was stored, return a workspace in which
  every node has a position: stored placements win, and any node the designer never
  placed (e.g. one added to the graph since) falls back to :func:`layered_layout`. So
  the editor always receives complete coordinates and never has to guess.
"""

from __future__ import annotations

from dataclasses import replace

from puzzcombinator.core.document import DEFAULT_GRAPH_ID
from puzzcombinator.core.graph import Graph
from puzzcombinator.visualization.layout import layered_layout
from puzzcombinator.visualization.workspace import Position, Tab, View, Workspace


def _auto_positions(graph: Graph) -> dict[str, Position]:
    """Auto-layout coordinates for every node, as workspace :class:`Position`\\ s."""
    return {nid: Position(x=p.x, y=p.y) for nid, p in layered_layout(graph).items()}


def _view_id(graph_id: str) -> str:
    return f"view-{graph_id}"


def default_workspace(graphs: dict[str, Graph], main_id: str = DEFAULT_GRAPH_ID) -> Workspace:
    """A starting workspace: an auto-arranged view per graph, one tab on the main view."""
    views = {
        _view_id(gid): View(graph=gid, title=gid, positions=_auto_positions(g))
        for gid, g in graphs.items()
    }
    main_view = _view_id(main_id if main_id in graphs else next(iter(graphs)))
    tab = Tab(id="tab-1", view=main_view)
    return Workspace(views=views, tabs=[tab], active_tab=tab.id)


def resolve_workspace(
    stored: Workspace | None, graphs: dict[str, Graph], main_id: str = DEFAULT_GRAPH_ID
) -> Workspace:
    """Complete a workspace so every node has a position (stored placements win).

    Returns a fresh :class:`Workspace`; ``stored`` is left untouched.
    """
    if stored is None:
        return default_workspace(graphs, main_id)
    views = {
        vid: replace(view, positions={**_auto_positions(graphs[view.graph]), **view.positions})
        if view.graph in graphs
        else view
        for vid, view in stored.views.items()
    }
    return replace(stored, views=views)
