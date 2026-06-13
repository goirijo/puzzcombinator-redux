"""Convert graphs and hunt documents to/from plain dicts.

This is the only place that knows the on-disk shape. The codec is **compositional**:
each level serializes its own slice and delegates the rest. An :class:`Edge`'s
artifacts round-trip through the registry; a :class:`Graph` owns its ``{nodes, edges}``
block; a :class:`HuntDocument` owns its ``graphs`` map and reuses the graph block. It
never embeds nodes inside edges (wiring is recomputed on load), so the dict is acyclic
and round-trips to a value-equal object.

There is no type-switching entry point: a graph and a document each get their own pair
of functions (``graph_to_dict``/``graph_from_dict`` and
``document_to_dict``/``document_from_dict``), and each ``*_from_dict`` returns one
concrete type. Callers serialize the thing they actually hold — a puzzle test rebuilds
a :class:`Graph`; the editor's file layer rebuilds a :class:`HuntDocument`.

Both envelopes share one ``schema_version`` (see ``schema.py``); version handling and
the migration scaffold live in :func:`_assert_current_version`.
"""

from __future__ import annotations

from typing import Any

from puzzcombinator.artifacts.registry import artifact_from_dict, artifact_to_dict
from puzzcombinator.core.document import HuntDocument
from puzzcombinator.core.graph import Edge, Graph, Node
from puzzcombinator.errors import SerializationError
from puzzcombinator.serialization.schema import (
    KEY_EDGES,
    KEY_GRAPH,
    KEY_GRAPHS,
    KEY_NODES,
    KEY_SCHEMA_VERSION,
    SCHEMA_VERSION,
)

#: Versions we recognize but no longer read. They route to a clear "migration not
#: implemented" error rather than being silently mis-parsed — the scaffold where real
#: old→new upgrades would go once there is saved data worth migrating.
_KNOWN_OLD_VERSIONS = ("1", "2")


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
        "content": [artifact_to_dict(a) for a in edge.content],
    }


def _edge_from_dict(data: dict[str, Any]) -> Edge:
    return Edge(
        id=data["id"],
        source=data["source"],
        target=data["target"],
        content=tuple(artifact_from_dict(d) for d in data.get("content", [])),
    )


def _block_to_dict(graph: Graph) -> dict[str, Any]:
    """A graph's bare ``{nodes, edges}`` slice (no version envelope)."""
    return {
        KEY_NODES: [_node_to_dict(n) for n in graph.nodes.values()],
        KEY_EDGES: [_edge_to_dict(e) for e in graph.edges.values()],
    }


def _block_from_dict(block: dict[str, Any]) -> Graph:
    nodes = [_node_from_dict(n) for n in block[KEY_NODES]]
    edges = [_edge_from_dict(e) for e in block[KEY_EDGES]]
    return Graph.assemble(nodes, edges)


def _assert_current_version(data: dict[str, Any]) -> None:
    """Raise unless ``data`` carries the current ``schema_version``.

    Known-but-older versions get a distinct "migration not implemented" message;
    anything else is simply unsupported.
    """
    version = data.get(KEY_SCHEMA_VERSION)
    if version == SCHEMA_VERSION:
        return
    if version in _KNOWN_OLD_VERSIONS:
        raise SerializationError(
            f"schema_version {version!r} predates {SCHEMA_VERSION!r}; migration is not "
            "implemented (no saved data to migrate yet)"
        )
    raise SerializationError(f"unsupported schema_version {version!r}; expected {SCHEMA_VERSION!r}")


def graph_to_dict(graph: Graph) -> dict[str, Any]:
    """Serialize a single graph to its own JSON-safe envelope."""
    return {KEY_SCHEMA_VERSION: SCHEMA_VERSION, KEY_GRAPH: _block_to_dict(graph)}


def graph_from_dict(data: dict[str, Any]) -> Graph:
    """Deserialize a graph produced by :func:`graph_to_dict`."""
    _assert_current_version(data)
    return _block_from_dict(data[KEY_GRAPH])


def document_to_dict(doc: HuntDocument) -> dict[str, Any]:
    """Serialize a whole hunt document (its ``graphs`` map) to a JSON-safe envelope."""
    return {
        KEY_SCHEMA_VERSION: SCHEMA_VERSION,
        KEY_GRAPHS: {gid: _block_to_dict(g) for gid, g in doc.graphs.items()},
    }


def document_from_dict(data: dict[str, Any]) -> HuntDocument:
    """Deserialize a hunt document produced by :func:`document_to_dict`."""
    _assert_current_version(data)
    return HuntDocument(graphs={gid: _block_from_dict(g) for gid, g in data[KEY_GRAPHS].items()})
