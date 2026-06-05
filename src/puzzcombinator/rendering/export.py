"""Write a single artifact to a standalone file — the inspection/output helpers.

Two layers of helper live in the codebase. The *binder* turns a whole hunt graph into
a bundle; these turn **one artifact** into **one file** — for eyeballing a piece while
you build it, or exporting it on its own.

This module holds the **artifact-agnostic** half: :func:`html_document` (the shared
minimal-HTML wrapper) and :func:`write_html` (render *any* artifact and wrap it). Both
need only the :class:`~puzzcombinator.rendering.fragment.Artifact` ABC and its
``render`` output, so they live here in ``rendering`` with no dependency on concrete
artifact types. The *native* per-primitive writers (a raw ``.svg``, decoded image
bytes, a plain ``.txt``) need concrete-type knowledge, so they live one layer up in
``puzzcombinator.artifacts.export`` — which re-exports these two for a single import
site.
"""

from __future__ import annotations

import html
from pathlib import Path

from puzzcombinator.rendering.fragment import Artifact


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
    path.write_text(html_document(artifact.id, fragment.markup, fragment.styles), encoding="utf-8")
    return path
