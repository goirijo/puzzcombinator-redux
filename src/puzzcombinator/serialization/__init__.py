"""Round-trip a hunt to/from JSON (stdlib) or YAML (optional ``[yaml]`` extra)."""

from __future__ import annotations

import json
from typing import Any

from puzzcombinator.core.graph import Graph
from puzzcombinator.serialization.codec import from_dict, to_dict
from puzzcombinator.serialization.schema import SCHEMA_VERSION

__all__ = [
    "SCHEMA_VERSION",
    "from_dict",
    "from_json",
    "from_yaml",
    "to_dict",
    "to_json",
    "to_yaml",
]

_YAML_HINT = "YAML support requires the 'yaml' extra: pip install puzzcombinator[yaml]"


def to_json(graph: Graph, *, indent: int | None = 2) -> str:
    """Serialize a graph to a JSON string."""
    return json.dumps(to_dict(graph), indent=indent, ensure_ascii=False)


def from_json(text: str) -> Graph:
    """Deserialize a graph from a JSON string."""
    data: Any = json.loads(text)
    return from_dict(data)


def to_yaml(graph: Graph) -> str:
    """Serialize a graph to a YAML string (requires the ``yaml`` extra)."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(_YAML_HINT) from exc
    return yaml.safe_dump(to_dict(graph), sort_keys=False)


def from_yaml(text: str) -> Graph:
    """Deserialize a graph from a YAML string (requires the ``yaml`` extra)."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(_YAML_HINT) from exc
    return from_dict(yaml.safe_load(text))
