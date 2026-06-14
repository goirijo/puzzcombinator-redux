"""Serialize hunts to/from plain data and files.

Two levels, both compositional (see ``codec.py``):

* **Component dicts** — ``graph_to_dict`` / ``graph_from_dict`` round-trip a single
  :class:`~puzzcombinator.core.graph.Graph`; ``document_to_dict`` /
  ``document_from_dict`` round-trip a whole
  :class:`~puzzcombinator.core.document.HuntDocument`. Each function owns one level, so
  a caller (a puzzle, a builder) serializes only the part it holds.
* **Files** — ``to_json`` / ``from_json`` (stdlib) and ``to_yaml`` / ``from_yaml``
  (optional ``[yaml]`` extra) persist a *hunt document* (a saved hunt file is a whole
  document). Keystone invariant: ``from_json(to_json(doc)) == doc``.
"""

from __future__ import annotations

import json
from typing import Any

from puzzcombinator.core.document import HuntDocument
from puzzcombinator.serialization.codec import (
    document_from_dict,
    document_to_dict,
    graph_from_dict,
    graph_to_dict,
)
from puzzcombinator.serialization.schema import SCHEMA_VERSION

__all__ = [
    "SCHEMA_VERSION",
    "document_from_dict",
    "document_to_dict",
    "from_json",
    "from_yaml",
    "graph_from_dict",
    "graph_to_dict",
    "to_json",
    "to_yaml",
]

_YAML_HINT = "YAML support requires the 'yaml' extra: pip install puzzcombinator[yaml]"


def to_json(doc: HuntDocument, *, indent: int | None = 2) -> str:
    """Serialize a hunt document to a JSON string (a saved hunt file)."""
    return json.dumps(document_to_dict(doc), indent=indent, ensure_ascii=False)


def from_json(text: str) -> HuntDocument:
    """Deserialize a hunt document from a JSON string."""
    data: Any = json.loads(text)
    return document_from_dict(data)


def to_yaml(doc: HuntDocument) -> str:
    """Serialize a hunt document to a YAML string (requires the ``yaml`` extra)."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(_YAML_HINT) from exc
    return yaml.safe_dump(document_to_dict(doc), sort_keys=False)


def from_yaml(text: str) -> HuntDocument:
    """Deserialize a hunt document from a YAML string (requires the ``yaml`` extra)."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(_YAML_HINT) from exc
    return document_from_dict(yaml.safe_load(text))
