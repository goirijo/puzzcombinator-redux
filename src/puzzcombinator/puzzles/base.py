"""The puzzle abstraction.

A :class:`Puzzle` is an **authoring-time template** the designer specializes to
*represent* a puzzle: it owns the puzzle's data, knows how to render its
printable artifact (for players) and its solution (for the game master), and
serializes itself. It deliberately knows nothing about
:class:`~puzzcombinator.core.graph.Node` — the graph holds a puzzle by
composition — which keeps the graph layer puzzle-agnostic.

A puzzle has **no notion of being "solved" and does no answer-checking**. In a
physically-played hunt nothing grades a submission: the player solves the puzzle
and uses its output as the input to the next step (or, physically, the key fits
the lock). Whether a step is cleared is a *playthrough* fact owned by a future
tracking layer, not by the puzzle template.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from puzzcombinator.rendering.fragment import Artifact, Audience, RenderFragment


class Puzzle(ABC):
    """Base class for all puzzle templates."""

    #: Stable registry key, e.g. ``"caesar_cipher"``.
    type_name: ClassVar[str]

    def __init__(self, id: str | None = None) -> None:
        #: Internal identity. Auto-generated as ``{type_name}-{uuid}`` when not
        #: supplied — it only needs to be unique within a hunt (it names the
        #: puzzle's output files); nothing ever looks a puzzle up by it. Pass an
        #: explicit id only when you want stable, readable printable filenames.
        self.id = id if id is not None else f"{type(self).type_name}-{uuid.uuid4().hex}"

    @abstractmethod
    def to_payload(self) -> dict[str, Any]:
        """Return this puzzle's JSON-safe, type-specific fields."""

    @classmethod
    @abstractmethod
    def from_payload(cls, id: str, payload: dict[str, Any]) -> Puzzle:
        """Rebuild a puzzle from :meth:`to_payload` output."""

    @abstractmethod
    def render(self, audience: Audience) -> RenderFragment:
        """Produce a printable fragment for the given audience."""

    def player_artifacts(self) -> list[Artifact]:
        """The player-facing printable piece(s) of this puzzle, each file-able.

        Default: a single HTML artifact wrapping the player render. Puzzles whose
        physical form is several separate sheets (e.g. the R4 decoder's grid and
        grille) override this to return one :class:`Artifact` per sheet.
        """
        return [Artifact("puzzle", self.render(Audience.PLAYER))]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Puzzle) or type(self) is not type(other):
            return NotImplemented
        return self.id == other.id and self.to_payload() == other.to_payload()

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.id))
