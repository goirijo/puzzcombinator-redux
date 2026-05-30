from __future__ import annotations

from puzzcombinator import CaesarCipherPuzzle
from puzzcombinator.puzzles.cipher import _caesar


def test_caesar_encode_decode_roundtrip() -> None:
    plain = "Attack at Dawn!"
    encoded = _caesar(plain, 7)
    assert encoded != plain
    assert _caesar(encoded, -7) == plain


def test_from_plaintext_generates_ciphertext() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext("c1", plaintext="HELLO", shift=3)
    assert puzzle.ciphertext == "KHOOR"
    assert puzzle.shift == 3


def test_solution_is_derivable() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext("c1", plaintext="FOUNTAIN", shift=5)
    assert puzzle.solution == "FOUNTAIN"


def test_payload_roundtrip() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext("c1", plaintext="CODE", shift=4)
    rebuilt = CaesarCipherPuzzle.from_payload("c1", puzzle.to_payload())
    assert rebuilt == puzzle


def test_puzzle_eq_and_hash() -> None:
    a = CaesarCipherPuzzle.from_plaintext("c1", plaintext="CODE", shift=4)
    b = CaesarCipherPuzzle.from_plaintext("c1", plaintext="CODE", shift=4)
    assert a == b
    assert a != "not a puzzle"
    assert len({a, b}) == 1
