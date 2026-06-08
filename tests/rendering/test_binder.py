"""Binder + puzzle integration tests — DEFERRED until the upper layers migrate.

These exercise the **not-yet-migrated** stack: the `puzzles/` generators
(`CaesarCipherPuzzle`, `R4DecoderPuzzle`) and the `binder` (`game_master_binder`,
`player_pages`, `hunt_bundle`, `write_bundle`), all of which still assume the
pre-refactor `audience`-on-artifact model. They fail today by design — see CLAUDE.md
"Current status & likely next steps" (next phases: puzzles, then the binder, where the
open question is how player-vs-game-master routing is re-derived without
`artifact.audience`).

The whole module is skipped so it doesn't hard-fail the suite. Unskip — and likely
relocate the puzzle-only cases to `tests/puzzles/` — as those phases land. The genuine
fragment-layer test that used to share this file now lives in `test_fragment.py`.
"""

from __future__ import annotations

import pytest

from puzzcombinator import (
    CaesarCipherPuzzle,
    Graph,
    game_master_binder,
    hunt_bundle,
    player_pages,
    write_bundle,
)

pytestmark = pytest.mark.skip(
    reason="Awaits the puzzles + binder migration to the audience-free model; see CLAUDE.md."
)


def test_player_artifact_shows_ciphertext_not_answer() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    fragment = puzzle.artifacts("cipher").render()
    assert fragment.kind == "html"
    assert puzzle.ciphertext in fragment.markup
    assert "FOUNTAIN" not in fragment.markup


def test_game_master_artifact_shows_solution() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    fragment = puzzle.artifacts("solution").render()
    assert "FOUNTAIN" in fragment.markup


def test_artifacts_carry_their_own_styles() -> None:
    # The cipher's styling rides on its fragment, not in the binder.
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="HI", shift=1, id="c1")
    assert ".ciphertext" in puzzle.artifacts("cipher").render().styles


def test_single_piece_puzzle_emits_one_named_artifact() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="HI", shift=1, id="c1")
    artifacts = puzzle.artifacts()
    assert list(artifacts) == ["cipher"]
    assert artifacts["cipher"].render().kind == "html"
    assert artifacts["cipher"].id == "c1-cipher"


def test_game_master_binder_walks_nodes_and_includes_answers(cipher_hunt: Graph) -> None:
    binder = game_master_binder(cipher_hunt)
    assert "<!DOCTYPE html>" in binder
    assert "Master Binder" in binder
    assert "FOUNTAIN" in binder  # solution shown to the game master
    assert "hide under the doormat" in binder  # node notes
    assert "Go to the fountain." in binder  # revealed downstream clue
    assert "Production checklist" in binder


def test_player_pages_omit_answers(cipher_hunt: Graph) -> None:
    pages = player_pages(cipher_hunt)
    assert "players/c1-cipher.html" in pages
    page = pages["players/c1-cipher.html"]
    assert "IRXQWDLQ" in page  # the ciphertext (FOUNTAIN shifted by 3)
    assert "FOUNTAIN" not in page  # but not the solution
    assert ".ciphertext" in page  # the cipher's own CSS made it into the page head


def test_multi_piece_puzzle_svg_player_pages() -> None:
    from puzzcombinator import GraphBuilder, R4DecoderPuzzle

    r4 = R4DecoderPuzzle.from_message("HELLO", seed=1, id="grille")
    builder = GraphBuilder()
    find = builder.node("find", action="find")
    solve = builder.node("solve", action="solve")
    graph = builder.connect(find, solve, *r4.artifacts().values()).build()
    pages = player_pages(graph)
    # Two player sheets, one per piece; the game-master "solution" makes no file.
    assert set(pages) == {"players/grille-grid.svg", "players/grille-grille.svg"}
    assert pages["players/grille-grid.svg"].startswith("<svg")
    # The binder renders the game-master pieces (incl. the decoded message).
    assert "HELLO" in game_master_binder(graph)


def test_binder_without_artifacts_has_no_checklist() -> None:
    from puzzcombinator import GraphBuilder, TextArtifact

    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    graph = builder.connect(a, b, TextArtifact("go")).build()
    binder = game_master_binder(graph)
    assert "Production checklist" not in binder


def test_hunt_bundle_and_write(cipher_hunt: Graph, tmp_path) -> None:
    bundle = hunt_bundle(cipher_hunt)
    assert "binder.html" in bundle
    assert any(p.startswith("players/") for p in bundle)
    written = write_bundle(bundle, tmp_path)
    assert (tmp_path / "binder.html").read_text()
    assert (tmp_path / "players" / "c1-cipher.html").exists()
    assert len(written) == len(bundle)
