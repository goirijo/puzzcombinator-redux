from __future__ import annotations

import pytest

from puzzcombinator import R4DecoderPuzzle, R4PieceArtifact
from puzzcombinator.errors import PuzzleError
from puzzcombinator.puzzles.r4 import _grid_dim


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
    puzzle = R4DecoderPuzzle.from_message(message, seed=7, id="r4")
    assert puzzle.message == cleaned
    assert puzzle.message_length == len(cleaned)


def test_non_letters_are_dropped() -> None:
    puzzle = R4DecoderPuzzle.from_message("go! 2 the dock.", seed=1, id="r4")
    assert puzzle.message == "GOTHEDOCK"


def test_determinism() -> None:
    a = R4DecoderPuzzle.from_message("MEETATDAWN", seed=5, id="r4")
    b = R4DecoderPuzzle.from_message("MEETATDAWN", seed=5, id="r4")
    c = R4DecoderPuzzle.from_message("MEETATDAWN", seed=6, id="r4")
    assert (a.grid, a.grille) == (b.grid, b.grille)
    assert (a.grid, a.grille) != (c.grid, c.grille)


def test_generated_grille_is_valid_turning_grille() -> None:
    # One open square per 4-cell orbit; reading covers each non-centre cell once.
    puzzle = R4DecoderPuzzle.from_message("ODDGRIDMESSAGEHERE", seed=2, id="r4")
    dim = puzzle.size
    assert dim == 5
    assert puzzle.grille[dim // 2][dim // 2] == "#"  # odd centre opaque
    # reading sequence is a permutation of all non-centre cells
    seq = puzzle.reading_sequence
    assert len(seq) == dim * dim - 1
    assert len(set(seq)) == len(seq)


def test_svg_pieces_are_inline_svg_sheets() -> None:
    puzzle = R4DecoderPuzzle.from_message("MEETATDAWN", seed=3, id="r4")
    pieces = puzzle.artifacts()
    assert set(pieces) == {
        "text_blank",
        "grille_blank",
        "solution_grille",
        "solution_grid",
        "solution_text",
    }
    for name in ("text_blank", "grille_blank", "solution_grille", "solution_grid"):
        fragment = pieces[name].render()
        assert fragment.kind == "svg"
        assert fragment.markup.startswith("<svg")
        assert 'xmlns="http://www.w3.org/2000/svg"' in fragment.markup
        assert fragment.markup.endswith("</svg>")


def test_blanks_are_empty_and_identical() -> None:
    puzzle = R4DecoderPuzzle.from_message("MEETATDAWN", seed=3, id="r4")
    text_blank = puzzle.artifacts("text_blank").render().markup
    grille_blank = puzzle.artifacts("grille_blank").render().markup
    # the two starting sheets are identical empty grids (same drawing, different name)
    assert text_blank == grille_blank
    assert "<text" not in text_blank  # blank — no letters
    assert 'fill="black"' not in text_blank  # blank — no shading


def test_solution_grid_is_the_filled_grid() -> None:
    puzzle = R4DecoderPuzzle.from_message("MEETATDAWN", seed=3, id="r4")
    solution = puzzle.artifacts("solution_grid").render().markup
    assert puzzle.artifacts("solution_grid").id == "r4-solution_grid"
    # the orientation marker is on every sheet, but only the filled grid draws letters
    assert "polygon" in solution
    assert solution.count("<text") == puzzle.size * puzzle.size  # every cell filled


def test_solution_text_carries_the_decoded_message() -> None:
    puzzle = R4DecoderPuzzle.from_message("MEETATDAWN", seed=3, id="r4")
    text = puzzle.artifacts("solution_text")
    assert text.render().kind == "html"
    assert puzzle.message in text.text


def test_solution_grille_honours_reveal_decoder() -> None:
    shaded = R4DecoderPuzzle.from_message("MEETATDAWN", seed=3, reveal_decoder=True, id="r4")
    blank = R4DecoderPuzzle.from_message("MEETATDAWN", seed=3, reveal_decoder=False, id="r4")
    assert 'fill="black"' in shaded.artifacts("solution_grille").render().markup
    assert 'fill="black"' not in blank.artifacts("solution_grille").render().markup


def test_piece_artifact_payload_roundtrip() -> None:
    puzzle = R4DecoderPuzzle.from_message("MEETATDAWN", seed=4, id="r4")
    art = puzzle.artifacts("solution_grid")
    rebuilt = R4PieceArtifact.from_payload(name=art.name, id=art.id, payload=art.to_payload())
    assert rebuilt == art


def test_message_too_long_for_explicit_size() -> None:
    with pytest.raises(PuzzleError, match="exceeds capacity"):
        R4DecoderPuzzle.from_message("TOOMANYLETTERS", size=2, seed=1, id="r4")


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
