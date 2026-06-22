"""The visualization layer: *how* a hunt is drawn, kept separate from *what* it is.

This package is the Python representation of the editor's visual/UI state — it is the
deliberate counterweight to the data layers (``core``/``artifacts``/``puzzles``/
``serialization``/``rendering``), which know nothing about drawing. The split is a
file-tree-visible separation of concerns: data lives there, *representation* lives here.

Two pieces:

* :mod:`~puzzcombinator.visualization.layout` — :func:`layered_layout`, a pure
  graph→positions query (the auto-arranged fallback when nothing is placed by hand).
* :mod:`~puzzcombinator.visualization.workspace` — the **workspace** channel: the
  views, tabs, and positions the editor persists. Self-contained — it references nodes
  by opaque id and never imports the hunt-data model, so a workspace serializes and
  unit-tests entirely on its own.

Dependency direction stays strictly downward: ``app`` composes this with
``serialization`` into one file; this layer may read ``core`` (layout needs a graph),
but ``core`` never learns this layer exists.
"""

from __future__ import annotations

from puzzcombinator.visualization.layout import (
    COLUMN_WIDTH,
    MARGIN_X,
    MARGIN_Y,
    ROW_HEIGHT,
    NodePosition,
    layered_layout,
)
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

__all__ = [
    "COLUMN_WIDTH",
    "MARGIN_X",
    "MARGIN_Y",
    "NodePosition",
    "Position",
    "ROW_HEIGHT",
    "Tab",
    "View",
    "Viewport",
    "Workspace",
    "layered_layout",
    "workspace_from_dict",
    "workspace_from_json",
    "workspace_to_dict",
    "workspace_to_json",
]
