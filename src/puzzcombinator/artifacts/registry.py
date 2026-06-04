"""Registry mapping artifact ``type_name`` to its class, for deserialization."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from puzzcombinator.errors import RegistryError

if TYPE_CHECKING:
    from puzzcombinator.rendering.fragment import Artifact

_ARTIFACT_TYPES: dict[str, type[Artifact]] = {}


def register_artifact[A: type[Artifact]](cls: A) -> A:
    """Class decorator: register an artifact subclass under its ``type_name``."""
    _ARTIFACT_TYPES[cls.type_name] = cls
    return cls


def build_artifact(type_name: str, *, name: str, id: str, payload: dict[str, Any]) -> Artifact:
    """Reconstruct an artifact from its serialized envelope and payload."""
    try:
        cls = _ARTIFACT_TYPES[type_name]
    except KeyError:
        raise RegistryError(
            f"unknown artifact type {type_name!r}; known: {sorted(_ARTIFACT_TYPES)}"
        ) from None
    return cls.from_payload(name=name, id=id, payload=payload)


def artifact_to_dict(artifact: Artifact) -> dict[str, Any]:
    """Serialize an artifact to its self-describing envelope ``{type,id,name,payload}``.

    This is the single artifact-level serialization shape. A composite uses it to
    round-trip its children; the graph codec composes it for whole edges.
    """
    return {
        "type": artifact.type_name,
        "id": artifact.id,
        "name": artifact.name,
        "payload": artifact.to_payload(),
    }


def artifact_from_dict(data: dict[str, Any]) -> Artifact:
    """Rebuild an artifact from the envelope produced by :func:`artifact_to_dict`."""
    return build_artifact(data["type"], name=data["name"], id=data["id"], payload=data["payload"])
