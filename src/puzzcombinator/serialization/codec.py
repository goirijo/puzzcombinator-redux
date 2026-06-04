"""Convert a :class:`~puzzcombinator.core.graph.Graph` to/from plain dicts.

This is the only place that knows the on-disk shape. It drives the artifact-type
registry to rebuild polymorphic payloads, and it never embeds nodes inside edges —
node wiring is recomputed on load — so the dict is acyclic and round-trips to a
value-equal graph.
"""

from __future__ import annotations

from typing import Any

from puzzcombinator.artifacts.registry import build_artifact
from puzzcombinator.core.graph import Edge, Graph, Node
from puzzcombinator.errors import SerializationError
from puzzcombinator.rendering.fragment import Artifact, Audience
from puzzcombinator.serialization.schema import (
    KEY_EDGES,
    KEY_GRAPH,
    KEY_NODES,
    KEY_SCHEMA_VERSION,
    SCHEMA_VERSION,
)


def _artifact_to_dict(artifact: Artifact) -> dict[str, Any]:
    return {
        "type": artifact.type_name,
        "id": artifact.id,
        "name": artifact.name,
        "audience": artifact.audience.value,
        "payload": artifact.to_payload(),
    }


def _artifact_from_dict(data: dict[str, Any]) -> Artifact:
    return build_artifact(
        data["type"],
        name=data["name"],
        audience=Audience(data["audience"]),
        id=data["id"],
        payload=data["payload"],
    )


def _node_to_dict(node: Node) -> dict[str, Any]:
    return {
        "id": node.id,
        "action": node.action,
        "label": node.label,
        "notes": node.notes,
    }


def _node_from_dict(data: dict[str, Any]) -> Node:
    return Node(
        id=data["id"],
        action=data.get("action"),
        label=data.get("label"),
        notes=data.get("notes"),
    )


def _edge_to_dict(edge: Edge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "source": edge.source,
        "target": edge.target,
        "content": [_artifact_to_dict(a) for a in edge.content],
    }


def _edge_from_dict(data: dict[str, Any]) -> Edge:
    return Edge(
        id=data["id"],
        source=data["source"],
        target=data["target"],
        content=tuple(_artifact_from_dict(d) for d in data.get("content", [])),
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
