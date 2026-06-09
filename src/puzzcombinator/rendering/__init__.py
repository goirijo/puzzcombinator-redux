"""Rendering: format-neutral fragments and the hunt-materials binder."""

from __future__ import annotations

from puzzcombinator.rendering.binder import (
    game_master_binder,
    hunt_bundle,
    player_pages,
    write_bundle,
)
from puzzcombinator.rendering.export import dump_artifacts, html_document, write_html
from puzzcombinator.rendering.fragment import Artifact, RenderFragment

__all__ = [
    "Artifact",
    "RenderFragment",
    "dump_artifacts",
    "game_master_binder",
    "html_document",
    "hunt_bundle",
    "player_pages",
    "write_bundle",
    "write_html",
]
