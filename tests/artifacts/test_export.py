from __future__ import annotations

import struct
import zlib

from puzzcombinator.artifacts import ImageArtifact, SvgArtifact, TextArtifact
from puzzcombinator.artifacts.export import write_image, write_svg, write_text

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


def test_write_text_writes_raw_string(tmp_path) -> None:
    art = TextArtifact("Search the LIBRARY", title="Clue", monospace=True, id="t1")
    path = write_text(art, tmp_path)
    assert path == tmp_path / "t1.txt"
    # Render hints (title/monospace) are dropped — the native form is the text itself.
    assert path.read_text(encoding="utf-8") == "Search the LIBRARY"


def test_write_svg_writes_markup_verbatim(tmp_path) -> None:
    path = write_svg(SvgArtifact(CIRCLE, id="s1"), tmp_path)
    assert path == tmp_path / "s1.svg"
    assert path.read_text(encoding="utf-8") == CIRCLE


def test_write_image_roundtrips_bytes_with_mime_extension(tmp_path) -> None:
    data = _png(3, 2, (0, 128, 0))
    art = ImageArtifact.from_bytes(data, mime="image/png", id="img1")
    path = write_image(art, tmp_path)
    assert path == tmp_path / "img1.png"
    assert path.read_bytes() == data


def test_write_image_picks_jpg_for_jpeg(tmp_path) -> None:
    art = ImageArtifact("data:image/jpeg;base64,/9j/", id="img2")
    path = write_image(art, tmp_path)
    assert path.suffix == ".jpg"
