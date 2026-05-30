from __future__ import annotations

from puzzcombinator import Audience, CaesarCipherPuzzle, Graph, RenderFragment, render_binder


def test_player_fragment_shows_ciphertext_not_answer() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext("c1", plaintext="FOUNTAIN", shift=3)
    fragment = puzzle.render(Audience.PLAYER)
    assert fragment.kind == "html"
    assert puzzle.ciphertext in fragment.markup
    assert "FOUNTAIN" not in fragment.markup


def test_game_master_fragment_shows_solution() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext("c1", plaintext="FOUNTAIN", shift=3)
    fragment = puzzle.render(Audience.GAME_MASTER)
    assert "FOUNTAIN" in fragment.markup


def test_svg_fragment_is_embeddable() -> None:
    fragment = RenderFragment.svg("<svg><rect/></svg>")
    assert fragment.kind == "svg"
    assert fragment.markup.startswith("<svg")


def test_binder_player_walks_in_order(cipher_hunt: Graph) -> None:
    html = render_binder(cipher_hunt, audience=Audience.PLAYER)
    assert "<!DOCTYPE html>" in html
    assert "Treasure Hunt" in html
    # Player binder shows the ciphertext but not the solution or designer notes.
    assert "IRXQWDLQ" in html  # FOUNTAIN shifted by 3
    assert "hide under the doormat" not in html


def test_binder_game_master_includes_notes_and_answers(cipher_hunt: Graph) -> None:
    html = render_binder(cipher_hunt, audience=Audience.GAME_MASTER)
    assert "Master Binder" in html
    assert "hide under the doormat" in html
    assert "FOUNTAIN" in html
    assert "Go to the fountain." in html  # revealed downstream clue
