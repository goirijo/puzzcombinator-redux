"""Round-trip tests for the workspace channel.

The whole point of this channel is independence: it carries only UI state and is
serializable on its own, with no graph anywhere in sight. So these tests build,
serialize, and reload a workspace without ever touching the hunt-data layer — and one
of them loads a hand-written, graph-free JSON document to prove the standalone
("could be two files") shape.
"""

from __future__ import annotations

from puzzcombinator.visualization.workspace import (
    Position,
    Tab,
    View,
    Viewport,
    Workspace,
    workspace_from_dict,
    workspace_from_json,
    workspace_to_dict,
    workspace_to_json,
)


def _sample_workspace() -> Workspace:
    return Workspace(
        views={
            "v1": View(
                graph="main",
                title="Main",
                positions={"start": Position(60.0, 60.0), "end": Position(280.0, 60.0)},
            ),
            # A second view of the SAME graph that hides the unplaced pool — the per-view
            # display distinction this flag exists for.
            "v2": View(graph="main", title="Cellar", positions={}, show_unplaced=False),
        },
        # Two tabs on the SAME view, framed differently — the whole point of per-tab viewport.
        tabs=[
            Tab(id="t1", view="v1", viewport=Viewport(-120.0, 40.0, 0.85)),
            Tab(id="t2", view="v1"),
        ],
        active_tab="t1",
    )


def test_dict_round_trip() -> None:
    ws = _sample_workspace()
    assert workspace_from_dict(workspace_to_dict(ws)) == ws


def test_json_round_trip() -> None:
    ws = _sample_workspace()
    assert workspace_from_json(workspace_to_json(ws)) == ws


def test_empty_workspace_round_trips() -> None:
    ws = Workspace()
    assert workspace_from_dict(workspace_to_dict(ws)) == ws
    assert ws.active_tab is None


def test_loads_standalone_graphless_json() -> None:
    # A workspace document with no graph present anywhere — the "could be two files"
    # invariant. It references nodes purely by opaque id.
    text = """
    {
      "views": {
        "v1": { "graph": "main", "title": "Main",
                "positions": { "start": {"x": 60, "y": 60} } }
      },
      "tabs": [ { "id": "t1", "view": "v1",
                  "viewport": {"x": 0, "y": 0, "zoom": 1} } ],
      "active_tab": "t1"
    }
    """
    ws = workspace_from_json(text)
    assert ws.active_tab == "t1"
    assert ws.views["v1"].title == "Main"
    assert ws.views["v1"].positions["start"] == Position(60.0, 60.0)
    assert ws.tabs[0].view == "v1"
    assert ws.tabs[0].viewport == Viewport(0.0, 0.0, 1.0)


def test_tab_without_viewport_defaults_to_identity() -> None:
    # Back-compat / minimal docs: a tab dict with no viewport key loads as the identity.
    text = '{ "views": {}, "tabs": [ { "id": "t1", "view": "v1" } ] }'
    ws = workspace_from_json(text)
    assert ws.tabs[0].viewport == Viewport(0.0, 0.0, 1.0)


def test_positions_and_viewport_preserved() -> None:
    ws = workspace_from_dict(workspace_to_dict(_sample_workspace()))
    assert ws.views["v1"].positions["end"] == Position(280.0, 60.0)  # positions on the view
    assert ws.tabs[0].viewport == Viewport(-120.0, 40.0, 0.85)  # framing on the tab
    assert ws.views["v2"].positions == {}
    assert ws.tabs[1].viewport == Viewport(0.0, 0.0, 1.0)  # defaulted


def test_show_unplaced_preserved_per_view() -> None:
    ws = workspace_from_dict(workspace_to_dict(_sample_workspace()))
    assert ws.views["v1"].show_unplaced is True  # defaulted on construction
    assert ws.views["v2"].show_unplaced is False  # the hide-pool view round-trips


def test_view_without_show_unplaced_defaults_to_shown() -> None:
    # Back-compat / minimal docs: a view dict written before this flag existed loads as
    # "show the pool" rather than failing — same forgiving read as a missing tab viewport.
    text = '{ "views": { "v1": { "graph": "main", "title": "Main" } }, "tabs": [] }'
    ws = workspace_from_json(text)
    assert ws.views["v1"].show_unplaced is True
