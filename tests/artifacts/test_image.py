from __future__ import annotations

import base64
import struct
import zlib

import pytest

from puzzcombinator.artifacts import ImageArtifact
from puzzcombinator.errors import PuzzleError


def _png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """A real, valid solid-colour PNG built with the stdlib (no Pillow)."""

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


def test_from_bytes_builds_data_uri() -> None:
    data = _png(2, 1, (255, 0, 0))
    art = ImageArtifact.from_bytes(data, mime="image/png", alt="a red dot", id="img1")
    assert art.data_uri.startswith("data:image/png;base64,")
    decoded = base64.b64decode(art.data_uri.split(",", 1)[1])
    assert decoded == data


def test_from_file_guesses_mime(tmp_path) -> None:
    p = tmp_path / "clue.png"
    p.write_bytes(_png(1, 1, (0, 0, 255)))
    art = ImageArtifact.from_file(p, alt="look", id="img1")
    assert art.data_uri.startswith("data:image/png;base64,")


def test_from_file_unknown_mime_raises(tmp_path) -> None:
    p = tmp_path / "clue.unknownext"
    p.write_bytes(b"nope")
    with pytest.raises(PuzzleError):
        ImageArtifact.from_file(p, id="img1")


def test_non_data_uri_rejected() -> None:
    with pytest.raises(PuzzleError):
        ImageArtifact("https://example.com/x.png")


def test_render_emits_the_image() -> None:
    uri = ImageArtifact.from_bytes(_png(1, 1, (1, 2, 3)), mime="image/png").data_uri
    markup = ImageArtifact(uri, alt="a clue", id="p").render().markup
    assert "data:image/png;base64," in markup
    assert 'alt="a clue"' in markup


def test_payload_roundtrip_is_byte_exact() -> None:
    data = _png(3, 2, (0, 128, 0))
    art = ImageArtifact.from_bytes(data, mime="image/png", alt="bar", id="img1")
    rebuilt = ImageArtifact.from_payload(name=art.name, id=art.id, payload=art.to_payload())
    assert rebuilt == art
    assert base64.b64decode(rebuilt.data_uri.split(",", 1)[1]) == data


def test_eq_and_hash() -> None:
    data = _png(1, 1, (9, 9, 9))
    uri = ImageArtifact.from_bytes(data, mime="image/png").data_uri
    a = ImageArtifact(uri, id="img1")
    b = ImageArtifact(uri, id="img1")
    assert a == b
    assert a != "not an artifact"
    assert len({a, b}) == 1
