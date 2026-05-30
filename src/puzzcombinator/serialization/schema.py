"""Schema version and dict-shape key constants for serialized hunts."""

from __future__ import annotations

#: Bumped when the serialized shape changes incompatibly. Loaders branch on it.
SCHEMA_VERSION = "1"

KEY_SCHEMA_VERSION = "schema_version"
KEY_GRAPH = "graph"
KEY_NODES = "nodes"
KEY_EDGES = "edges"
