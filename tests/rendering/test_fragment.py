from __future__ import annotations

from puzzcombinator import (
    Artifact,
    Audience,
    CaesarCipherPuzzle,
    Graph,
    RenderFragment,
    game_master_binder,
    hunt_bundle,
    player_pages,
    write_bundle,
)


def test_player_fragment_shows_ciphertext_not_answer() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    fragment = puzzle.render(Audience.PLAYER)
    assert fragment.kind == "html"
    assert puzzle.ciphertext in fragment.markup
    assert "FOUNTAIN" not in fragment.markup


def test_game_master_fragment_shows_solution() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")
    fragment = puzzle.render(Audience.GAME_MASTER)
    assert "FOUNTAIN" in fragment.markup


def test_svg_fragment_is_embeddable() -> None:
    fragment = RenderFragment.svg("<svg><rect/></svg>")
    assert fragment.kind == "svg"
    assert fragment.markup.startswith("<svg")


def test_fragments_carry_their_own_styles() -> None:
    # The cipher's styling rides on its fragment, not in the binder.
    fragment = CaesarCipherPuzzle.from_plaintext(plaintext="HI", shift=1, id="c1").render(
        Audience.PLAYER
    )
    assert ".ciphertext" in fragment.styles


def test_default_player_artifact_is_one_html_page() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="HI", shift=1, id="c1")
    artifacts = puzzle.player_artifacts()
    assert len(artifacts) == 1
    assert isinstance(artifacts[0], Artifact)
    assert artifacts[0].fragment.kind == "html"


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
    assert "players/c1-puzzle.html" in pages
    page = pages["players/c1-puzzle.html"]
    assert "IRXQWDLQ" in page  # the ciphertext (FOUNTAIN shifted by 3)
    assert "FOUNTAIN" not in page  # but not the solution
    assert ".ciphertext" in page  # the cipher's own CSS made it into the page head


def test_edge_puzzle_svg_player_pages() -> None:
    from puzzcombinator import GraphBuilder, R4DecoderPuzzle

    r4 = R4DecoderPuzzle.from_message("HELLO", seed=1, id="grille")
    builder = GraphBuilder()
    find = builder.node("find", action="find")
    solve = builder.node("solve", action="solve")
    graph = builder.connect(find, solve, puzzle=r4).build()
    pages = player_pages(graph)
    assert "players/grille-grid.svg" in pages
    assert "players/grille-decoder.svg" in pages
    assert pages["players/grille-grid.svg"].startswith("<svg")
    # The binder renders the R4 game-master view on the solve node's incoming edge.
    assert "R4 Decoder" in game_master_binder(graph)


def test_binder_without_artifacts_has_no_checklist() -> None:
    from puzzcombinator import GraphBuilder

    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    graph = builder.connect(a, b, text="go").build()
    binder = game_master_binder(graph)
    assert "Production checklist" not in binder


def test_hunt_bundle_and_write(cipher_hunt: Graph, tmp_path) -> None:
    bundle = hunt_bundle(cipher_hunt)
    assert "binder.html" in bundle
    assert any(p.startswith("players/") for p in bundle)
    written = write_bundle(bundle, tmp_path)
    assert (tmp_path / "binder.html").read_text()
    assert (tmp_path / "players" / "c1-puzzle.html").exists()
    assert len(written) == len(bundle)
