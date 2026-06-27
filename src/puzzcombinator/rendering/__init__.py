"""Rendering: format-neutral fragments and the composable binder."""

from __future__ import annotations

from puzzcombinator.rendering import presets
from puzzcombinator.rendering.binder import Binder, Chapter, Section
from puzzcombinator.rendering.export import (
    html_document,
    write_artifact,
    write_artifacts,
    write_html,
)
from puzzcombinator.rendering.fragment import Artifact, RenderFragment, dedupe_css

__all__ = [
    "Artifact",
    "Binder",
    "Chapter",
    "RenderFragment",
    "Section",
    "dedupe_css",
    "html_document",
    "presets",
    "write_artifact",
    "write_artifacts",
    "write_html",
]
