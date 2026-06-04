from __future__ import annotations

from puzzcombinator import (
    Audience,
    CaesarCipherPuzzle,
    Graph,
    RenderFragment,
    game_master_binder,
    hunt_bundle,
    player_pages,
    write_bundle,
)


def test_player_artifact_shows_ciphertext_not_answer() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    fragment = puzzle.artifacts("cipher").render()
    assert fragment.kind == "html"
    assert puzzle.ciphertext in fragment.markup
    assert "FOUNTAIN" not in fragment.markup


def test_game_master_artifact_shows_solution() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    fragment = puzzle.artifacts("cipher", audience=Audience.GAME_MASTER).render()
    assert "FOUNTAIN" in fragment.markup


def test_svg_fragment_is_embeddable() -> None:
    fragment = RenderFragment.svg("<svg><rect/></svg>")
    assert fragment.kind == "svg"
    assert fragment.markup.startswith("<svg")


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
    graph = builder.connect(
        find,
        solve,
        *r4.artifacts().values(),
        *r4.artifacts(audience=Audience.GAME_MASTER).values(),
    ).build()
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
    # Only a game-master artifact: nothing for players to print.
    graph = builder.connect(a, b, TextArtifact("go", audience=Audience.GAME_MASTER)).build()
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
