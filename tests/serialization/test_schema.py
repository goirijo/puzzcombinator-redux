from __future__ import annotations

import pytest

from puzzcombinator import Graph
from puzzcombinator.errors import RegistryError, SerializationError
from puzzcombinator.serialization import from_dict, to_dict


def test_envelope_has_version_and_keys(cipher_hunt: Graph) -> None:
    data = to_dict(cipher_hunt)
    assert data["schema_version"] == "2"
    assert set(data["graph"]) == {"nodes", "edges"}
    node = next(n for n in data["graph"]["nodes"] if n["id"] == "solve")
    assert node["action"] == "solve"
    assert node["notes"] == "hide under the doormat"
    # An edge's content is a list of artifact envelopes — audience-free.
    edge = next(e for e in data["graph"]["edges"] if e["id"] == "start->solve")
    assert edge["content"][0]["type"] == "caesar_cipher"
    assert {a["name"] for a in edge["content"]} == {"cipher", "shift", "solution"}
    assert all("audience" not in a for a in edge["content"])


def test_unsupported_version_raises(cipher_hunt: Graph) -> None:
    data = to_dict(cipher_hunt)
    data["schema_version"] = "999"
    with pytest.raises(SerializationError, match="schema_version"):
        from_dict(data)


def test_unknown_artifact_type_raises(cipher_hunt: Graph) -> None:
    data = to_dict(cipher_hunt)
    edge = next(e for e in data["graph"]["edges"] if e["id"] == "start->solve")
    edge["content"][0]["type"] = "mystery_box"
    with pytest.raises(RegistryError, match="mystery_box"):
        from_dict(data)
