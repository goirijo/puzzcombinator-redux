from __future__ import annotations

from puzzcombinator.artifacts import TextArtifact
from puzzcombinator.artifacts.registry import build_artifact


def test_defaults_to_a_paragraph() -> None:
    art = TextArtifact("Search the LIBRARY")
    assert art.name == "text"
    markup = art.render().markup
    assert "Search the LIBRARY" in markup
    assert "<pre>" not in markup  # paragraph, not monospace


def test_monospace_renders_a_pre_block() -> None:
    assert "<pre>" in TextArtifact("12,34", monospace=True).render().markup


def test_payload_roundtrip_via_registry() -> None:
    art = TextArtifact("ROAD", title="Word", monospace=True, id="t1")
    rebuilt = build_artifact("text", name=art.name, id=art.id, payload=art.to_payload())
    assert rebuilt == art
    assert isinstance(rebuilt, TextArtifact)
