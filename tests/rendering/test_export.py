from __future__ import annotations

from puzzcombinator.artifacts import SvgArtifact, TextArtifact
from puzzcombinator.rendering.export import html_document, write_html

CIRCLE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    '<circle cx="5" cy="5" r="4"/></svg>'
)


def test_html_document_is_pure_and_complete() -> None:
    doc = html_document("My Title", "<p>hi</p>", styles=".x { color: red; }")
    assert doc.startswith("<!DOCTYPE html>")
    assert "<title>My Title</title>" in doc
    assert "<p>hi</p>" in doc
    assert ".x { color: red; }" in doc


def test_html_document_escapes_title() -> None:
    assert "<title>a &amp; b</title>" in html_document("a & b", "")


def test_write_html_returns_path_and_embeds_markup_and_styles(tmp_path) -> None:
    art = TextArtifact("ROAD", title="Word", id="t1")
    path = write_html(art, tmp_path)
    assert path == tmp_path / "t1.html"
    frag = art.render()
    content = path.read_text(encoding="utf-8")
    assert frag.markup in content
    assert frag.styles in content


def test_write_html_embeds_inline_svg_in_body(tmp_path) -> None:
    path = write_html(SvgArtifact(CIRCLE, id="s1"), tmp_path)
    content = path.read_text(encoding="utf-8")
    assert "<body>" in content
    assert CIRCLE in content  # inline <svg>, not an <img>
    assert "<img" not in content
