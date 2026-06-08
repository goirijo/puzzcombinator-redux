"""The puzzle abstraction — an authoring-time *generator* of artifacts.

A :class:`Puzzle` is a design-time helper the designer specializes to *represent*
a puzzle: it owns the puzzle's data and emits **all** the :class:`Artifact`\\ s that
make it up — the pieces players receive *and* the answer key — as one flat
``{name: Artifact}`` map. The designer then places those artifacts on edges,
together or scattered across the graph. A puzzle makes no routing decision: whether
a given piece is handed to a player or only kept for the answer key is a
**placement** decision a higher layer makes, not something the generator bakes in
(so the same answer artifact can be routed however the designer wants).

A puzzle is **not** stored in the graph and is **not** serialized — only its
emitted artifacts are (each round-trips through the artifact registry). It knows
nothing about :class:`~puzzcombinator.core.graph.Node`, keeping the graph layer
artifact-agnostic.

A puzzle has **no notion of being "solved" and does no answer-checking**: in a
physically-played hunt the player uses one piece's output as the next step's
input. Whether a step is cleared is a *playthrough* fact for a future tracking
layer, not for this template.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import ClassVar

from puzzcombinator.errors import PuzzleError
from puzzcombinator.rendering.fragment import Artifact


class Puzzle(ABC):
    """Base class for all puzzle generators."""

    #: A readable prefix for the ids of the artifacts this puzzle emits.
    type_name: ClassVar[str]

    def __init__(self, id: str | None = None) -> None:
        #: Prefix for emitted artifact ids (``{id}-{name}``). Auto-generated when
        #: not supplied; pass an explicit id only for stable, readable player
        #: filenames. Nothing ever looks a puzzle up by it.
        self.id = id if id is not None else f"{type(self).type_name}-{uuid.uuid4().hex}"

    def artifact_id(self, name: str) -> str:
        """The id (and player filename stem) for the artifact called ``name``."""
        return f"{self.id}-{name}"

    @abstractmethod
    def _artifacts(self) -> list[Artifact]:
        """Build all of this puzzle's artifacts (each with name/id set)."""

    def artifacts(self, name: str | None = None) -> dict[str, Artifact] | Artifact:
        """This puzzle's artifacts, keyed by name.

        With no ``name`` returns the whole ``{name: Artifact}`` map; pass a
        ``name`` to get a single artifact — the idiom for scattering one puzzle's
        pieces across different edges.
        """
        mapping = {a.name: a for a in self._artifacts()}
        if name is None:
            return mapping
        try:
            return mapping[name]
        except KeyError:
            raise PuzzleError(f"no artifact named {name!r}; have {sorted(mapping)}") from None
