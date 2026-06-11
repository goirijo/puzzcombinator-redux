"""Each artifact's native file form (the ``native()`` contract) and id legibility.

The exporters that *consume* ``native()`` (``write_artifact`` / ``write_artifacts``) are
tested in ``tests/rendering/test_export.py``; here we pin what each artifact *reports*.
"""

from __future__ import annotations

import struct
import zlib

from puzzcombinator.artifacts import (
    CompositeArtifact,
    ImageArtifact,
    SvgArtifact,
    TextArtifact,
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


# --- native(): each artifact's source form, read from the payload (not the render) ---


def test_text_native_is_the_raw_string() -> None:
    # title/monospace are render-only hints, dropped — the native form is the text itself.
    art = TextArtifact("Search the LIBRARY", title="Clue", monospace=True, id="t1")
    assert art.native() == (".txt", b"Search the LIBRARY")


def test_svg_native_is_markup_verbatim() -> None:
    # No override on SvgArtifact: the base default serves an svg-kind render verbatim.
    assert SvgArtifact(CIRCLE, id="s1").native() == (".svg", CIRCLE.encode("utf-8"))


def test_image_native_roundtrips_bytes_with_mime_extension() -> None:
    data = _png(3, 2, (0, 128, 0))
    art = ImageArtifact.from_bytes(data, mime="image/png", id="img1")
    assert art.native() == (".png", data)


def test_image_native_picks_jpg_for_jpeg() -> None:
    ext, _ = ImageArtifact("data:image/jpeg;base64,/9j/", id="img2").native()
    assert ext == ".jpg"


def test_composite_has_no_native_form() -> None:
    assert CompositeArtifact([TextArtifact("hi")], id="c1").native() is None


# --- the name folds into the auto-generated id, so files read legibly ---


def test_named_artifact_id_folds_in_name() -> None:
    assert TextArtifact("hi", name="instructions").id.startswith("instructions-")


def test_unnamed_artifact_id_keeps_its_type() -> None:
    assert TextArtifact("hi").id.startswith("text-")
