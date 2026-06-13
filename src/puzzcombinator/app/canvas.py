"""The canvas/visualization channel — *where* a hunt is drawn, kept separate from
*what* the hunt is.

This is the second of the two persisted channels (the first being hunt data, in
``serialization``/``core.document``). It carries purely visual state — node
positions, which view, collapsed/expanded nodes — and **never** any treasure-hunt
data. Keeping it out of :class:`~puzzcombinator.core.document.HuntDocument` is
deliberate: visualization state must not be able to affect hunt-data round-trip
equality, and a hunt is fully valid with no canvas state at all (the editor falls
back to the auto-arranged :func:`~puzzcombinator.app.layout.layered_layout`).

A hunt may have **several views of the same graph** — different manual positioning,
different collapsed nodes, a filtered subgraph. So a view references a graph by id
and carries its own positions; many views can point at one graph.

**Status:** shape only. Nothing moves nodes yet (manual positioning + drag arrive
with the canvas-interaction milestone), so these structures are *defined* but not yet
persisted or wired into an endpoint. When persistence lands, a view's ``positions``
override the auto-layout per node; a node with no stored position falls back to
:func:`layered_layout`. The on-disk shape is documented in
``serialization/schema.py``; this module is its in-memory mirror.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Position:
    """A node's manually-set pixel position on the canvas."""

    x: float
    y: float


@dataclass
class View:
    """One visual representation of a graph.

    ``graph`` is the id of the graph this view draws. ``positions`` maps node id →
    :class:`Position` for nodes the designer has placed by hand (others auto-layout).
    ``collapsed`` lists node ids drawn collapsed. ``subgraph`` (future) will filter
    the view to a subset of the graph; ``None`` means the whole graph.
    """

    graph: str
    positions: dict[str, Position] = field(default_factory=dict)
    collapsed: list[str] = field(default_factory=list)
    subgraph: None = None


@dataclass
class CanvasDocument:
    """The canvas sidecar: named views of a hunt's graphs."""

    views: dict[str, View] = field(default_factory=dict)
