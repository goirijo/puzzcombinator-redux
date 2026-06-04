"""Ready-made :class:`RenderFragment` factories for the common cases.

Most puzzles render something simple — a word, a code, a pair of coordinates, an
image — and writing the wrapper markup and CSS by hand for each is tedious. These
helpers do it for you: hand them the raw value and you get back a styled fragment
that already carries its own CSS. The CSS is one shared constant, so every preset
fragment in a hunt aggregates to a *single* copy in the binder's ``<head>``.

This module is puzzle-agnostic and depends only on :mod:`fragment`, so puzzles can
import it freely. When a preset isn't enough, fall back to :func:`card` (your own
body markup, default styling) or to :class:`RenderFragment` directly (your own
markup *and* CSS) — the presets are a convenience, never a requirement.
"""

from __future__ import annotations

import html

from puzzcombinator.rendering.fragment import RenderFragment

#: Default styling shared by every preset fragment (deduplicated by the binder).
CARD_CSS = """
  .pc-card { margin: 0.5rem 0; }
  .pc-card h3 { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; }
  .pc-card .pc-body p { margin: 0.3rem 0; }
  .pc-card pre { font-size: 1.2rem; letter-spacing: 0.08em; background: #f4f4f4;
                 padding: 0.5rem; overflow-x: auto; }
  .pc-card img { max-width: 100%; height: auto; border: 1px solid #ccc; }
  .pc-card figcaption { font-style: italic; color: #555; }
  .pc-card .answer { font-weight: bold; }
"""


def card(body: str, *, title: str | None = None, id: str | None = None) -> RenderFragment:
    """Wrap ready-made ``body`` markup in the standard styled card.

    The escape hatch one level below the typed presets: use it when you have your
    own inner HTML but want the default look and CSS. ``body`` is inserted
    verbatim — escape any untrusted text yourself (the typed presets do this for
    you).
    """
    attrs = f' data-id="{html.escape(id)}"' if id is not None else ""
    head = f"<h3>{html.escape(title)}</h3>" if title is not None else ""
    return RenderFragment.html(
        f'<section class="puzzle pc-card"{attrs}>{head}<div class="pc-body">{body}</div></section>',
        styles=CARD_CSS,
    )


def text(
    value: str,
    *,
    title: str | None = None,
    id: str | None = None,
    monospace: bool = False,
) -> RenderFragment:
    """A fragment for a plain string — escaped and wrapped for you.

    Set ``monospace=True`` for codes, coordinates, or ASCII art (renders in a
    ``<pre>`` block, preserving spacing); otherwise the text is a paragraph.
    """
    escaped = html.escape(value)
    body = f"<pre>{escaped}</pre>" if monospace else f"<p>{escaped}</p>"
    return card(body, title=title, id=id)


def image(
    data_uri: str,
    *,
    alt: str = "",
    caption: str | None = None,
    title: str | None = None,
    id: str | None = None,
) -> RenderFragment:
    """A fragment for an inline image (a ``data:`` URI or any image URL).

    ``caption`` shows beneath the image; ``alt`` is the accessibility/fallback
    text. The bytes are not touched — pass a data URI to keep the hunt
    self-contained (see :class:`~puzzcombinator.artifacts.image.ImageArtifact`).
    """
    figcaption = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
    body = (
        f'<figure><img src="{html.escape(data_uri)}" alt="{html.escape(alt)}"/>'
        f"{figcaption}</figure>"
    )
    return card(body, title=title, id=id)
