from __future__ import annotations

import pytest

from puzzcombinator import CaesarCipherPuzzle, CipherArtifact
from puzzcombinator.puzzles.cipher import _caesar


def test_caesar_encode_decode_roundtrip() -> None:
    plain = "Attack at Dawn!"
    encoded = _caesar(plain, 7)
    assert encoded != plain
    assert _caesar(encoded, -7) == plain


def test_from_plaintext_generates_ciphertext() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="HELLO", shift=3, id="c1")
    assert puzzle.ciphertext == "KHOOR"
    assert puzzle.shift == 3


def test_solution_is_derivable() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=5, id="c1")
    assert puzzle.solution == "FOUNTAIN"


def test_omitted_id_is_auto_generated_and_distinct() -> None:
    # No id supplied: the base class auto-generates one as "{type_name}-{uuid}".
    a = CaesarCipherPuzzle.from_plaintext(plaintext="HI", shift=1)
    b = CaesarCipherPuzzle.from_plaintext(plaintext="HI", shift=1)
    assert a.id.startswith("caesar_cipher-")
    assert a.id != b.id  # unique even for identical content


def test_artifacts_named_and_id_prefixed() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="HI", shift=1, id="c1")
    assert set(puzzle.artifacts()) == {"cipher", "shift", "solution"}
    cipher = puzzle.artifacts("cipher")
    assert cipher.name == "cipher"
    assert cipher.id == "c1-cipher"


def test_three_pieces_split_prompt_shift_and_solution() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    # The "cipher" piece is the prompt to decode — neither shift nor answer baked in.
    cipher = puzzle.artifacts("cipher")
    assert (cipher.shift, cipher.solution) == (None, None)
    # The "shift" piece carries only the Caesar shift.
    shift = puzzle.artifacts("shift")
    assert (shift.shift, shift.solution) == (3, None)
    assert shift.id == "c1-shift"
    # The "solution" piece carries only the decoded answer.
    solution = puzzle.artifacts("solution")
    assert solution.solution == "FOUNTAIN"
    assert solution.id == "c1-solution"


def test_each_piece_renders_only_its_own_content() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    cipher = puzzle.artifacts("cipher").render().markup
    shift = puzzle.artifacts("shift").render().markup
    solution = puzzle.artifacts("solution").render().markup
    # the prompt shows the ciphertext but neither the shift nor the answer
    assert "IRXQWDLQ" in cipher and "FOUNTAIN" not in cipher
    # the shift piece shows the shift but not the answer
    assert "3" in shift and "FOUNTAIN" not in shift
    # the solution piece shows the answer
    assert "FOUNTAIN" in solution


def test_artifacts_drops_audience_kwarg() -> None:
    # The audience split is gone: artifacts() no longer accepts an audience.
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="HI", shift=1, id="c1")
    with pytest.raises(TypeError):
        puzzle.artifacts(audience="anything")  # type: ignore[call-arg]


def test_artifact_payload_roundtrip() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="CODE", shift=4, id="c1")
    art = puzzle.artifacts("solution")
    rebuilt = CipherArtifact.from_payload(name=art.name, id=art.id, payload=art.to_payload())
    assert rebuilt == art


def test_artifact_eq_and_hash() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="CODE", shift=4, id="c1")
    a = puzzle.artifacts("cipher")
    b = puzzle.artifacts("cipher")
    assert a == b
    assert a != "not an artifact"
    assert len({a, b}) == 1
