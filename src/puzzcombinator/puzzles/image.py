"""An image-backed puzzle: a picture clue carried inline as a data URI.

The pressure-test for raster media. A puzzle that *is* a picture (a photo clue, a
rebus, a scrambled image) needs its bytes somewhere, but the serialized hunt is
JSON and is meant to stay self-contained — copy the JSON and you have copied the
whole hunt. So the bytes ride **inside** the payload as a ``data:`` URI (the
base64 of the image with its MIME type), exactly the way the R4 puzzle embeds
inline SVG: ``render`` stays pure (it only emits a longer string), the output
bundle stays text-only, and ``from_payload(to_payload())`` round-trips byte-exact
because the bytes are part of the value being compared.

The designer authors from raw bytes (or a file) via :meth:`from_bytes` /
:meth:`from_file`; the player view shows the image and a prompt; the game-master
view adds the authored answer note (an answer *key*, never answer-checking).
"""

from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path
from typing import Any

from puzzcombinator.errors import PuzzleError
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.registry import register_puzzle
from puzzcombinator.rendering import presets
from puzzcombinator.rendering.fragment import Audience, RenderFragment


def _data_uri(data: bytes, mime: str) -> str:
    """Encode raw bytes as a ``data:<mime>;base64,<...>`` URI."""
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


@register_puzzle
class ImagePuzzle(Puzzle):
    """A picture clue with the image embedded inline as a data URI."""

    type_name = "image"

    def __init__(
        self,
        id: str,
        *,
        data_uri: str,
        prompt: str = "",
        answer: str | None = None,
        alt: str = "",
    ) -> None:
        super().__init__(id)
        self.data_uri = data_uri
        #: Player-facing instruction shown beside the image.
        self.prompt = prompt
        #: Game-master answer-key note (not shown to players; never graded).
        self.answer = answer
        #: Accessibility / fallback text for the ``<img>``.
        self.alt = alt
        self._validate()

    @classmethod
    def from_bytes(
        cls,
        id: str,
        data: bytes,
        *,
        mime: str,
        prompt: str = "",
        answer: str | None = None,
        alt: str = "",
    ) -> ImagePuzzle:
        """Author a puzzle from raw image bytes plus its MIME type."""
        return cls(id, data_uri=_data_uri(data, mime), prompt=prompt, answer=answer, alt=alt)

    @classmethod
    def from_file(
        cls,
        id: str,
        path: str | Path,
        *,
        prompt: str = "",
        answer: str | None = None,
        alt: str = "",
    ) -> ImagePuzzle:
        """Author a puzzle by reading an image file (MIME guessed from suffix).

        Authoring-time convenience — this is the one spot that touches the
        filesystem, and only when the designer explicitly asks it to. The
        resulting puzzle is fully self-contained: the bytes live in the payload.
        """
        p = Path(path)
        mime, _ = mimetypes.guess_type(p.name)
        if mime is None:
            raise PuzzleError(f"could not guess MIME type for {p.name!r}; use from_bytes")
        return cls.from_bytes(id, p.read_bytes(), mime=mime, prompt=prompt, answer=answer, alt=alt)

    def _validate(self) -> None:
        if not self.data_uri.startswith("data:"):
            raise PuzzleError(f"image data_uri must be a data: URI, got {self.data_uri[:16]!r}")

    # -- serialization -----------------------------------------------------

    def to_payload(self) -> dict[str, Any]:
        return {
            "data_uri": self.data_uri,
            "prompt": self.prompt,
            "answer": self.answer,
            "alt": self.alt,
        }

    @classmethod
    def from_payload(cls, id: str, payload: dict[str, Any]) -> ImagePuzzle:
        return cls(
            id,
            data_uri=payload["data_uri"],
            prompt=payload.get("prompt", ""),
            answer=payload.get("answer"),
            alt=payload.get("alt", ""),
        )

    # -- rendering ---------------------------------------------------------

    def render(self, audience: Audience) -> RenderFragment:
        figcaption = f"<figcaption>{html.escape(self.prompt)}</figcaption>" if self.prompt else ""
        body = (
            f'<figure><img src="{html.escape(self.data_uri)}" '
            f'alt="{html.escape(self.alt)}"/>{figcaption}</figure>'
        )
        if audience is Audience.GAME_MASTER and self.answer is not None:
            body += f'<p class="answer">Answer: {html.escape(self.answer)}</p>'
        return presets.card(body, title="Image", id=self.id)
