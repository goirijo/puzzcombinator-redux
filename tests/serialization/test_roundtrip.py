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
    # Notes and puzzle payload survive.
    assert restored.nodes["c1"].notes == "hide under the doormat"
    assert restored.nodes["c1"].payload is not None


def test_json_roundtrip_preserves_puzzle_data(cipher_hunt: Graph) -> None:
    from puzzcombinator import CaesarCipherPuzzle

    restored = from_json(to_json(cipher_hunt))
    puzzle = restored.nodes["c1"].payload
    assert isinstance(puzzle, CaesarCipherPuzzle)
    assert puzzle.solution == "FOUNTAIN"


def test_roundtrip_with_contentless_edges() -> None:
    from puzzcombinator import GraphBuilder, NodeKind

    graph = (
        GraphBuilder()
        .node("s", kind=NodeKind.START)
        .node("e", kind=NodeKind.END)
        .connect("s", "e")  # no content
        .build()
    )
    assert from_dict(to_dict(graph)) == graph


def test_yaml_roundtrip(cipher_hunt: Graph) -> None:
    pytest.importorskip("yaml")
    from puzzcombinator.serialization import from_yaml, to_yaml

    assert from_yaml(to_yaml(cipher_hunt)) == cipher_hunt
