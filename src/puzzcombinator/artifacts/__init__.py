"""Standalone, *orphan* artifacts and the artifact-type registry.

An :class:`~puzzcombinator.rendering.fragment.Artifact` is the universal "thing
that renders" carried on a graph edge. Most concrete artifacts are emitted by a
:class:`~puzzcombinator.puzzles.base.Puzzle` generator and live beside it in the
``puzzles`` layer (a cipher's ciphertext, a crossword grid). The ones here are
different: they have **no puzzle behind them** — there is nothing to generate, so
the designer constructs them directly. ``TextArtifact`` (a clue, a word),
``ImageArtifact`` (a single picture, carried inline as a data URI), ``SvgArtifact``
(inline vector markup, rendered verbatim), and ``CompositeArtifact`` (several
artifacts aggregated into one) are the orphans today; coordinates / QR codes / URIs
would join them.

This package also owns the registry (``register_artifact`` / ``build_artifact`` and
the ``artifact_to_dict`` / ``artifact_from_dict`` envelope helpers) that every
artifact type — orphan or puzzle-bound — uses to round-trip through serialization.
It depends only on the ``rendering`` layer, so the ``puzzles`` layer can build on top
of it without an import cycle.
"""

from __future__ import annotations

from puzzcombinator.artifacts.composite import CompositeArtifact
from puzzcombinator.artifacts.image import ImageArtifact
from puzzcombinator.artifacts.registry import (
    artifact_from_dict,
    artifact_to_dict,
    build_artifact,
    register_artifact,
)
from puzzcombinator.artifacts.svg import SvgArtifact
from puzzcombinator.artifacts.text import TextArtifact

__all__ = [
    "CompositeArtifact",
    "ImageArtifact",
    "SvgArtifact",
    "TextArtifact",
    "artifact_from_dict",
    "artifact_to_dict",
    "build_artifact",
    "register_artifact",
]
