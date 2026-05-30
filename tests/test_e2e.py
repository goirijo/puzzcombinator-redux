"""End-to-end: author -> serialize -> reload -> order -> solve -> render."""

from __future__ import annotations

from puzzcombinator import (
    Audience,
    CaesarCipherPuzzle,
    Content,
    GraphBuilder,
    NodeKind,
    chronological_order,
    render_binder,
    unlocked_outputs,
)
from puzzcombinator.serialization import from_json, to_json


def test_full_flow() -> None:
    cipher = CaesarCipherPuzzle.from_plaintext("c1", plaintext="FOUNTAIN", shift=3)
    graph = (
        GraphBuilder()
        .node("start", kind=NodeKind.START, label="Welcome")
        .node("c1", payload=cipher, label="Caesar gate", notes="leave on the bench")
        .node("end", kind=NodeKind.END, label="Treasure")
        .connect("start", "c1", content=Content(text="Decode to proceed."))
        .connect("c1", "end", content=Content(text="Go to the fountain."))
        .build()
    )

    # Serialize and reload — value-equal.
    reloaded = from_json(to_json(graph))
    assert reloaded == graph

    # Solve order respects the chain.
    assert [n.id for n in chronological_order(reloaded)] == ["start", "c1", "end"]

    # Correct submission unlocks the downstream clue; wrong one does not.
    unlocked = unlocked_outputs(reloaded, "c1", "fountain")
    assert [c.text for c in unlocked] == ["Go to the fountain."]
    assert unlocked_outputs(reloaded, "c1", "nope") == []

    # The player binder shows the prompt; the game-master binder shows the solution.
    player_binder = render_binder(reloaded, audience=Audience.PLAYER)
    assert "IRXQWDLQ" in player_binder  # ciphertext
    assert "FOUNTAIN" not in player_binder

    gm_binder = render_binder(reloaded, audience=Audience.GAME_MASTER)
    assert "FOUNTAIN" in gm_binder  # solution
    assert "leave on the bench" in gm_binder  # designer notes
