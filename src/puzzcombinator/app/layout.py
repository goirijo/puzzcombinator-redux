"""Compute 2-D positions for a hunt graph's nodes — a pure design-time query.

Given a :class:`~puzzcombinator.core.graph.Graph`, decide where to draw each node so
the picture reads left-to-right in solve order. This is the heart of the read-only
visualization milestone, and it is intentionally a *pure function*: a graph goes in,
a ``{node_id: NodePosition}`` map comes out, with no I/O, no browser, and no global
state. That makes it trivially unit-testable, and the same data structure serializes
straight to JSON for the frontend.

The layout is a standard **layered DAG** ("Sugiyama-lite"):

* **Layer (the column / x-axis)** — a node's layer is the length of the longest path
  of edges reaching it from any start node. Start nodes (no incoming edges) sit at
  layer 0. Because we walk the nodes in :func:`topological_order`, every
  predecessor's layer is already known when we reach a node, so an edge always points
  to a strictly higher layer — i.e. rightward — which is what makes the graph legible.
* **Row (within a column / y-axis)** — nodes sharing a layer are stacked top-to-bottom
  in topological order (which is deterministic, ties broken by id), one per row slot.

Pixel geometry lives here (not in the browser) so positions are fully determined
server-side and the tests can assert exact coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass

from puzzcombinator.core.graph import Graph
from puzzcombinator.core.ordering import topological_order

# Pixel geometry for the drawn graph. Tweak freely — the tests read these constants
# rather than hard-coding numbers, so changing them here keeps the suite green.
COLUMN_WIDTH = 220.0  # horizontal gap between consecutive layers
ROW_HEIGHT = 120.0  # vertical gap between nodes within a layer
MARGIN_X = 60.0  # left padding before layer 0
MARGIN_Y = 60.0  # top padding above row 0


@dataclass(frozen=True)
class NodePosition:
    """Where one node is drawn.

    ``layer``/``row`` are the abstract grid coordinates (column index, and the node's
    slot within that column); ``x``/``y`` are the pixel coordinates the browser draws
    at. Both are returned so the frontend can use the pixels directly or re-space the
    grid itself later.
    """

    layer: int
    row: int
    x: float
    y: float


def layered_layout(graph: Graph) -> dict[str, NodePosition]:
    """Assign each node a layer, a row, and pixel coordinates.

    Pure: depends only on the graph's structure. Raises
    :class:`~puzzcombinator.errors.GraphError` on a cycle (via
    :func:`topological_order`). The empty graph yields an empty map.
    """
    order = topological_order(graph)  # topological ids; predecessors come first

    # 1. Layer = longest path (in edges) from any start node. Safe to read each
    #    predecessor's layer because topological order visits it first.
    layer: dict[str, int] = {}
    for node_id in order:
        incoming = graph.incoming(node_id)
        layer[node_id] = max((layer[e.source] for e in incoming), default=-1) + 1

    # 2. Row = the node's position among others sharing its layer, in topo order.
    next_row: dict[int, int] = {}
    positions: dict[str, NodePosition] = {}
    for node_id in order:
        lyr = layer[node_id]
        row = next_row.get(lyr, 0)
        next_row[lyr] = row + 1
        positions[node_id] = NodePosition(
            layer=lyr,
            row=row,
            x=MARGIN_X + lyr * COLUMN_WIDTH,
            y=MARGIN_Y + row * ROW_HEIGHT,
        )
    return positions
