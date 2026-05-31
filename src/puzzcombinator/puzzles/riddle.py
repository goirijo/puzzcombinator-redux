# This is a simple riddle puzzle. A riddle is a string and has a string as an
# answer. The riddle can be split into multiple substrings so that the answer
# is impossible to guess until they're all put together in the right order.

from __future__ import annotations

from typing import Any

from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.registry import register_puzzle
from puzzcombinator.rendering import presets
from puzzcombinator.rendering.fragment import Artifact, Audience, RenderFragment


@register_puzzle
class RiddlePuzzle(Puzzle):
    """A riddle has a unique answer and may be split into substrings so that it can't be guessed
    until they're all assembled."""

    type_name = "riddle"  # unique, stable registry key

    # TODO: make it accept just a string if it's not split into segments
    def __init__(self, id: str, *, riddle: list[str], answer: str) -> None:
        super().__init__(id)  # <-- stores self.id; do not skip
        self.parts = riddle
        self.answer = answer

    def to_payload(self) -> dict[str, Any]:
        return {"parts": self.parts, "answer": self.answer}

    @classmethod
    def from_payload(cls, id: str, payload: dict[str, Any]) -> RiddlePuzzle:
        return cls(id, riddle=payload["parts"], answer=payload["answer"])

    def render(self, audience: Audience) -> RenderFragment:
        if audience is Audience.PLAYER:
            return presets.text("\n".join(self.parts), title="Riddle", id=self.id, monospace=True)
        return presets.text(self.answer, title="Answer", id=self.id)

    def player_artifacts(self) -> list[Artifact]:
        """Each part of the riddle is found separately; the answer emerges when combined."""
        total = len(self.parts)
        return [
            Artifact(
                f"line{ix}",
                presets.text(part, title=f"Line {ix + 1}/{total}", id=self.id, monospace=True),
            )
            for ix, part in enumerate(self.parts)
        ]
