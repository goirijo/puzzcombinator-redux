"""Rendering: format-neutral fragments and the composable binder."""

from __future__ import annotations

from puzzcombinator.rendering.binder import Binder, Chapter, Section
from puzzcombinator.rendering.export import (
    html_document,
    write_artifact,
    write_artifacts,
    write_html,
)
from puzzcombinator.rendering.fragment import Artifact, RenderFragment

__all__ = [
    "Artifact",
    "Binder",
    "Chapter",
    "RenderFragment",
    "Section",
    "html_document",
    "write_artifact",
    "write_artifacts",
    "write_html",
]
