from __future__ import annotations

import pytest

from puzzcombinator import Graph, HuntDocument
from puzzcombinator.serialization import (
    document_from_dict,
    document_to_dict,
    from_json,
    graph_from_dict,
    graph_to_dict,
    to_json,
)

# --- Graph level: a graph round-trips its own {nodes, edges} slice. ----------------


def test_graph_dict_roundtrip_cipher(cipher_hunt: Graph) -> None:
    assert graph_from_dict(graph_to_dict(cipher_hunt)) == cipher_hunt


def test_graph_dict_roundtrip_converging(converging_hunt: Graph) -> None:
    assert graph_from_dict(graph_to_dict(converging_hunt)) == converging_hunt


def test_graph_roundtrip_preserves_artifacts(cipher_hunt: Graph) -> None:
    from puzzcombinator import CipherArtifact

    restored = graph_from_dict(graph_to_dict(cipher_hunt))
    # Node notes and the edge-carried artifacts (ciphertext + answer) survive.
    assert restored.nodes["solve"].notes == "hide under the doormat"
    content = restored.edges["start->solve"].content
    assert [a.name for a in content] == ["cipher", "shift", "solution"]
    solution = next(a for a in content if a.name == "solution")
    assert isinstance(solution, CipherArtifact)
    assert solution.solution == "FOUNTAIN"


def test_graph_roundtrip_multi_artifact_edge_preserves_order() -> None:
    from puzzcombinator import GraphBuilder, TextArtifact

    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    graph = builder.connect(
        a,
        b,
        TextArtifact("first", id="t1"),
        TextArtifact("second", id="t2"),
        TextArtifact("answer", id="t3"),
    ).build()
    restored = graph_from_dict(graph_to_dict(graph))
    assert restored == graph
    assert [a.text for a in restored.edges["a->b"].content] == ["first", "second", "answer"]


def test_graph_roundtrip_with_contentless_edges() -> None:
    from puzzcombinator import GraphBuilder

    builder = GraphBuilder()
    s = builder.node("s")
    e = builder.node("e")
    graph = builder.connect(s, e).build()
    assert graph_from_dict(graph_to_dict(graph)) == graph


# --- Document level: a multi-graph hunt round-trips its graphs map. -----------------


def test_document_dict_roundtrip(cipher_hunt: Graph, converging_hunt: Graph) -> None:
    doc = HuntDocument(graphs={"main": cipher_hunt, "other": converging_hunt})
    assert document_from_dict(document_to_dict(doc)) == doc


def test_document_roundtrip_with_unplaced_pool(cipher_hunt: Graph) -> None:
    from puzzcombinator import TextArtifact

    doc = HuntDocument(
        graphs={"main": cipher_hunt},
        unplaced={
            "main": (
                TextArtifact("loose one", id="loose-1"),
                TextArtifact("loose two", id="loose-2"),
            )
        },
    )
    restored = document_from_dict(document_to_dict(doc))
    assert restored == doc
    assert [a.text for a in restored.unplaced["main"]] == ["loose one", "loose two"]


def test_document_without_unplaced_key_loads_empty_pool(cipher_hunt: Graph) -> None:
    # A document serialized before the pool existed has no "unplaced" key; it must
    # read back as an empty pool, not raise.
    data = document_to_dict(HuntDocument.single(cipher_hunt))
    del data["unplaced"]
    restored = document_from_dict(data)
    assert restored.unplaced == {}
    assert restored == HuntDocument.single(cipher_hunt)


def test_json_file_roundtrip_preserves_unplaced(cipher_hunt: Graph) -> None:
    from puzzcombinator import TextArtifact

    doc = HuntDocument(
        graphs={"main": cipher_hunt},
        unplaced={"main": (TextArtifact("scratch", id="loose-1"),)},
    )
    assert from_json(to_json(doc)) == doc


# --- File level: saving/loading a hunt file is document-level JSON/YAML. -------------


def test_json_file_roundtrip(cipher_hunt: Graph) -> None:
    doc = HuntDocument.single(cipher_hunt)
    assert from_json(to_json(doc)) == doc


def test_yaml_file_roundtrip(cipher_hunt: Graph) -> None:
    pytest.importorskip("yaml")
    from puzzcombinator.serialization import from_yaml, to_yaml

    doc = HuntDocument.single(cipher_hunt)
    assert from_yaml(to_yaml(doc)) == doc
