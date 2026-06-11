"""An SVG artifact: inline vector markup carried verbatim.

The counterpart to :class:`~puzzcombinator.artifacts.image.ImageArtifact`. An image
is an *opaque picture* — bytes wrapped in an ``<img>`` (``kind="html"``). This is the
other half: a piece whose value **is** a snippet of ``<svg>...</svg>`` markup, spliced
inline so it renders as live vector graphics (``kind="svg"``). That is what you want
for anything geometric and generated in code — a map, a diagram, a grid — where you
need vector precision, CSS-styleable shapes, crisp print at any scale, and a usable
standalone ``.svg`` file.

It is a deliberately **dumb carrier**: it holds finished SVG and renders it, exactly
as :class:`~puzzcombinator.artifacts.text.TextArtifact` holds a finished string. It
does **not** generate anything — that is the caller's job, whether the designer draws
the markup in code (then ``SvgArtifact(markup)``) or a
:class:`~puzzcombinator.puzzles.base.Puzzle` produces it (then a puzzle-bound artifact
beside that generator, like the R4 grid). Keeping generation out of the artifact is
what stops it from sprawling into a drawing engine.

A title or caption is *separate content*: it would force a wrapping element and flip
the fragment back to ``kind="html"``, so put a ``TextArtifact`` beside this in a
:class:`~puzzcombinator.artifacts.composite.CompositeArtifact` instead. Any CSS the
graphic needs lives **inside** the markup as a ``<style>`` element (valid within
``<svg>``), so the payload stays a single string and the artifact stays a pure value.

.. note::

   For the rendered markup to also work as a *standalone* ``.svg`` file it must carry
   ``xmlns="http://www.w3.org/2000/svg"``; inline-in-HTML does not require it, so
   generated markup often omits it. :meth:`render` stays pure and unaware of
   file-vs-inline, so supplying the namespace is the markup author's responsibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from puzzcombinator.artifacts.registry import register_artifact
from puzzcombinator.errors import PuzzleError
from puzzcombinator.rendering.fragment import Artifact, RenderFragment


@register_artifact
class SvgArtifact(Artifact):
    """A snippet of inline SVG markup, rendered verbatim as an ``svg``-kind fragment."""

    type_name = "svg"

    def __init__(
        self,
        markup: str,
        *,
        name: str = "svg",
        id: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id)
        self.markup = markup
        if "<svg" not in markup:
            raise PuzzleError(
                f"SvgArtifact markup must contain an <svg> element, got {markup[:16]!r}"
            )

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        name: str = "svg",
        id: str | None = None,
    ) -> SvgArtifact:
        """Author an SVG artifact by reading a ``.svg`` file's markup verbatim.

        Unlike :meth:`ImageArtifact.from_file`, which base64s the file into an
        ``<img>`` data URI, this keeps the markup *inline* so it renders as live
        vector graphics. Authoring-time convenience — the one spot that touches the
        filesystem, and only when the designer asks it to.
        """
        return cls(Path(path).read_text(encoding="utf-8"), name=name, id=id)

    def to_payload(self) -> dict[str, Any]:
        return {"markup": self.markup}

    @classmethod
    def from_payload(cls, *, name: str, id: str, payload: dict[str, Any]) -> SvgArtifact:
        return cls(payload["markup"], name=name, id=id)

    def render(self) -> RenderFragment:
        return RenderFragment.svg(self.markup)

    # No native() override: an svg-kind render is already a standalone .svg, so the
    # Artifact base serves the markup verbatim. (Validity still requires the markup to
    # carry xmlns="http://www.w3.org/2000/svg" — the author's responsibility, per the
    # class docstring.)
