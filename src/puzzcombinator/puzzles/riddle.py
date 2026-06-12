"""A riddle puzzle: a string with a unique answer, split into ordered pieces.

A riddle can be broken into substrings so the answer is impossible to guess until
they're assembled in the right order. Each piece is a separate
:class:`RiddleLineArtifact`, so the designer can **scatter** them across the graph
— a different line found at each of several locations — and the player assembles
them at a merge. The puzzle also emits the lines joined into one ``full_text``
artifact (the assembled riddle) and the answer, both as :class:`TextArtifact`.
"""

from __future__ import annotations

from typing import Any

from puzzcombinator.artifacts.registry import register_artifact
from puzzcombinator.artifacts.text import TextArtifact
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.rendering import presets
from puzzcombinator.rendering.fragment import Artifact, RenderFragment


@register_artifact
class RiddleLineArtifact(Artifact):
    """One line of a riddle, labelled with its position so the player can order them."""

    type_name = "riddle_line"

    def __init__(
        self,
        text: str,
        *,
        index: int,
        total: int,
        name: str | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(name=name if name is not None else f"line{index}", id=id)
        self.text = text
        self.index = index
        self.total = total

    def to_payload(self) -> dict[str, Any]:
        return {"text": self.text, "index": self.index, "total": self.total}

    @classmethod
    def from_payload(cls, *, name: str, id: str, payload: dict[str, Any]) -> RiddleLineArtifact:
        return cls(
            payload["text"],
            index=payload["index"],
            total=payload["total"],
            name=name,
            id=id,
        )

    def render(self) -> RenderFragment:
        return presets.text(
            self.text, title=f"Line {self.index + 1}/{self.total}", id=self.id, monospace=True
        )


class RiddlePuzzle(Puzzle):
    """Generates a riddle's ordered line artifacts plus its answer."""

    type_name = "riddle"

    def __init__(self, id: str | None = None, *, riddle: list[str], answer: str) -> None:
        super().__init__(id)
        self.parts = riddle
        self.answer = answer

    def _artifacts(self) -> list[Artifact]:
        """Build this puzzle's artifacts.

        Keys:
        - ``line0``, ``line1``, … ``line{N-1}`` — one per ordered riddle line.
        - ``full_text`` — every line joined into a single monospace text artifact.
        - ``answer`` — the riddle's answer, as a text artifact.
        """
        total = len(self.parts)
        out: list[Artifact] = [
            RiddleLineArtifact(
                part,
                index=ix,
                total=total,
                name=f"line{ix}",
                id=self.artifact_id(f"line{ix}"),
            )
            for ix, part in enumerate(self.parts)
        ]
        out.append(
            TextArtifact(
                "\n".join(self.parts),
                title="Riddle",
                monospace=True,
                name="full_text",
                id=self.artifact_id("full_text"),
            )
        )
        out.append(
            TextArtifact(
                self.answer,
                title="Answer",
                name="answer",
                id=self.artifact_id("answer"),
            )
        )
        return out
