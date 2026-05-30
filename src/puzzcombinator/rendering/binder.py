"""The master-binder seam.

The long-term vision is a printable master document compiling the whole hunt.
This milestone ships the *seam*, not the full compiler: :func:`render_binder`
walks the graph in solve-order and stitches each puzzle's fragment together with
its edge clues (and, for the game master, notes, the answer key, and revealed
outputs). Rich layout, a full player/game-master split, and asset handling are
deferred — but the contract is fixed, so the later compiler needs no model or
puzzle refactoring: it only ever calls :func:`chronological_order`,
``graph.incoming`` / ``graph.outgoing``, and ``puzzle.render``.
"""

from __future__ import annotations

import html

from puzzcombinator.core.graph import Graph, Node
from puzzcombinator.core.ordering import chronological_order
from puzzcombinator.rendering.fragment import Audience

_DOC_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  .page {{ page-break-after: always; margin-bottom: 2rem; }}
  .notes {{ font-style: italic; color: #555; }}
  .clue-out {{ color: #060; }}
  .ciphertext {{ font-size: 1.25rem; letter-spacing: 0.1em; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def _esc(text: str) -> str:
    return html.escape(text)


def _node_section(graph: Graph, node: Node, audience: Audience) -> str:
    parts: list[str] = []
    heading = node.label or node.id
    parts.append(f"<h2>{_esc(heading)}</h2>")

    for edge in graph.incoming(node.id):
        if edge.content is not None and edge.content.text:
            parts.append(f'<p class="clue-in">{_esc(edge.content.text)}</p>')

    if node.payload is not None:
        parts.append(node.payload.render(audience).markup)

    if audience is Audience.GAME_MASTER:
        if node.notes:
            parts.append(f'<aside class="notes">{_esc(node.notes)}</aside>')
        for edge in graph.outgoing(node.id):
            if edge.content is not None and edge.content.text:
                parts.append(f'<p class="clue-out">Reveals: {_esc(edge.content.text)}</p>')

    return f'<article class="page" data-id="{_esc(node.id)}">{"".join(parts)}</article>'


def render_binder(graph: Graph, *, audience: Audience = Audience.PLAYER) -> str:
    """Render the hunt to a single HTML document for the given audience.

    Milestone-1 skeleton: linear flow, one audience at a time. See module
    docstring for what the full compiler will add.
    """
    body = "\n".join(_node_section(graph, node, audience) for node in chronological_order(graph))
    title = "Master Binder" if audience is Audience.GAME_MASTER else "Treasure Hunt"
    return _DOC_SHELL.format(title=title, body=body)
