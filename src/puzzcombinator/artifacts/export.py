"""Write a single artifact to a file — the native, per-primitive exporters.

Companion to :mod:`puzzcombinator.rendering.export`. That module holds the
artifact-agnostic helpers (:func:`~puzzcombinator.rendering.export.html_document` and
:func:`~puzzcombinator.rendering.export.write_html`, which render *any* artifact into
an HTML page). This module holds the other half: **native** exporters that bypass
``render`` and write each primitive's payload in its most natural file format — a raw
``.svg``, the decoded image bytes, a plain ``.txt``. They need concrete-type knowledge,
so they live here in the ``artifacts`` layer (which already depends on ``rendering``)
rather than down in ``rendering`` itself.

The agnostic pair is re-exported here so a caller has a single import site::

    from puzzcombinator.artifacts.export import write_html, write_svg, write_image, write_text

``write_html`` answers "how does this look?" (presentation); the native writers answer
"give me the thing itself." An :class:`~puzzcombinator.artifacts.svg.SvgArtifact`, for
instance, supports both — an HTML preview *and* a standalone ``.svg``.
"""

from __future__ import annotations

import base64
from pathlib import Path

from puzzcombinator.artifacts.image import ImageArtifact
from puzzcombinator.artifacts.svg import SvgArtifact
from puzzcombinator.artifacts.text import TextArtifact
from puzzcombinator.rendering.export import dump_artifacts, html_document, write_html

__all__ = [
    "dump_artifacts",
    "html_document",
    "write_html",
    "write_image",
    "write_svg",
    "write_text",
]


def write_text(artifact: TextArtifact, out_dir: str | Path) -> Path:
    """Write a :class:`TextArtifact`'s string to a plain ``{id}.txt``; return the path.

    The native form of text is the text itself — ``title`` and ``monospace`` are render
    hints for the HTML view and are intentionally dropped here.
    """
    path = Path(out_dir) / f"{artifact.id}.txt"
    path.write_text(artifact.text, encoding="utf-8")
    return path


def write_svg(artifact: SvgArtifact, out_dir: str | Path) -> Path:
    """Write a :class:`SvgArtifact`'s markup verbatim to a native ``{id}.svg``.

    The markup must carry ``xmlns="http://www.w3.org/2000/svg"`` to be a valid
    standalone file (inline-in-HTML does not require it); that is the markup author's
    responsibility — see :class:`SvgArtifact`.
    """
    path = Path(out_dir) / f"{artifact.id}.svg"
    path.write_text(artifact.markup, encoding="utf-8")
    return path


def write_image(artifact: ImageArtifact, out_dir: str | Path) -> Path:
    """Decode an :class:`ImageArtifact`'s data URI and write the raw bytes to a file.

    The extension is derived from the embedded MIME type (``image/png`` -> ``.png``),
    so the caller passes only a directory and gets back the written path.
    """
    mime, data = _decode_data_uri(artifact.data_uri)
    ext = _extension_for(mime)
    path = Path(out_dir) / f"{artifact.id}{ext}"
    path.write_bytes(data)
    return path


def _decode_data_uri(data_uri: str) -> tuple[str, bytes]:
    """Split ``data:{mime};base64,{blob}`` into ``(mime, raw_bytes)``.

    ImageArtifact always emits base64, but a hand-built data URI may not — fall back to
    treating the payload as percent-free UTF-8 text in that case.
    """
    header, _, payload = data_uri.partition(",")
    mime = header.removeprefix("data:").split(";", 1)[0] or "application/octet-stream"
    data = base64.b64decode(payload) if ";base64" in header else payload.encode("utf-8")
    return mime, data


def _extension_for(mime: str) -> str:
    """A file extension for ``mime`` — ``mimetypes`` first, then a small explicit map.

    ``mimetypes.guess_extension`` is platform-dependent (e.g. it can return ``.jpe`` for
    JPEG), so the common image types are pinned for stable, expected filenames.
    """
    import mimetypes

    pinned = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    return pinned.get(mime) or mimetypes.guess_extension(mime) or ".bin"
