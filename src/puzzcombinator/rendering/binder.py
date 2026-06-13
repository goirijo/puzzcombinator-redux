"""Render a hunt graph into game-master and player materials.

.. warning::

   **STALE — pre-refactor, does not run.** This module has NOT been migrated to the
   audience-free artifact model (Phase 1, 2026-06-04). It still reads
   ``artifact.audience``, a field the ``Artifact`` ABC no longer has, so it will
   raise on import/use. It is kept only as the migration *target* for the binder
   phase (see CLAUDE.md). **Do not treat anything here as a correct reference for the
   current artifact layer** — only ``artifacts/ARTIFACTS.md`` and ``tests/artifacts/``
   describe what runs today.

The output is a **bundle**: a game-master ``binder.html`` plus a ``players/``
folder of standalone printables. Everything here is a pure, **artifact-agnostic**
consumer of the model — it walks nodes/edges, calls ``render`` on whatever
artifacts the edges carry, and aggregates the CSS each fragment declares. Adding a
new artifact type needs no changes here. The only function that touches the
filesystem is :func:`write_bundle`.

Artifacts live on edges, so a node page shows the artifacts on its incoming *and*
outgoing edges. Player printables come from ``PLAYER``-audience artifacts (each its
own file); the game-master binder renders every artifact on a node's edges, so the
answer key shows both the player-facing pieces and the ``GAME_MASTER`` ones (the
revealed answers). A visual hunt map is intentionally deferred (it belongs with the
future GUI).
"""

from __future__ import annotations

import html
from collections.abc import Iterable
from pathlib import Path

from puzzcombinator.core.graph import Graph, Node
from puzzcombinator.core.ordering import topological_order
from puzzcombinator.rendering.fragment import Artifact

# Generic binder layout only — never artifact-specific. Artifacts carry their own
# CSS via RenderFragment.styles, which the document aggregates.
_CSS = """
  body { font-family: system-ui, sans-serif; margin: 2rem; }
  .page { page-break-after: always; margin-bottom: 2rem; }
  .action { font-size: 0.6em; color: #888; vertical-align: middle; text-transform: uppercase; }
  .io { margin: 0.5rem 0; }
  .io.out { color: #060; }
  .io h3 { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; margin: 0.3rem 0; }
  .notes { font-style: italic; color: #555; }
  .checklist ul.check { list-style: none; padding-left: 0; }
  .checklist ul.check li::before { content: "\\2610\\00a0\\00a0"; }
  .checklist code { background: #f4f4f4; padding: 0 0.25em; }
"""

_DOC = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>"""


def _esc(text: str) -> str:
    return html.escape(text)


def _document(title: str, body: str, extra_styles: Iterable[str] = ()) -> str:
    css = _CSS + "".join(sorted(set(extra_styles)))
    return _DOC.format(title=_esc(title), css=css, body=body)


def _artifact_path(artifact_id: str, kind: str) -> str:
    ext = "svg" if kind == "svg" else "html"
    return f"players/{artifact_id}.{ext}"


# -- game-master binder ---------------------------------------------------


def _render_artifacts(artifacts: Iterable[Artifact]) -> tuple[str, set[str]]:
    """Render a run of artifacts for the binder, collecting the CSS they declare."""
    parts: list[str] = []
    styles: set[str] = set()
    for artifact in artifacts:
        fragment = artifact.render()
        parts.append(fragment.markup)
        if fragment.styles:
            styles.add(fragment.styles)
    return "".join(parts), styles


def _node_page(graph: Graph, node: Node) -> tuple[str, set[str]]:
    styles: set[str] = set()
    action = f' <span class="action">{_esc(node.action)}</span>' if node.action else ""
    parts = [f"<h2>{_esc(node.label or node.id)}{action}</h2>"]
    for direction, title in (("in", "Receives"), ("out", "Produces")):
        edges = graph.incoming(node.id) if direction == "in" else graph.outgoing(node.id)
        markup, sub = _render_artifacts(a for e in edges for a in e.content)
        styles |= sub
        if markup:
            parts.append(f'<section class="io {direction}"><h3>{title}</h3>{markup}</section>')
    if node.notes:
        parts.append(f'<aside class="notes"><strong>Setup:</strong> {_esc(node.notes)}</aside>')
    page = f'<article class="page node" data-id="{_esc(node.id)}">{"".join(parts)}</article>'
    return page, styles


def _checklist(graph: Graph, order: list[Node]) -> str:
    items: list[str] = []
    for node in order:
        for edge in graph.outgoing(node.id):
            for artifact in edge.content:
                path = _artifact_path(artifact.id, artifact.render().kind)
                items.append(f"<li>Print &amp; place <code>{_esc(path)}</code></li>")
        if node.notes:
            label = _esc(node.label or node.id)
            items.append(f"<li><strong>{label}</strong>: {_esc(node.notes)}</li>")
    if not items:
        return ""
    return (
        '<section class="page checklist"><h2>Production checklist</h2>'
        '<ul class="check">' + "".join(items) + "</ul></section>"
    )


def game_master_binder(graph: Graph) -> str:
    """The game master's document: a page per node (solve order) + a checklist."""
    order = topological_order(graph)
    styles: set[str] = set()
    pages: list[str] = []
    for node in order:
        markup, sub = _node_page(graph, node)
        styles |= sub
        pages.append(markup)
    body = "\n".join(pages) + "\n" + _checklist(graph, order)
    return _document("Master Binder", body, styles)


# -- player printables ----------------------------------------------------


def player_pages(graph: Graph) -> dict[str, str]:
    """Standalone player printables, keyed by relative path (``players/...``).

    One file per ``PLAYER`` artifact carried on an edge: SVG artifacts are written
    as standalone ``.svg`` documents; HTML artifacts are wrapped in a minimal page
    that carries the fragment's own styles. ``GAME_MASTER`` artifacts render only
    in the binder and produce no file.
    """
    pages: dict[str, str] = {}
    for edge in graph.edges.values():
        for artifact in edge.content:
            fragment = artifact.render()
            path = _artifact_path(artifact.id, fragment.kind)
            if fragment.kind == "svg":
                pages[path] = fragment.markup
            else:
                extra = {fragment.styles} if fragment.styles else set()
                pages[path] = _document(artifact.id, fragment.markup, extra)
    return pages


# -- bundle ---------------------------------------------------------------


def hunt_bundle(graph: Graph) -> dict[str, str]:
    """The whole output as relative-path -> content (pure; no filesystem access)."""
    bundle = {"binder.html": game_master_binder(graph)}
    bundle.update(player_pages(graph))
    return bundle


def write_bundle(bundle: dict[str, str], out_dir: str | Path) -> list[Path]:
    """Write a :func:`hunt_bundle` to disk under ``out_dir``. The only IO here."""
    base = Path(out_dir)
    written: list[Path] = []
    for rel, content in bundle.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
