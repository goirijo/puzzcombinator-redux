from __future__ import annotations

import struct
import zlib

from puzzcombinator.artifacts import (
    CompositeArtifact,
    ImageArtifact,
    SvgArtifact,
    TextArtifact,
)
from puzzcombinator.rendering.export import (
    html_document,
    write_artifact,
    write_artifacts,
    write_html,
)

CIRCLE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    '<circle cx="5" cy="5" r="4"/></svg>'
)


def _png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """A real, valid solid-colour PNG built with the stdlib (mirrors test_image.py)."""

    def chunk(typ: bytes, data: bytes) -> bytes:
        body = typ + data
        crc = struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + body + crc

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


# --- html_document / write_html: the presentation view ---


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


# --- write_artifact: native form to {id}.{ext}, HTML fallback when there is none ---


def test_write_artifact_writes_text_natively(tmp_path) -> None:
    path = write_artifact(TextArtifact("ROAD", title="Word", id="t1"), tmp_path)
    assert path == tmp_path / "t1.txt"
    assert path.read_text(encoding="utf-8") == "ROAD"  # render hints dropped


def test_write_artifact_writes_svg_raw(tmp_path) -> None:
    path = write_artifact(SvgArtifact(CIRCLE, id="s1"), tmp_path)
    assert path == tmp_path / "s1.svg"
    assert path.read_text(encoding="utf-8") == CIRCLE


def test_write_artifact_writes_image_bytes(tmp_path) -> None:
    data = _png(3, 2, (0, 128, 0))
    art = ImageArtifact.from_bytes(data, mime="image/png", id="img1")
    path = write_artifact(art, tmp_path)
    assert path == tmp_path / "img1.png"
    assert path.read_bytes() == data


def test_write_artifact_falls_back_to_html_for_composite(tmp_path) -> None:
    path = write_artifact(CompositeArtifact([TextArtifact("hi")], id="c1"), tmp_path)
    assert path == tmp_path / "c1.html"
    assert path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_write_artifact_creates_missing_directory(tmp_path) -> None:
    out = tmp_path / "nested" / "out"  # does not exist yet
    path = write_artifact(TextArtifact("x", id="t9"), out)
    assert path == out / "t9.txt"
    assert path.read_text(encoding="utf-8") == "x"


# --- write_artifacts: write_artifact across a map, filenames from each artifact's id ---


def test_write_artifacts_names_by_id_using_native_forms(tmp_path) -> None:
    out = tmp_path / "out"  # does not exist yet — write_artifacts must create it
    artifacts = {
        "diagram": SvgArtifact(CIRCLE, id="s1"),
        "clue": TextArtifact("ROAD", id="t1"),
    }
    paths = write_artifacts(artifacts, out)

    # Named by id (not the map key), each in its native form.
    assert paths == [out / "s1.svg", out / "t1.txt"]
    assert (out / "s1.svg").read_text(encoding="utf-8") == CIRCLE
    assert (out / "t1.txt").read_text(encoding="utf-8") == "ROAD"
