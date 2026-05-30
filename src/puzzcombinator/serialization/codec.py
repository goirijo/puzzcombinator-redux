"""Convert a :class:`~puzzcombinator.core.graph.Graph` to/from plain dicts.

This is the only place that knows the on-disk shape. It drives the validator-
and puzzle-type registries to rebuild polymorphic payloads, and it never embeds
nodes inside edges — node wiring is recomputed on load — so the dict is acyclic
and round-trips to a value-equal graph.
"""

from __future__ import annotations

from typing import Any

from puzzcombinator.core.graph import Content, Edge, Graph, Node, NodeKind
from puzzcombinator.errors import SerializationError
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.registry import build_puzzle
from puzzcombinator.serialization.schema import (
    KEY_EDGES,
    KEY_GRAPH,
    KEY_NODES,
    KEY_SCHEMA_VERSION,
    SCHEMA_VERSION,
)


def _content_to_dict(content: Content | None) -> dict[str, Any] | None:
    if content is None:
        return None
    return {"text": content.text, "data": content.data}


def _content_from_dict(data: dict[str, Any] | None) -> Content | None:
    if data is None:
        return None
    return Content(text=data.get("text"), data=data.get("data", {}))


def _puzzle_to_dict(puzzle: Puzzle) -> dict[str, Any]:
    return {"type": puzzle.type_name, "payload": puzzle.to_payload()}


def _puzzle_from_dict(node_id: str, data: dict[str, Any]) -> Puzzle:
    return build_puzzle(data["type"], node_id, data["payload"])


def _node_to_dict(node: Node) -> dict[str, Any]:
    return {
        "id": node.id,
        "kind": node.kind.value,
        "label": node.label,
        "notes": node.notes,
        "puzzle": _puzzle_to_dict(node.payload) if node.payload is not None else None,
    }


def _node_from_dict(data: dict[str, Any]) -> Node:
    puzzle_data = data.get("puzzle")
    payload = _puzzle_from_dict(data["id"], puzzle_data) if puzzle_data else None
    return Node(
        id=data["id"],
        payload=payload,
        kind=NodeKind(data["kind"]),
        label=data.get("label"),
        notes=data.get("notes"),
    )


def _edge_to_dict(edge: Edge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "source": edge.source,
        "target": edge.target,
        "content": _content_to_dict(edge.content),
    }


def _edge_from_dict(data: dict[str, Any]) -> Edge:
    return Edge(
        id=data["id"],
        source=data["source"],
        target=data["target"],
        content=_content_from_dict(data.get("content")),
    )


def to_dict(graph: Graph) -> dict[str, Any]:
    """Serialize a graph to a JSON-safe dict."""
    return {
        KEY_SCHEMA_VERSION: SCHEMA_VERSION,
        KEY_GRAPH: {
            KEY_NODES: [_node_to_dict(n) for n in graph.nodes.values()],
            KEY_EDGES: [_edge_to_dict(e) for e in graph.edges.values()],
        },
    }


def from_dict(data: dict[str, Any]) -> Graph:
    """Deserialize a graph produced by :func:`to_dict`."""
    version = data.get(KEY_SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        raise SerializationError(
            f"unsupported schema_version {version!r}; expected {SCHEMA_VERSION!r}"
        )
    graph_data = data[KEY_GRAPH]
    nodes = [_node_from_dict(n) for n in graph_data[KEY_NODES]]
    edges = [_edge_from_dict(e) for e in graph_data[KEY_EDGES]]
    return Graph.assemble(nodes, edges)
