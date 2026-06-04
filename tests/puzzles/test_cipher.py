from __future__ import annotations

from puzzcombinator import Audience, CaesarCipherPuzzle, CipherArtifact
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
    player = puzzle.artifacts("cipher")
    assert player.name == "cipher"
    assert player.id == "c1-cipher"


def test_player_artifact_hides_solution_game_master_reveals_it() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    assert puzzle.artifacts("cipher").solution is None
    gm = puzzle.artifacts("cipher", audience=Audience.GAME_MASTER)
    assert gm.solution == "FOUNTAIN"


def test_artifact_payload_roundtrip() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="CODE", shift=4, id="c1")
    art = puzzle.artifacts("cipher", audience=Audience.GAME_MASTER)
    rebuilt = CipherArtifact.from_payload(
        name=art.name, audience=art.audience, id=art.id, payload=art.to_payload()
    )
    assert rebuilt == art


def test_artifact_eq_and_hash() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="CODE", shift=4, id="c1")
    a = puzzle.artifacts("cipher")
    b = puzzle.artifacts("cipher")
    assert a == b
    assert a != "not an artifact"
    assert len({a, b}) == 1
