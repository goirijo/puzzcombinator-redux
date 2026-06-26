"""Tests for the layout↔workspace bridge: default synthesis and position fallback."""

from __future__ import annotations

from puzzcombinator import Graph, GraphBuilder
from puzzcombinator.visualization.defaults import default_workspace, resolve_workspace
from puzzcombinator.visualization.workspace import Position, Tab, View, Viewport, Workspace


def _two_node_graph() -> Graph:
    b = GraphBuilder()
    b.node("start")
    b.node("end")
    return b.build()


def test_default_workspace_arranges_every_node_with_one_active_tab() -> None:
    graph = _two_node_graph()
    ws = default_workspace({"main": graph})

    assert ws.active_tab is not None
    tab = next(t for t in ws.tabs if t.id == ws.active_tab)
    view = ws.views[tab.view]
    assert view.graph == "main"
    assert set(view.positions) == {"start", "end"}  # auto-laid-out
    assert isinstance(tab.viewport, Viewport)  # framing lives on the tab


def test_resolve_none_synthesizes_default() -> None:
    graph = _two_node_graph()
    assert resolve_workspace(None, {"main": graph}) == default_workspace({"main": graph})


def test_resolve_keeps_stored_positions_and_fills_missing() -> None:
    # A stored view places only "start"; "end" was never placed (e.g. added later). The
    # stored placement must win, and the missing node must be filled from auto-layout.
    graph = _two_node_graph()
    stored = Workspace(
        views={"v1": View(graph="main", title="Main", positions={"start": Position(999.0, 42.0)})},
        tabs=[Tab(id="t1", view="v1")],
        active_tab="t1",
    )
    resolved = resolve_workspace(stored, {"main": graph})

    positions = resolved.views["v1"].positions
    assert positions["start"] == Position(999.0, 42.0)  # stored wins
    assert "end" in positions  # missing node filled from layout
    assert positions["end"] != Position(999.0, 42.0)


def test_resolve_ignores_views_over_unknown_graphs() -> None:
    # A view referencing a graph that isn't present is left untouched (no crash).
    stored = Workspace(
        views={"v1": View(graph="ghost", title="Ghost", positions={})},
        tabs=[],
        active_tab=None,
    )
    resolved = resolve_workspace(stored, {"main": _two_node_graph()})
    assert resolved.views["v1"].positions == {}
