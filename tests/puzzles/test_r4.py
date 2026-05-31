from __future__ import annotations

import pytest

from puzzcombinator import (
    Audience,
    GraphBuilder,
    R4DecoderPuzzle,
)
from puzzcombinator.errors import PuzzleError
from puzzcombinator.puzzles.r4 import _grid_dim
from puzzcombinator.serialization import from_json, to_json


@pytest.mark.parametrize(
    ("n", "dim"),
    [(1, 2), (9, 4), (10, 4), (16, 4), (17, 5), (25, 6)],
)
def test_grid_dim(n: int, dim: int) -> None:
    assert _grid_dim(n) == dim


@pytest.mark.parametrize(
    "message",
    ["MEET AT DAWN", "FOLLOWTHEROADTOTHEOLDOAKTREE", "HI", "ODDGRIDMESSAGEHERE"],
)
def test_encode_then_decode_recovers_message(message: str) -> None:
    cleaned = "".join(c for c in message.upper() if "A" <= c <= "Z")
    puzzle = R4DecoderPuzzle.from_message("r4", message, seed=7)
    assert puzzle.message == cleaned
    assert puzzle.message_length == len(cleaned)


def test_non_letters_are_dropped() -> None:
    puzzle = R4DecoderPuzzle.from_message("r4", "go! 2 the dock.", seed=1)
    assert puzzle.message == "GOTHEDOCK"


def test_determinism() -> None:
    a = R4DecoderPuzzle.from_message("r4", "MEETATDAWN", seed=5)
    b = R4DecoderPuzzle.from_message("r4", "MEETATDAWN", seed=5)
    c = R4DecoderPuzzle.from_message("r4", "MEETATDAWN", seed=6)
    assert a == b
    assert a != c


def test_generated_grille_is_valid_turning_grille() -> None:
    # One open square per 4-cell orbit; reading covers each non-centre cell once.
    puzzle = R4DecoderPuzzle.from_message("r4", "ODDGRIDMESSAGEHERE", seed=2)
    dim = puzzle.size
    assert dim == 5
    assert puzzle.grille[dim // 2][dim // 2] == "#"  # odd centre opaque
    # reading sequence is a permutation of all non-centre cells
    seq = puzzle.reading_sequence
    assert len(seq) == dim * dim - 1
    assert len(set(seq)) == len(seq)


def test_reveal_flags_control_player_view() -> None:
    puzzle = R4DecoderPuzzle.from_message(
        "r4", "MEETATDAWN", seed=3, reveal_grid=False, reveal_decoder=False
    )
    player = puzzle.render(Audience.PLAYER).markup
    assert "<svg" in player
    assert "polygon" in player  # orientation marker present
    assert "<text" not in player  # no letters revealed
    assert 'fill="black"' not in player  # no shading revealed

    revealed = (
        R4DecoderPuzzle.from_message(
            "r4", "MEETATDAWN", seed=3, reveal_grid=True, reveal_decoder=True
        )
        .render(Audience.PLAYER)
        .markup
    )
    assert "<text" in revealed
    assert 'fill="black"' in revealed


def test_game_master_always_reveals_everything() -> None:
    # Even with both player flags off, the game master sees letters, shading, answer.
    puzzle = R4DecoderPuzzle.from_message(
        "r4", "MEETATDAWN", seed=3, reveal_grid=False, reveal_decoder=False
    )
    gm = puzzle.render(Audience.GAME_MASTER).markup
    assert "<text" in gm
    assert 'fill="black"' in gm
    assert "MEETATDAWN" in gm
    assert "Reading order" in gm


def test_svg_assets_are_standalone_documents() -> None:
    puzzle = R4DecoderPuzzle.from_message("r4", "MEETATDAWN", seed=3)
    assets = puzzle.svg_assets(Audience.PLAYER)
    assert set(assets) == {"grid", "decoder"}
    for svg in assets.values():
        assert svg.startswith("<svg")
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg
        assert svg.endswith("</svg>")
    # Player view honours reveal flags; game master reveals everything.
    blank = R4DecoderPuzzle.from_message(
        "r4", "MEETATDAWN", seed=3, reveal_grid=False, reveal_decoder=False
    )
    assert "<text" not in blank.svg_assets(Audience.PLAYER)["grid"]
    assert "<text" in blank.svg_assets(Audience.GAME_MASTER)["grid"]


def test_payload_roundtrip() -> None:
    puzzle = R4DecoderPuzzle.from_message("r4", "MEETATDAWN", seed=4, reveal_grid=False)
    assert R4DecoderPuzzle.from_payload("r4", puzzle.to_payload()) == puzzle


def test_graph_json_roundtrip() -> None:
    puzzle = R4DecoderPuzzle.from_message("decoder", "FINDTHEKEY", seed=8)
    graph = (
        GraphBuilder()
        .node("start")
        .node("solve", action="solve", label="The grille")
        .node("end")
        .connect("start", "solve", puzzle=puzzle)
        .connect("solve", "end", text="The message is FIND THE KEY")
        .build()
    )
    assert from_json(to_json(graph)) == graph


def test_message_too_long_for_explicit_size() -> None:
    with pytest.raises(PuzzleError, match="exceeds capacity"):
        R4DecoderPuzzle.from_message("r4", "TOOMANYLETTERS", size=2, seed=1)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"grid": [], "grille": [], "message_length": 0}, "non-empty"),
        (
            {"grid": ["AB", "CD"], "grille": ["O#", "##"], "message_length": 99},
            "out of range",
        ),
        (
            {"grid": ["ABC", "DE"], "grille": ["O#O", "###", "###"], "message_length": 0},
            "square",
        ),
        (
            {"grid": ["A1", "BC"], "grille": ["O#", "##"], "message_length": 0},
            "must be A-Z",
        ),
        (
            {"grid": ["AB", "CD"], "grille": ["OX", "##"], "message_length": 0},
            "must be",
        ),
        (
            # 3x3 with an open centre (illegal)
            {
                "grid": ["ABC", "DEF", "GHI"],
                "grille": ["#O#", "#O#", "###"],
                "message_length": 0,
            },
            "centre",
        ),
        (
            # 2x2 orbit with two open cells (illegal turning grille)
            {"grid": ["AB", "CD"], "grille": ["OO", "##"], "message_length": 0},
            "exactly one open",
        ),
    ],
)
def test_malformed_definitions_raise(kwargs: dict, match: str) -> None:
    with pytest.raises(PuzzleError, match=match):
        R4DecoderPuzzle("bad", **kwargs)
