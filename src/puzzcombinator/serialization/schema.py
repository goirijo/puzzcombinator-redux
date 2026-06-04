"""Schema version and dict-shape key constants for serialized hunts."""

from __future__ import annotations

#: Bumped when the serialized shape changes incompatibly. Loaders branch on it.
#: v2: edges carry a list of artifacts ``{type,id,name,audience,payload}`` instead
#: of a single ``Content`` with text/data/puzzle.
SCHEMA_VERSION = "2"

KEY_SCHEMA_VERSION = "schema_version"
KEY_GRAPH = "graph"
KEY_NODES = "nodes"
KEY_EDGES = "edges"
