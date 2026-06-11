"""An image artifact: a single picture carried inline as a data URI.

The pressure-test for raster media. A clue that *is* a picture (a photo, a rebus,
a scrambled image) needs its bytes somewhere, but the serialized hunt is JSON and
is meant to stay self-contained — copy the JSON and you have copied the whole hunt.
So the bytes ride **inside** the artifact payload as a ``data:`` URI (the base64 of
the image with its MIME type): ``render`` stays pure (it only emits a longer
string), the output bundle stays text-only, and the artifact round-trips byte-exact
because the bytes are part of the value being compared.

An image is a *single thing* — just the picture (plus ``alt`` text describing it).
Any caption, prompt, or answer note is its own artifact; place an image and a
``TextArtifact`` together in a :class:`~puzzcombinator.artifacts.composite.CompositeArtifact`
when you want both. The designer authors an image directly, usually from a file
(:meth:`from_file`) or raw bytes (:meth:`from_bytes`).
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from puzzcombinator.artifacts.registry import register_artifact
from puzzcombinator.errors import PuzzleError
from puzzcombinator.rendering import presets
from puzzcombinator.rendering.fragment import Artifact, RenderFragment


def _data_uri(data: bytes, mime: str) -> str:
    """Encode raw bytes as a ``data:<mime>;base64,<...>`` URI."""
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _decode_data_uri(data_uri: str) -> tuple[str, bytes]:
    """Split ``data:{mime};base64,{blob}`` into ``(mime, raw_bytes)``.

    :meth:`ImageArtifact.from_bytes` always emits base64, but a hand-built data URI may
    not — fall back to treating the payload as UTF-8 text in that case.
    """
    header, _, payload = data_uri.partition(",")
    mime = header.removeprefix("data:").split(";", 1)[0] or "application/octet-stream"
    data = base64.b64decode(payload) if ";base64" in header else payload.encode("utf-8")
    return mime, data


def _extension_for(mime: str) -> str:
    """A file extension for ``mime`` — common image types pinned, else ``mimetypes``.

    ``mimetypes.guess_extension`` is platform-dependent (e.g. it can return ``.jpe`` for
    JPEG), so the common image types are pinned for stable, expected filenames.
    """
    pinned = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    return pinned.get(mime) or mimetypes.guess_extension(mime) or ".bin"


@register_artifact
class ImageArtifact(Artifact):
    """A single picture embedded inline as a data URI."""

    type_name = "image"

    def __init__(
        self,
        data_uri: str,
        *,
        alt: str = "",
        name: str = "image",
        id: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id)
        self.data_uri = data_uri
        #: Accessibility / fallback text for the ``<img>``.
        self.alt = alt
        if not self.data_uri.startswith("data:"):
            raise PuzzleError(f"image data_uri must be a data: URI, got {self.data_uri[:16]!r}")

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        *,
        mime: str,
        alt: str = "",
        name: str = "image",
        id: str | None = None,
    ) -> ImageArtifact:
        """Author an image artifact from raw image bytes plus its MIME type."""
        return cls(_data_uri(data, mime), alt=alt, name=name, id=id)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        alt: str = "",
        name: str = "image",
        id: str | None = None,
    ) -> ImageArtifact:
        """Author an image artifact by reading a file (MIME guessed from suffix).

        Authoring-time convenience — this is the one spot that touches the
        filesystem, and only when the designer explicitly asks it to. The
        resulting artifact is fully self-contained: the bytes live in the payload.
        """
        p = Path(path)
        mime, _ = mimetypes.guess_type(p.name)
        if mime is None:
            raise PuzzleError(f"could not guess MIME type for {p.name!r}; use from_bytes")
        return cls.from_bytes(p.read_bytes(), mime=mime, alt=alt, name=name, id=id)

    def to_payload(self) -> dict[str, Any]:
        return {"data_uri": self.data_uri, "alt": self.alt}

    @classmethod
    def from_payload(cls, *, name: str, id: str, payload: dict[str, Any]) -> ImageArtifact:
        return cls(
            payload["data_uri"],
            alt=payload.get("alt", ""),
            name=name,
            id=id,
        )

    def render(self) -> RenderFragment:
        return presets.image(self.data_uri, alt=self.alt, id=self.id)

    def native(self) -> tuple[str, bytes]:
        """Decode the data URI back to ``(extension, raw_bytes)`` — the original picture.

        Reads :attr:`data_uri` (the payload), reversing the base64 that :meth:`from_bytes`
        applied, with the extension derived from the embedded MIME type. The ``<img>`` that
        :meth:`render` builds is never consulted.
        """
        mime, data = _decode_data_uri(self.data_uri)
        return (_extension_for(mime), data)
