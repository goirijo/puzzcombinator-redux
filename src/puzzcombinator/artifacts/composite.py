"""A composite artifact: several artifacts aggregated into one.

The primitives (:class:`~puzzcombinator.artifacts.text.TextArtifact`,
:class:`~puzzcombinator.artifacts.image.ImageArtifact`, …) are each a *single
thing*. When a clue is really several things together — a picture with a caption, a
riddle's lines, a grid beside its instructions — you compose them. A
:class:`CompositeArtifact` holds an ordered collection of child artifacts and is
itself an :class:`Artifact`, so composites nest freely and serialize and render like
any other piece.

It depends only on the registry's envelope helpers
(:func:`~puzzcombinator.artifacts.registry.artifact_to_dict` /
:func:`~puzzcombinator.artifacts.registry.artifact_from_dict`) to round-trip its
children, so any registered artifact type can be a child without this module knowing
about it.
"""

from __future__ import annotations

import html
from collections.abc import Iterable
from typing import Any

from puzzcombinator.artifacts.registry import (
    artifact_from_dict,
    artifact_to_dict,
    register_artifact,
)
from puzzcombinator.rendering.fragment import Artifact, RenderFragment, dedupe_css

#: Styling for the composite wrapper itself; children carry their own CSS.
COMPOSITE_CSS = """
  .pc-composite { display: flex; flex-direction: column; gap: 0.5rem; }
"""


@register_artifact
class CompositeArtifact(Artifact):
    """An ordered aggregate of child artifacts, rendered as one fragment."""

    type_name = "composite"

    def __init__(
        self,
        children: Iterable[Artifact],
        *,
        name: str = "composite",
        id: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id)
        self.children: tuple[Artifact, ...] = tuple(children)

    def to_payload(self) -> dict[str, Any]:
        return {"children": [artifact_to_dict(c) for c in self.children]}

    @classmethod
    def from_payload(cls, *, name: str, id: str, payload: dict[str, Any]) -> CompositeArtifact:
        return cls(
            [artifact_from_dict(d) for d in payload["children"]],
            name=name,
            id=id,
        )

    def render(self) -> RenderFragment:
        fragments = [child.render() for child in self.children]
        body = "".join(f.markup for f in fragments)
        styles = dedupe_css([COMPOSITE_CSS, *(f.styles for f in fragments)])
        return RenderFragment.html(
            f'<section class="pc-composite" data-id="{html.escape(self.id)}">{body}</section>',
            styles=styles,
        )
