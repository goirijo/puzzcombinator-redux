"""The workspace channel — the editor's UI state — kept strictly separate from the
hunt data.

This is the second of the two persisted channels (the first being hunt data, in
``serialization``/``core.document``). It carries purely *front-facing* state — which
views exist, which tabs are open, where nodes are drawn, how each tab is framed — and
**never** any treasure-hunt data. The separation is a hard invariant: lose the whole
workspace and you have lost only *visualizations*, nothing about the hunt. So this
module never imports the graph model and references nodes only by opaque id; a
workspace is serializable and unit-testable entirely on its own (a workspace-only JSON
is a valid fixture, with no graph present).

The mental model is **vim**:

* A **view** is a *buffer* — a created, persistent arrangement of one graph: node
  positions and a title. It exists whether or not anything is displaying it.
* A **tab** is a *window* — a display slot that *references* a view by id and carries its
  own framing (pan/zoom). Several tabs may show the same view, each framed differently
  (zoomed into a different part of the same graph); closing a tab does not destroy the
  view. (Framing lives on the tab, not the view — mirroring how two vim windows onto one
  buffer each keep their own scroll position.)
* The **workspace** is the whole channel: every view, every tab, and the active tab.

On disk the workspace is one top-level entry alongside ``graphs`` in the hunt file (it
*could* be a separate file — the codec here is self-contained — but in practice the
``app`` layer stitches the two channels into one document). A node with no stored
position in its view falls back to the auto-arranged
:func:`~puzzcombinator.visualization.layout.layered_layout`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# The on-disk workspace dict keys, defined right here. The core serialization package
# is UI-ignorant and intentionally knows none of these.
KEY_VIEWS = "views"
KEY_TABS = "tabs"
KEY_ACTIVE_TAB = "active_tab"
KEY_VIEW_GRAPH = "graph"  # a view's reference to the graph id it draws
KEY_VIEW_TITLE = "title"
KEY_VIEW_POSITIONS = "positions"
KEY_VIEW_SHOW_UNPLACED = "show_unplaced"  # per-view: draw the graph's unplaced artifacts?
KEY_TAB_ID = "id"
KEY_TAB_VIEW = "view"  # a tab's reference to the view id it displays
KEY_VIEWPORT = "viewport"


@dataclass(frozen=True)
class Position:
    """A node's pixel position within a view."""

    x: float
    y: float


@dataclass(frozen=True)
class Viewport:
    """A tab's pan/zoom framing of its view (React Flow's viewport)."""

    x: float
    y: float
    zoom: float


#: React Flow's identity viewport — the framing a never-framed tab starts at. A tab
#: still showing this is treated as "auto-fit me" by the editor.
IDENTITY_VIEWPORT = Viewport(x=0.0, y=0.0, zoom=1.0)


@dataclass
class View:
    """One visual arrangement of a graph (a *buffer*).

    ``graph`` is the id of the graph this view draws. ``title`` is the view's name (a
    tab showing this view displays this title). ``positions`` maps node id →
    :class:`Position` for nodes the designer has placed; nodes absent from the map fall
    back to auto-layout. Framing (pan/zoom) lives on the :class:`Tab`, not here, so two
    tabs on one view can each remember their own camera.

    ``show_unplaced`` is a per-view *display* choice: whether this view draws the
    graph's unplaced (loose) artifacts. The pool itself belongs to the hunt data and is
    shared by every view of the graph; this flag only governs whether *this* arrangement
    renders it — so two views of one graph can differ solely in showing the pool or not
    (the visualization analog of per-view node collapse). Defaults to showing them.
    """

    graph: str
    title: str
    positions: dict[str, Position] = field(default_factory=dict)
    show_unplaced: bool = True


@dataclass
class Tab:
    """One open display slot (a *window*) referencing a view by id.

    ``viewport`` is this tab's saved pan/zoom framing — per tab, not per view, so two
    tabs on the same view can be zoomed into different parts of the graph.
    """

    id: str
    view: str
    viewport: Viewport = IDENTITY_VIEWPORT


