"""Rendering: format-neutral fragments and the master-binder seam."""

from __future__ import annotations

from puzzcombinator.rendering.binder import render_binder
from puzzcombinator.rendering.fragment import Audience, RenderFragment

__all__ = [
    "Audience",
    "RenderFragment",
    "render_binder",
]
