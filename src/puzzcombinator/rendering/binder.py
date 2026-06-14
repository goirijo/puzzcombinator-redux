"""Compose artifact and node renderings into printable binders.

A **binder** is not a fixed thing. It is simply *a collection of renderings that
logically belong together* — whatever the designer decides belongs together: every
``solution`` artifact, one page per node in solve order, the props for a single hunt
branch. This module gives the designer the composition machinery and stays out of the
business of deciding what a hunt's output "should" be (there is no player-vs-answer-key
routing here — that is a placement decision the designer already made on the graph).

Three nesting levels, each a renderable that aggregates the one below — mirroring
:class:`~puzzcombinator.artifacts.composite.CompositeArtifact`, which aggregates child
artifacts:

- :class:`Section` — **one** rendered item: a single artifact, or a single node (its
  label/action/notes plus the artifacts on its incoming and/or outgoing edges).
- :class:`Chapter` — a group of closely-related sections under an optional title. The
  unit of "keep these together": sections within a chapter share a page; chapters break.
- :class:`Binder` — a collection of chapters that renders to **one standalone HTML
  document**. The only level that produces a finished document; the layout knobs
  (``title`` and the two dividers) live here.

Everything is **pure** (no filesystem access — a binder renders to a string; write it
with ``Path.write_text``) and **artifact-agnostic** (each artifact carries its own CSS
via its :class:`~puzzcombinator.rendering.fragment.RenderFragment`; the binder only
aggregates and de-duplicates those styles, so a new artifact type needs zero edits here).
"""

from __future__ import annotations

import html
from collections.abc import Iterable
from dataclasses import dataclass

from puzzcombinator.core.graph import Graph
from puzzcombinator.core.ordering import produced_outputs, required_inputs
from puzzcombinator.rendering.export import html_document
from puzzcombinator.rendering.fragment import Artifact

#: Divider HTML placed *between* items. A page break (its CSS lives in ``_BINDER_CSS``)
#: separates chapters; a thin rule separates sections within a chapter. Pass either — or
#: any HTML string of your own — to a :class:`Binder`'s ``chapter_divider`` /
#: ``section_divider`` to change how the divisions look.
PAGE_BREAK = '<div class="binder-break"></div>'
RULE = '<hr class="binder-divider">'

#: Generic binder layout only — never artifact-specific. Artifacts carry their own CSS
#: via ``RenderFragment.styles``, which :meth:`Binder.render` aggregates alongside this.
_BINDER_CSS = """
  .binder-break { page-break-after: always; }
  .binder-divider { border: none; border-top: 1px solid #ddd; margin: 1.5rem 0; }
  .binder-chapter { margin-bottom: 1.5rem; }
  .binder-chapter > h2 { font-size: 1.1rem; border-bottom: 2px solid #333; padding-bottom: 0.2rem; }
  .binder-node > h3 { margin-bottom: 0.2rem; }
  .binder-action { font-size: 0.6em; color: #888; text-transform: uppercase;
                   vertical-align: middle; }
  .binder-notes { font-style: italic; color: #555; }
  .binder-io > h4 { font-size: 0.75rem; text-transform: uppercase;
                    letter-spacing: 0.05em; margin: 0.4rem 0 0.2rem; }
  .binder-io.binder-out { color: #060; }
"""


def _dedupe(blocks: Iterable[str]) -> str:
    """Join CSS blocks, keeping the first occurrence of each and preserving order.

    A local copy of the same helper used by ``CompositeArtifact`` — the binder lives in
    ``rendering`` and must not reach up into ``artifacts``.
    """
    seen: dict[str, None] = {}
    for block in blocks:
        if block and block not in seen:
            seen[block] = None
    return "".join(seen)


def _render_run(artifacts: Iterable[Artifact]) -> tuple[str, tuple[str, ...]]:
    """Render a run of artifacts to concatenated markup + the CSS blocks they declare."""
    markup: list[str] = []
    styles: list[str] = []
    for artifact in artifacts:
        fragment = artifact.render()
        markup.append(fragment.markup)
        if fragment.styles:
            styles.append(fragment.styles)
    return "".join(markup), tuple(styles)


