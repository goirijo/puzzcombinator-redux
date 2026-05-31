"""The format-neutral rendering primitive.

A :class:`RenderFragment` is a self-contained snippet of markup a puzzle emits on
demand — usually HTML, but inline SVG for puzzles needing precise geometry (SVG
embeds directly in the HTML binder and prints sharply). This module is
dependency-free so ``puzzles`` can import it without creating an import cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Audience(Enum):
    """Who a rendered fragment is intended for."""

    PLAYER = "PLAYER"
    GAME_MASTER = "GAME_MASTER"


@dataclass(frozen=True)
class RenderFragment:
    """A self-contained snippet of markup, its kind, and any CSS it needs.

    ``styles`` is optional CSS the fragment depends on (keyed by its own class
    names). A consumer such as the binder aggregates the ``styles`` of every
    fragment it embeds into one ``<head>`` — so a puzzle carries its own styling
    and the binder never needs puzzle-specific CSS.
    """

    markup: str
    kind: Literal["html", "svg"] = "html"
    styles: str = ""

    @classmethod
    def html(cls, markup: str, *, styles: str = "") -> RenderFragment:
        return cls(markup=markup, kind="html", styles=styles)

    @classmethod
    def svg(cls, markup: str, *, styles: str = "") -> RenderFragment:
        """An inline ``<svg>...</svg>`` fragment; embeds directly inside HTML."""
        return cls(markup=markup, kind="svg", styles=styles)


@dataclass(frozen=True)
class Artifact:
    """One printable piece of a node's player-facing material.

    ``slug`` is a short filename-safe name (e.g. ``"grid"``); ``fragment`` is the
    markup. Most puzzles yield a single HTML artifact; some (e.g. the R4 decoder)
    yield several standalone SVG pieces that print on separate sheets.
    """

    slug: str
    fragment: RenderFragment
