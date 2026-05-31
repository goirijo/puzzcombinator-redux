"""End-to-end: author -> serialize -> reload -> order -> inspect I/O -> render."""

from __future__ import annotations

from puzzcombinator import (
    CaesarCipherPuzzle,
    GraphBuilder,
    chronological_order,
    game_master_binder,
    player_pages,
    produced_outputs,
)
from puzzcombinator.serialization import from_json, to_json


def test_full_flow() -> None:
    cipher = CaesarCipherPuzzle.from_plaintext("c1", plaintext="FOUNTAIN", shift=3)
    graph = (
        GraphBuilder()
        .node("start", label="Welcome")
        .node("solve", action="solve", label="Caesar gate", notes="leave on the bench")
        .node("end", label="Treasure")
        .connect("start", "solve", puzzle=cipher)
        .connect("solve", "end", text="Go to the fountain.")
        .build()
    )

    # Serialize and reload — value-equal.
    reloaded = from_json(to_json(graph))
    assert reloaded == graph

    # Solve order respects the chain.
    assert [n.id for n in chronological_order(reloaded)] == ["start", "solve", "end"]

    # The solve action's output (the revealed clue) flows on its outgoing edge.
    assert [c.text for c in produced_outputs(reloaded, "solve")] == ["Go to the fountain."]

    # The player printable shows the prompt; the game-master binder shows the solution.
    player_page = player_pages(reloaded)["players/c1-puzzle.html"]
    assert "IRXQWDLQ" in player_page  # ciphertext (FOUNTAIN shifted by 3)
    assert "FOUNTAIN" not in player_page

    gm_binder = game_master_binder(reloaded)
    assert "FOUNTAIN" in gm_binder  # solution (answer key)
    assert "leave on the bench" in gm_binder  # designer notes
    assert "Production checklist" in gm_binder