@dataclass(frozen=True)
class Section:
    """One rendered item — a single artifact or a single node — and the CSS it needs.

    ``markup`` is already rendered (an artifact renders itself; there is nothing to tune
    at this level). ``styles`` is the ordered tuple of CSS blocks the item pulled in,
    de-duplicated against everything else only when the whole document is assembled.
    """

    markup: str
    styles: tuple[str, ...] = ()

    @classmethod
    def from_artifact(cls, artifact: Artifact) -> Section:
        """A section showing a single artifact's render."""
        fragment = artifact.render()
        markup = (
            f'<section class="binder-section" data-id="{html.escape(artifact.id)}">'
            f"{fragment.markup}</section>"
        )
        return cls(markup, (fragment.styles,) if fragment.styles else ())

    @classmethod
    def from_node(
        cls, graph: Graph, node_id: str, *, incoming: bool = True, outgoing: bool = True
    ) -> Section:
        """A section for one node: its header (label/action/notes) plus the artifacts on
        its incoming and/or outgoing edges.

        ``node_id`` is the node's id — the handle :meth:`GraphBuilder.node` hands back
        and :func:`topological_order` returns; the node is materialized internally via
        :meth:`Graph.node`. ``incoming``/``outgoing`` select which side(s) to include —
        e.g. ``outgoing=False`` for a sheet that shows only what each action hands the
        player.
        """
        node = graph.node(node_id)
        action = (
            f' <span class="binder-action">{html.escape(node.action)}</span>' if node.action else ""
        )
        parts = [f"<h3>{html.escape(node.label or node.id)}{action}</h3>"]
        if node.notes:
            parts.append(f'<p class="binder-notes">{html.escape(node.notes)}</p>')
        styles: list[str] = []
        for include, node_artifacts, css_class, title in (
            (incoming, required_inputs, "binder-in", "Receives"),
            (outgoing, produced_outputs, "binder-out", "Produces"),
        ):
            if not include:
                continue
            body, sub = _render_run(node_artifacts(graph, node.id))
            styles.extend(sub)
            if body:
                parts.append(f'<div class="binder-io {css_class}"><h4>{title}</h4>{body}</div>')
        markup = (
            f'<section class="binder-section binder-node" data-id="{html.escape(node.id)}">'
            f"{''.join(parts)}</section>"
        )
        return cls(markup, tuple(styles))


@dataclass(frozen=True)
class Chapter:
    """A group of closely-related sections, under an optional heading."""

    sections: tuple[Section, ...]
    title: str | None = None

    @classmethod
    def of_artifacts(cls, artifacts: Iterable[Artifact], *, title: str | None = None) -> Chapter:
        """A chapter with one section per artifact, in order."""
        return cls(tuple(Section.from_artifact(a) for a in artifacts), title)

    @classmethod
    def of_nodes(
        cls,
        graph: Graph,
        node_ids: Iterable[str],
        *,
        incoming: bool = True,
        outgoing: bool = True,
        title: str | None = None,
    ) -> Chapter:
        """A chapter with one section per node id, in the order given.

        ``node_ids`` are the handles you collected while building (or got from
        :func:`topological_order`); each is resolved via :meth:`Graph.node`.
        """
        return cls(
            tuple(
                Section.from_node(graph, nid, incoming=incoming, outgoing=outgoing)
                for nid in node_ids
            ),
            title,
        )

    def _body(self, section_divider: str) -> str:
        head = f"<h2>{html.escape(self.title)}</h2>" if self.title is not None else ""
        inner = section_divider.join(s.markup for s in self.sections)
        return f'<section class="binder-chapter">{head}{inner}</section>'

    def _style_blocks(self) -> tuple[str, ...]:
        return tuple(block for section in self.sections for block in section.styles)


@dataclass(frozen=True)
class Binder:
    """A collection of chapters; renders to one standalone HTML document.

    The layout knobs live here, set at construction and tweakable before rendering:
    ``title`` (the document title), ``chapter_divider`` (between chapters — a page break
    by default), and ``section_divider`` (between sections within a chapter — a thin rule
    by default). For the common ungrouped cases use :meth:`of_artifacts` /
    :meth:`of_nodes`, which wrap everything in a single chapter.
    """

    chapters: tuple[Chapter, ...]
    title: str = "Binder"
    section_divider: str = RULE
    chapter_divider: str = PAGE_BREAK

    @classmethod
    def of_artifacts(
        cls,
        artifacts: Iterable[Artifact],
        *,
        title: str = "Binder",
        section_divider: str = RULE,
        chapter_divider: str = PAGE_BREAK,
    ) -> Binder:
        """A binder of one chapter, one section per artifact — the "concatenate these
        renderings" case (e.g. every ``solution`` artifact in a hunt)."""
        return cls(
            (Chapter.of_artifacts(artifacts),),
            title=title,
            section_divider=section_divider,
            chapter_divider=chapter_divider,
        )

    @classmethod
    def of_nodes(
        cls,
        graph: Graph,
        node_ids: Iterable[str],
        *,
        incoming: bool = True,
        outgoing: bool = True,
        title: str = "Binder",
        section_divider: str = RULE,
        chapter_divider: str = PAGE_BREAK,
    ) -> Binder:
        """A binder of one chapter, one section per node id — the "page per node" case.

        Order the ids however you like; pass ``topological_order(graph)`` for solve
        order.
        """
        return cls(
            (Chapter.of_nodes(graph, node_ids, incoming=incoming, outgoing=outgoing),),
            title=title,
            section_divider=section_divider,
            chapter_divider=chapter_divider,
        )

    def render(self) -> str:
        """Assemble the whole document: chapters joined by ``chapter_divider``, every
        fragment's CSS aggregated and de-duplicated into the ``<head>``."""
        body = self.chapter_divider.join(c._body(self.section_divider) for c in self.chapters)
        styles = _dedupe([_BINDER_CSS, *(b for c in self.chapters for b in c._style_blocks())])
        return html_document(self.title, body, styles)
