from __future__ import annotations

import pytest

from puzzcombinator import (
    Audience,
    CrosswordPuzzle,
    GraphBuilder,
)
from puzzcombinator.errors import PuzzleError
from puzzcombinator.puzzles.crossword import Slot
from puzzcombinator.serialization import from_json, to_json

# Solution grid:
#   C A T
#   A # O
#   R Y E
# Across: 1 CAT, 3 RYE.  Down: 1 CAR, 2 TOE.
GRID = ["CAT", "A#O", "RYE"]
ACROSS = {1: "Feline", 3: "Bread grain"}
DOWN = {1: "Automobile", 2: "Foot digit"}
HIGHLIGHT = [(0, 0), (1, 2), (2, 1)]  # C, O, Y -> "COY"


def _puzzle() -> CrosswordPuzzle:
    return CrosswordPuzzle("cw1", solution=GRID, across=ACROSS, down=DOWN, highlight=HIGHLIGHT)


def test_slots_and_numbering() -> None:
    across, down = _puzzle().slots()
    assert across == [Slot(1, 0, 0, "CAT"), Slot(3, 2, 0, "RYE")]
    assert down == [Slot(1, 0, 0, "CAR"), Slot(2, 0, 2, "TOE")]


def test_size_and_emergent_word() -> None:
    puzzle = _puzzle()
    assert puzzle.size == (3, 3)
    assert puzzle.emergent_word == "COY"


def test_lowercase_grid_is_normalized() -> None:
    puzzle = CrosswordPuzzle("cw", solution=["cat", "a#o", "rye"], across={}, down={})
    assert puzzle.solution == ["CAT", "A#O", "RYE"]


def test_player_render_hides_answers() -> None:
    markup = _puzzle().render(Audience.PLAYER).markup
    assert "Feline" in markup
    assert '<span class="len">(3)</span>' in markup  # enumeration shown
    assert '<span class="num">1</span></td>' in markup  # numbered but empty cell
    assert "Hidden word" not in markup


def test_game_master_render_shows_answers() -> None:
    markup = _puzzle().render(Audience.GAME_MASTER).markup
    assert '<span class="num">1</span>C' in markup  # filled cell
    assert '<span class="answer">CAT</span>' in markup
    assert "Hidden word" in markup
    assert "<strong>COY</strong>" in markup


def test_payload_roundtrip() -> None:
    puzzle = _puzzle()
    assert CrosswordPuzzle.from_payload("cw1", puzzle.to_payload()) == puzzle


def test_graph_json_roundtrip() -> None:
    builder = GraphBuilder()
    start = builder.node("start")
    solve = builder.node("solve", action="solve", label="The grid")
    end = builder.node("end")
    graph = (
        builder.connect(start, solve, puzzle=_puzzle())
        .connect(solve, end, text="The word is COY")
        .build()
    )
    assert from_json(to_json(graph)) == graph


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"solution": [], "across": {}, "down": {}}, "non-empty"),
        ({"solution": ["CAT", "AB"], "across": {}, "down": {}}, "width"),
        ({"solution": ["C1T"], "across": {}, "down": {}}, "must be a letter"),
        ({"solution": GRID, "across": {9: "x"}, "down": {}}, "non-existent"),
        ({"solution": GRID, "across": {}, "down": {9: "x"}}, "non-existent"),
        (
            {"solution": GRID, "across": {}, "down": {}, "highlight": [(5, 5)]},
            "out of bounds",
        ),
        (
            {"solution": GRID, "across": {}, "down": {}, "highlight": [(1, 1)]},
            "is a block",
        ),
    ],
)
def test_malformed_definitions_raise(kwargs: dict, match: str) -> None:
    with pytest.raises(PuzzleError, match=match):
        CrosswordPuzzle("bad", **kwargs)
