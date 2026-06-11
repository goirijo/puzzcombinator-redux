"""Write a single artifact (or a whole bag) to a file — the inspection/output helpers.

The *binder* (:mod:`puzzcombinator.rendering.binder`) turns a whole hunt graph into a
bundle; these turn **one artifact** into **one file** — for eyeballing a piece while you
build it, or exporting it on its own. Two complementary views:

- :func:`write_html` renders *any* artifact via
  :meth:`~puzzcombinator.rendering.fragment.Artifact.render` and wraps it in a standalone
  HTML page — *"how does this look?"*
- :func:`write_artifact` writes a piece in its **native** format — a raw ``.svg``, decoded
  image bytes, a plain ``.txt`` — by asking the artifact itself via
  :meth:`~puzzcombinator.rendering.fragment.Artifact.native`, and falls back to
  :func:`write_html` for anything with no native form (a composite) — *"give me the thing
  itself."* There is **no per-type ``isinstance`` ladder**: each artifact declares its own
  native ``(extension, bytes)``, so a new artifact type is exported correctly with zero
  edits here.

:func:`write_artifacts` is the whole-bag sibling — :func:`write_artifact` over every piece
in a ``{name: Artifact}`` map (e.g. all of ``puzzle.artifacts()``) or a plain iterable of
artifacts (e.g. an edge's ``content`` tuple).

All four need only the :class:`~puzzcombinator.rendering.fragment.Artifact` ABC — the
type-specific knowledge lives in each artifact's ``render`` / ``native`` — so they live
here in ``rendering`` with no dependency on concrete artifact types.
"""

from __future__ import annotations

import html
from collections.abc import Iterable, Mapping
from pathlib import Path

from puzzcombinator.rendering.fragment import Artifact


# TODO: Is this really a function we want to be public?
def html_document(title: str, body: str, styles: str = "") -> str:
    """Wrap body markup + CSS in a minimal standalone HTML document (pure, no I/O).

    ``body`` is inserted verbatim (it is already-rendered markup); ``title`` is escaped.
    Inline SVG bodies are valid here and render directly.
    """
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><style>{styles}</style></head>"
        f"<body>{body}</body></html>"
    )


def write_html(artifact: Artifact, out_dir: str | Path) -> Path:
    """Render any artifact and write it as a standalone ``{id}.html``; return the path.

    Works for every artifact because it goes through the universal ``render`` contract
    (a composite, an inline ``<svg>``, a text card all embed in the HTML body). The
    fragment's own ``styles`` ride along in the document ``<head>``.
    """
    fragment = artifact.render()
    path = Path(out_dir) / f"{artifact.id}.html"
    _ = path.write_text(
        html_document(artifact.id, fragment.markup, fragment.styles), encoding="utf-8"
    )
    return path


def write_artifact(artifact: Artifact, out_dir: str | Path) -> Path:
    """Write an artifact in its most natural format to ``{id}.{ext}``; return the path.

    Asks the artifact for its native form via
    :meth:`~puzzcombinator.rendering.fragment.Artifact.native`: a piece that has one
    (``SvgArtifact`` -> raw ``.svg``, ``ImageArtifact`` -> decoded bytes, ``TextArtifact``
    -> ``.txt``) is written byte-for-byte; a piece that returns ``None`` (a composite, or
    any type with no single native file) falls back to an HTML render via
    :func:`write_html`. The dispatch lives entirely in the artifacts, so a new artifact
    type needs no change here. The file is named by ``artifact.id`` — unique within a hunt,
    and legible when the artifact was named. Creates ``out_dir`` if it does not exist.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    native = artifact.native()
    if native is None:
        return write_html(artifact, out)
    ext, data = native
    path = out / f"{artifact.id}{ext}"
    _ = path.write_bytes(data)
    return path


def write_artifacts(
    artifacts: Mapping[str, Artifact] | Iterable[Artifact], out_dir: str | Path
) -> list[Path]:
    """Write every artifact to its own native file in ``out_dir``; return paths.

    :func:`write_artifact` applied across a collection — either a ``{name: Artifact}`` map
    (typically ``puzzle.artifacts()``) or a plain iterable of artifacts (e.g. an edge's
    ``content`` tuple). The inspection helper a puzzle demo uses to dump every piece at
    once. When given a map, only its values are written — the keys (which are just the
    artifacts' own names) are unused, so filenames always come from each artifact's ``id``
    and two like-named pieces from different puzzle instances never collide.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    items = artifacts.values() if isinstance(artifacts, Mapping) else artifacts
    return [write_artifact(artifact, out) for artifact in items]
