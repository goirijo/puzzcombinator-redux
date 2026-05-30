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
    """A snippet of HTML or inline-SVG markup, plus a tag for which it is."""

    markup: str
    kind: Literal["html", "svg"] = "html"

    @classmethod
    def html(cls, markup: str) -> RenderFragment:
        return cls(markup=markup, kind="html")

    @classmethod
    def svg(cls, markup: str) -> RenderFragment:
        """An inline ``<svg>...</svg>`` fragment; embeds directly inside HTML."""
        return cls(markup=markup, kind="svg")
