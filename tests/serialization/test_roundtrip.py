from __future__ import annotations

import pytest

from puzzcombinator import Graph
from puzzcombinator.serialization import from_dict, from_json, to_dict, to_json


def test_dict_roundtrip_cipher(cipher_hunt: Graph) -> None:
    assert from_dict(to_dict(cipher_hunt)) == cipher_hunt


def test_dict_roundtrip_converging(converging_hunt: Graph) -> None:
    assert from_dict(to_dict(converging_hunt)) == converging_hunt


def test_json_roundtrip_cipher(cipher_hunt: Graph) -> None:
    restored = from_json(to_json(cipher_hunt))
    assert restored == cipher_hunt
    # Node notes and the edge-carried artifacts (ciphertext + answer) survive.
    assert restored.nodes["solve"].notes == "hide under the doormat"
    content = restored.edges["start->solve"].content
    assert [a.name for a in content] == ["cipher", "shift", "solution"]


def test_json_roundtrip_preserves_artifact_data(cipher_hunt: Graph) -> None:
    from puzzcombinator import CipherArtifact

    restored = from_json(to_json(cipher_hunt))
    content = restored.edges["start->solve"].content
    solution = next(a for a in content if a.name == "solution")
    assert isinstance(solution, CipherArtifact)
    assert solution.solution == "FOUNTAIN"


def test_json_roundtrip_multi_artifact_edge_preserves_order() -> None:
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
    restored = from_json(to_json(graph))
    assert restored == graph
    assert [a.text for a in restored.edges["a->b"].content] == ["first", "second", "answer"]


def test_roundtrip_with_contentless_edges() -> None:
    from puzzcombinator import GraphBuilder

    builder = GraphBuilder()
    s = builder.node("s")
    e = builder.node("e")
    graph = builder.connect(s, e).build()
    assert from_dict(to_dict(graph)) == graph


def test_yaml_roundtrip(cipher_hunt: Graph) -> None:
    pytest.importorskip("yaml")
    from puzzcombinator.serialization import from_yaml, to_yaml

    assert from_yaml(to_yaml(cipher_hunt)) == cipher_hunt