@dataclass
class Workspace:
    """The editor's whole UI channel: every view, every tab, and the active tab."""

    views: dict[str, View] = field(default_factory=dict)
    tabs: list[Tab] = field(default_factory=list)
    active_tab: str | None = None


# --- Codec: self-contained, no hunt-data import. ---------------------------------
# Mirrors serialization/codec.py's compositional style, but for the UI channel: each
# level serializes its own slice. The dict shape is the one documented in this module's
# docstring.


def _position_to_dict(pos: Position) -> dict[str, Any]:
    return {"x": pos.x, "y": pos.y}


def _position_from_dict(data: dict[str, Any]) -> Position:
    return Position(x=data["x"], y=data["y"])


def _viewport_to_dict(vp: Viewport) -> dict[str, Any]:
    return {"x": vp.x, "y": vp.y, "zoom": vp.zoom}


def _viewport_from_dict(data: dict[str, Any]) -> Viewport:
    return Viewport(x=data["x"], y=data["y"], zoom=data["zoom"])


def _view_to_dict(view: View) -> dict[str, Any]:
    return {
        KEY_VIEW_GRAPH: view.graph,
        KEY_VIEW_TITLE: view.title,
        KEY_VIEW_POSITIONS: {nid: _position_to_dict(p) for nid, p in view.positions.items()},
        KEY_VIEW_SHOW_UNPLACED: view.show_unplaced,
    }


def _view_from_dict(data: dict[str, Any]) -> View:
    return View(
        graph=data[KEY_VIEW_GRAPH],
        title=data[KEY_VIEW_TITLE],
        positions={
            nid: _position_from_dict(p) for nid, p in data.get(KEY_VIEW_POSITIONS, {}).items()
        },
        # Additive + defaulted: a view from a file written before this flag existed loads as
        # "show them" rather than failing — same forgiving read as the tab viewport above.
        show_unplaced=data.get(KEY_VIEW_SHOW_UNPLACED, True),
    )


def _tab_to_dict(tab: Tab) -> dict[str, Any]:
    return {
        KEY_TAB_ID: tab.id,
        KEY_TAB_VIEW: tab.view,
        KEY_VIEWPORT: _viewport_to_dict(tab.viewport),
    }


def _tab_from_dict(data: dict[str, Any]) -> Tab:
    raw_viewport = data.get(KEY_VIEWPORT)
    return Tab(
        id=data[KEY_TAB_ID],
        view=data[KEY_TAB_VIEW],
        viewport=_viewport_from_dict(raw_viewport) if raw_viewport else IDENTITY_VIEWPORT,
    )


def workspace_to_dict(workspace: Workspace) -> dict[str, Any]:
    """Serialize a workspace to a JSON-safe dict (the body of the ``workspace`` entry)."""
    return {
        KEY_VIEWS: {vid: _view_to_dict(v) for vid, v in workspace.views.items()},
        KEY_TABS: [_tab_to_dict(t) for t in workspace.tabs],
        KEY_ACTIVE_TAB: workspace.active_tab,
    }


def workspace_from_dict(data: dict[str, Any]) -> Workspace:
    """Deserialize a workspace produced by :func:`workspace_to_dict`."""
    return Workspace(
        views={vid: _view_from_dict(v) for vid, v in data.get(KEY_VIEWS, {}).items()},
        tabs=[_tab_from_dict(t) for t in data.get(KEY_TABS, [])],
        active_tab=data.get(KEY_ACTIVE_TAB),
    )


def workspace_to_json(workspace: Workspace, *, indent: int | None = 2) -> str:
    """Serialize a workspace to a standalone JSON string (the 'could be two files' case)."""
    return json.dumps(workspace_to_dict(workspace), indent=indent, ensure_ascii=False)


def workspace_from_json(text: str) -> Workspace:
    """Deserialize a standalone workspace JSON string."""
    return workspace_from_dict(json.loads(text))
