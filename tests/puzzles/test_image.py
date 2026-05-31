from __future__ import annotations

import base64
import struct
import zlib

import pytest

from puzzcombinator import Audience, ImagePuzzle
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
    puzzle = ImagePuzzle.from_bytes("img1", data, mime="image/png", prompt="hue?", answer="RED")
    assert puzzle.data_uri.startswith("data:image/png;base64,")
    decoded = base64.b64decode(puzzle.data_uri.split(",", 1)[1])
    assert decoded == data


def test_from_file_guesses_mime(tmp_path) -> None:
    p = tmp_path / "clue.png"
    p.write_bytes(_png(1, 1, (0, 0, 255)))
    puzzle = ImagePuzzle.from_file("img1", p, prompt="look")
    assert puzzle.data_uri.startswith("data:image/png;base64,")


def test_from_file_unknown_mime_raises(tmp_path) -> None:
    p = tmp_path / "clue.unknownext"
    p.write_bytes(b"nope")
    with pytest.raises(PuzzleError):
        ImagePuzzle.from_file("img1", p)


def test_non_data_uri_rejected() -> None:
    with pytest.raises(PuzzleError):
        ImagePuzzle("img1", data_uri="https://example.com/x.png")


def test_payload_roundtrip_is_byte_exact() -> None:
    data = _png(3, 2, (0, 128, 0))
    puzzle = ImagePuzzle.from_bytes("img1", data, mime="image/png", answer="GREEN", alt="bar")
    rebuilt = ImagePuzzle.from_payload("img1", puzzle.to_payload())
    assert rebuilt == puzzle
    assert base64.b64decode(rebuilt.data_uri.split(",", 1)[1]) == data


def test_player_view_hides_answer_gm_shows_it() -> None:
    data = _png(1, 1, (1, 2, 3))
    puzzle = ImagePuzzle.from_bytes("img1", data, mime="image/png", answer="SECRET")
    player = puzzle.render(Audience.PLAYER).markup
    gm = puzzle.render(Audience.GAME_MASTER).markup
    assert "data:image/png;base64," in player
    assert "SECRET" not in player
    assert "SECRET" in gm


def test_eq_and_hash() -> None:
    data = _png(1, 1, (9, 9, 9))
    a = ImagePuzzle.from_bytes("img1", data, mime="image/png")
    b = ImagePuzzle.from_bytes("img1", data, mime="image/png")
    assert a == b
    assert a != "not a puzzle"
    assert len({a, b}) == 1
