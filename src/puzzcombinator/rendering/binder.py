"""Render a hunt graph into game-master and player materials.

The output is a **bundle**: a game-master ``binder.html`` plus a ``players/``
folder of standalone printables. Everything here is a pure, **puzzle-agnostic**
consumer of the model — it walks nodes/edges, calls ``render`` /
``player_artifacts`` on whatever puzzles the edges carry, and aggregates the CSS
each fragment declares. Adding a new puzzle type needs no changes here. The only
function that touches the filesystem is :func:`write_bundle`.

Puzzles live on edges (as :class:`~puzzcombinator.core.graph.Content`), so a node
page shows the content on its incoming *and* outgoing edges. A visual hunt map is
intentionally deferred (it belongs with the future GUI).
"""

from __future__ import annotations

import html
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from puzzcombinator.core.graph import Content, Graph, Node
from puzzcombinator.core.ordering import chronological_order
from puzzcombinator.rendering.fragment import Artifact, Audience

# Generic binder layout only — never puzzle-specific. Puzzles carry their own CSS
# via RenderFragment.styles, which the document aggregates.
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

Direction = Literal["in", "out"]


def _esc(text: str) -> str:
    return html.escape(text)


def _document(title: str, body: str, extra_styles: Iterable[str] = ()) -> str:
    css = _CSS + "".join(sorted(set(extra_styles)))
    return _DOC.format(title=_esc(title), css=css, body=body)


def _artifact_path(puzzle_id: str, artifact: Artifact) -> str:
    ext = "svg" if artifact.fragment.kind == "svg" else "html"
    return f"players/{puzzle_id}-{artifact.slug}.{ext}"


def _edge_contents(graph: Graph, node: Node, direction: Direction) -> list[Content]:
    edges = graph.incoming(node.id) if direction == "in" else graph.outgoing(node.id)
    return [e.content for e in edges if e.content is not None]


# -- game-master binder ---------------------------------------------------


def _render_content(content: Content, audience: Audience) -> tuple[str, set[str]]:
    """Render one edge's content (text clue and/or puzzle) for the binder."""
    parts: list[str] = []
    styles: set[str] = set()
    if content.text:
        parts.append(f'<p class="clue">{_esc(content.text)}</p>')
    if content.puzzle is not None:
        fragment = content.puzzle.render(audience)
        parts.append(fragment.markup)
        if fragment.styles:
            styles.add(fragment.styles)
    return "".join(parts), styles


def _node_page(graph: Graph, node: Node) -> tuple[str, set[str]]:
    styles: set[str] = set()
    action = f' <span class="action">{_esc(node.action)}</span>' if node.action else ""
    parts = [f"<h2>{_esc(node.label or node.id)}{action}</h2>"]
    for direction, title in (("in", "Receives"), ("out", "Produces")):
        rendered: list[str] = []
        for content in _edge_contents(graph, node, direction):  # type: ignore[arg-type]
            markup, sub = _render_content(content, Audience.GAME_MASTER)
            rendered.append(markup)
            styles |= sub
        if rendered:
            parts.append(
                f'<section class="io {direction}"><h3>{title}</h3>{"".join(rendered)}</section>'
            )
    if node.notes:
        parts.append(f'<aside class="notes"><strong>Setup:</strong> {_esc(node.notes)}</aside>')
    page = f'<article class="page node" data-id="{_esc(node.id)}">{"".join(parts)}</article>'
    return page, styles


def _checklist(graph: Graph, order: list[Node]) -> str:
    items: list[str] = []
    for node in order:
        for edge in graph.outgoing(node.id):
            if edge.content is not None and edge.content.puzzle is not None:
                puzzle = edge.content.puzzle
                files = ", ".join(
                    f"<code>{_esc(_artifact_path(puzzle.id, art))}</code>"
                    for art in puzzle.player_artifacts()
                )
                items.append(f"<li>Print &amp; place {files}</li>")
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
    order = chronological_order(graph)
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

    One file per artifact of each puzzle carried on an edge: SVG artifacts are
    written as standalone ``.svg`` documents; HTML artifacts are wrapped in a
    minimal page that carries the fragment's own styles.
    """
    pages: dict[str, str] = {}
    for edge in graph.edges.values():
        content = edge.content
        if content is None or content.puzzle is None:
            continue
        puzzle = content.puzzle
        for artifact in puzzle.player_artifacts():
            path = _artifact_path(puzzle.id, artifact)
            fragment = artifact.fragment
            if fragment.kind == "svg":
                pages[path] = fragment.markup
            else:
                extra = {fragment.styles} if fragment.styles else set()
                pages[path] = _document(puzzle.id, fragment.markup, extra)
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
