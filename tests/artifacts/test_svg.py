from __future__ import annotations

import pytest

from puzzcombinator.artifacts import (
    SvgArtifact,
    artifact_from_dict,
    artifact_to_dict,
)
from puzzcombinator.errors import PuzzleError

CIRCLE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    '<circle cx="5" cy="5" r="4"/></svg>'
)


def test_render_is_svg_kind_and_verbatim() -> None:
    frag = SvgArtifact(CIRCLE, id="s1").render()
    assert frag.kind == "svg"
    assert frag.markup == CIRCLE


def test_non_svg_markup_rejected() -> None:
    with pytest.raises(PuzzleError):
        SvgArtifact("<div>not svg</div>")


def test_from_file_reads_markup_verbatim(tmp_path) -> None:
    p = tmp_path / "shape.svg"
    p.write_text(CIRCLE, encoding="utf-8")
    art = SvgArtifact.from_file(p, id="s1")
    assert art.markup == CIRCLE
    assert art.render().kind == "svg"


def test_payload_roundtrip() -> None:
    art = SvgArtifact(CIRCLE, name="diagram", id="s1")
    rebuilt = SvgArtifact.from_payload(name=art.name, id=art.id, payload=art.to_payload())
    assert rebuilt == art


def test_registry_roundtrip() -> None:
    art = SvgArtifact(CIRCLE, name="diagram", id="s1")
    assert artifact_from_dict(artifact_to_dict(art)) == art


def test_eq_and_hash() -> None:
    a = SvgArtifact(CIRCLE, id="s1")
    b = SvgArtifact(CIRCLE, id="s1")
    assert a == b
    assert a != "not an artifact"
    assert len({a, b}) == 1
