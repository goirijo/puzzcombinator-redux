from __future__ import annotations

import pytest

from puzzcombinator import Graph
from puzzcombinator.errors import RegistryError, SerializationError
from puzzcombinator.serialization import from_dict, to_dict


def test_envelope_has_version_and_keys(cipher_hunt: Graph) -> None:
    data = to_dict(cipher_hunt)
    assert data["schema_version"] == "1"
    assert set(data["graph"]) == {"nodes", "edges"}
    node = next(n for n in data["graph"]["nodes"] if n["id"] == "c1")
    assert node["puzzle"]["type"] == "caesar_cipher"
    assert node["notes"] == "hide under the doormat"


def test_unsupported_version_raises(cipher_hunt: Graph) -> None:
    data = to_dict(cipher_hunt)
    data["schema_version"] = "999"
    with pytest.raises(SerializationError, match="schema_version"):
        from_dict(data)


def test_unknown_puzzle_type_raises(cipher_hunt: Graph) -> None:
    data = to_dict(cipher_hunt)
    node = next(n for n in data["graph"]["nodes"] if n["id"] == "c1")
    node["puzzle"]["type"] = "mystery_box"
    with pytest.raises(RegistryError, match="mystery_box"):
        from_dict(data)
