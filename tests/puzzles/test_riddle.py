from __future__ import annotations

from puzzcombinator import Audience, RiddlePuzzle

parts = [
    "The person who built it sold it.",
    "The person who bought it never used it.",
    "The person who used it never saw it.",
]
answer = "coffin"


def test_construction() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    assert puzzle.answer == answer
    assert puzzle.parts == parts


def test_payload_roundtrip() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    rebuilt = RiddlePuzzle.from_payload("r1", puzzle.to_payload())
    assert rebuilt == puzzle


def test_puzzle_eq_and_hash() -> None:
    a = RiddlePuzzle("r1", riddle=parts, answer=answer)
    b = RiddlePuzzle("r1", riddle=parts, answer=answer)
    assert a == b
    assert a != "not a puzzle"
    assert len({a, b}) == 1


def test_render_hides_answer_from_player_shows_to_gm() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    assert answer not in puzzle.render(Audience.PLAYER).markup
    assert answer in puzzle.render(Audience.GAME_MASTER).markup


def test_player_artifacts_one_sheet_per_part() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer=answer)
    artifacts = puzzle.player_artifacts()
    assert [a.slug for a in artifacts] == [f"line{i}" for i in range(len(parts))]
    # the answer must never leak onto a player sheet
    assert all(answer not in a.fragment.markup for a in artifacts)
