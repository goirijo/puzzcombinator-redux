"""A plain-text artifact — the simplest renderable, and the default edge content.

A clue, a word, an instruction: anything that is just a string. It carries no
puzzle and reads the same for everyone, so the designer constructs it directly
(``TextArtifact("Search the LIBRARY")``) rather than via a puzzle generator. It is
the template for the other "orphan" artifacts in this package (the image, and
future coordinates / QR codes / URIs) — each is a ``@register_artifact`` class with
three small methods and no puzzle behind it.
"""

from __future__ import annotations

from typing import Any

from puzzcombinator.artifacts.registry import register_artifact
from puzzcombinator.rendering import presets
from puzzcombinator.rendering.fragment import Artifact, RenderFragment


@register_artifact
class TextArtifact(Artifact):
    """A fragment for a plain string — escaped and wrapped for printing."""

    type_name = "text"

    def __init__(
        self,
        text: str,
        *,
        title: str | None = None,
        monospace: bool = False,
        name: str = "text",
        id: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id)
        self.text = text
        self.title = title
        self.monospace = monospace

    def to_payload(self) -> dict[str, Any]:
        return {"text": self.text, "title": self.title, "monospace": self.monospace}

    @classmethod
    def from_payload(cls, *, name: str, id: str, payload: dict[str, Any]) -> TextArtifact:
        return cls(
            payload["text"],
            title=payload.get("title"),
            monospace=payload.get("monospace", False),
            name=name,
            id=id,
        )

    def render(self) -> RenderFragment:
        return presets.text(self.text, title=self.title, id=self.id, monospace=self.monospace)

    def native(self) -> tuple[str, bytes]:
        """The raw string itself — ``title``/``monospace`` are render-only hints, dropped.

        Reads :attr:`text` directly (the same payload :meth:`render` starts from), so the
        ``.txt`` is the bare source, never the un-escaped/un-wrapped HTML.
        """
        return (".txt", self.text.encode("utf-8"))
