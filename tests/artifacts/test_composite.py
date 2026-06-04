from __future__ import annotations

from puzzcombinator.artifacts import (
    CompositeArtifact,
    ImageArtifact,
    TextArtifact,
    artifact_from_dict,
    artifact_to_dict,
)

_URI = "data:image/png;base64,AAAA"


def _composite(id: str = "c1") -> CompositeArtifact:
    return CompositeArtifact(
        [
            TextArtifact("solve me", title="Clue", id="t1"),
            ImageArtifact(_URI, alt="a map", id="i1"),
        ],
        id=id,
    )


def test_renders_every_child() -> None:
    markup = _composite().render().markup
    assert "solve me" in markup
    assert "data:image/png" in markup
    assert 'class="pc-composite"' in markup


def test_styles_are_unioned_without_duplication() -> None:
    # Two text children share TextArtifact's CSS; it should appear only once.
    comp = CompositeArtifact([TextArtifact("a", id="a"), TextArtifact("b", id="b")])
    styles = comp.render().styles
    assert styles.count(".pc-card pre") == 1
    assert ".pc-composite" in styles


def test_payload_roundtrips_via_envelope() -> None:
    comp = _composite()
    rebuilt = artifact_from_dict(artifact_to_dict(comp))
    assert rebuilt == comp
    assert isinstance(rebuilt, CompositeArtifact)
    assert [c.id for c in rebuilt.children] == ["t1", "i1"]


def test_nested_composites_roundtrip() -> None:
    inner = _composite("inner")
    outer = CompositeArtifact([inner, TextArtifact("outer note", id="note")], id="outer")
    rebuilt = artifact_from_dict(artifact_to_dict(outer))
    assert rebuilt == outer
    assert "solve me" in rebuilt.render().markup


def test_value_equality() -> None:
    assert _composite() == _composite()
    assert _composite("a") != _composite("b")
