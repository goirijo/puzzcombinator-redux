from __future__ import annotations

import pytest

from puzzcombinator import Graph, HuntDocument
from puzzcombinator.errors import RegistryError, SerializationError
from puzzcombinator.serialization import (
    document_to_dict,
    graph_from_dict,
    graph_to_dict,
)


def test_graph_envelope_has_version_and_body(cipher_hunt: Graph) -> None:
    data = graph_to_dict(cipher_hunt)
    assert data["schema_version"] == "3"
    assert set(data["graph"]) == {"nodes", "edges"}
    node = next(n for n in data["graph"]["nodes"] if n["id"] == "solve")
    assert node["action"] == "solve"
    assert node["notes"] == "hide under the doormat"
    # An edge's content is a list of artifact envelopes — audience-free.
    edge = next(e for e in data["graph"]["edges"] if e["id"] == "start->solve")
    assert edge["content"][0]["type"] == "caesar_cipher"
    assert {a["name"] for a in edge["content"]} == {"cipher", "shift", "solution"}
    assert all("audience" not in a for a in edge["content"])


def test_document_envelope_is_a_graphs_map(cipher_hunt: Graph) -> None:
    data = document_to_dict(HuntDocument.single(cipher_hunt))
    assert data["schema_version"] == "3"
    assert set(data["graphs"]) == {"main"}
    assert set(data["graphs"]["main"]) == {"nodes", "edges"}


def test_unsupported_version_raises(cipher_hunt: Graph) -> None:
    data = graph_to_dict(cipher_hunt)
    data["schema_version"] = "999"
    with pytest.raises(SerializationError, match="schema_version"):
        graph_from_dict(data)


def test_known_old_version_reports_unmigrated(cipher_hunt: Graph) -> None:
    # A known pre-v3 version routes to the migration scaffold (unwritten by design).
    data = graph_to_dict(cipher_hunt)
    data["schema_version"] = "2"
    with pytest.raises(SerializationError, match="migration is not"):
        graph_from_dict(data)


def test_unknown_artifact_type_raises(cipher_hunt: Graph) -> None:
    data = graph_to_dict(cipher_hunt)
    edge = next(e for e in data["graph"]["edges"] if e["id"] == "start->solve")
    edge["content"][0]["type"] = "mystery_box"
    with pytest.raises(RegistryError, match="mystery_box"):
        graph_from_dict(data)
