"""The format-neutral rendering primitive and the artifact abstraction.

A :class:`RenderFragment` is a self-contained snippet of markup — usually HTML,
but inline SVG when precise geometry is needed (SVG embeds directly in the HTML
binder and prints sharply).

An :class:`Artifact` is the universal **thing that renders** carried on a graph
edge: a registry-backed, serializable renderable (a clue, a cipher, a grid, a pair
of coordinates). It owns its type-specific data and turns it into a
:class:`RenderFragment` on demand. Puzzles (in the ``puzzles`` layer) are
authoring-time *generators* of artifacts; the graph only ever holds artifacts.

This module is dependency-free (stdlib only) so every other layer can import it
without an import cycle — concrete artifact types live in the ``puzzles`` layer.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Literal


@dataclass(frozen=True)
class RenderFragment:
    """A self-contained snippet of markup, its kind, and any CSS it needs.

    ``styles`` is optional CSS the fragment depends on (keyed by its own class
    names). A consumer such as the binder aggregates the ``styles`` of every
    fragment it embeds into one ``<head>`` — so an artifact carries its own
    styling and the binder never needs artifact-specific CSS.
    """

    markup: str
    kind: Literal["html", "svg"] = "html"
    styles: str = ""

    @classmethod
    def html(cls, markup: str, *, styles: str = "") -> RenderFragment:
        return cls(markup=markup, kind="html", styles=styles)

    @classmethod
    def svg(cls, markup: str, *, styles: str = "") -> RenderFragment:
        """An inline ``<svg>...</svg>`` fragment; embeds directly inside HTML."""
        return cls(markup=markup, kind="svg", styles=styles)


class Artifact(ABC):
    """A serializable renderable: the thing handed to a player or representing a
    solution.

    An artifact is a *pure renderer of its own payload*: :meth:`render` reads the
    type-specific data and returns a :class:`RenderFragment`, with no branching on
    who's asking. Whether a piece goes to the player or only into the answer key is a
    *placement* decision made by a higher layer, not a property of the thing that
    renders.

    Two envelope fields sit beside the type-specific ``payload``:

    - :attr:`name` — a generic label/key for the artifact (a composite addresses
      its children by it; a generator names the pieces it emits).
    - :attr:`id` — unique within a hunt; names the output file for an artifact.
      Auto-generated as ``{type_name}-{uuid}`` when not supplied.
    """

    #: Stable registry key, e.g. ``"text"`` / ``"caesar_cipher"``.
    type_name: ClassVar[str]

    def __init__(
        self,
        *,
        name: str = "artifact",
        id: str | None = None,
    ) -> None:
        self.name = name
        self.id = id if id is not None else f"{type(self).type_name}-{uuid.uuid4().hex}"

    @abstractmethod
    def to_payload(self) -> dict[str, Any]:
        """Return this artifact's JSON-safe, type-specific fields."""

    @classmethod
    @abstractmethod
    def from_payload(cls, *, name: str, id: str, payload: dict[str, Any]) -> Artifact:
        """Rebuild an artifact from its envelope + :meth:`to_payload` output."""

    @abstractmethod
    def render(self) -> RenderFragment:
        """Produce this artifact's printable fragment (a pure function of its data)."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Artifact) or type(self) is not type(other):
            return NotImplemented
        return (self.id, self.name, self.to_payload()) == (
            other.id,
            other.name,
            other.to_payload(),
        )

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.id, self.name))
