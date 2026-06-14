"""puzzcombinator — a modular library for *authoring* treasure-hunt games.

The library is a design-time tool: it helps a designer create puzzles, compose the
artifacts they emit into a hunt graph, and produce printable materials. It does not
play or grade a hunt — correctness is verified implicitly when a player uses one
artifact's output as the next step's input (or, physically, the key fits the lock).
Live progress tracking is a separate, future layer.

Importing this package also imports the built-in artifact types so they
self-register in the artifact-type registry (needed for deserialization).
"""

from __future__ import annotations

__version__ = "0.0.1"

from puzzcombinator.artifacts.image import ImageArtifact
from puzzcombinator.artifacts.registry import build_artifact, register_artifact
from puzzcombinator.artifacts.text import TextArtifact
from puzzcombinator.core.builder import GraphBuilder
from puzzcombinator.core.document import HuntDocument
from puzzcombinator.core.graph import Edge, Graph, Node
from puzzcombinator.core.ordering import (
    produced_outputs,
    required_inputs,
    topological_order,
)
from puzzcombinator.errors import (
    GraphError,
    PuzzcombinatorError,
    RegistryError,
    SerializationError,
)
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.cipher import CaesarCipherPuzzle, CipherArtifact
from puzzcombinator.puzzles.crossword import CrosswordArtifact, CrosswordPuzzle
from puzzcombinator.puzzles.r4 import R4DecoderPuzzle, R4PieceArtifact
from puzzcombinator.puzzles.riddle import RiddleLineArtifact, RiddlePuzzle
from puzzcombinator.rendering.binder import Binder, Chapter, Section
from puzzcombinator.rendering.export import write_artifact, write_artifacts, write_html
from puzzcombinator.rendering.fragment import Artifact, RenderFragment

__all__ = [
    "Artifact",
    "Binder",
    "CaesarCipherPuzzle",
    "Chapter",
    "CipherArtifact",
    "CrosswordArtifact",
    "CrosswordPuzzle",
    "Edge",
    "Graph",
    "GraphBuilder",
    "GraphError",
    "HuntDocument",
    "ImageArtifact",
    "Node",
    "Puzzle",
    "PuzzcombinatorError",
    "R4DecoderPuzzle",
    "R4PieceArtifact",
    "RegistryError",
    "RenderFragment",
    "RiddleLineArtifact",
    "RiddlePuzzle",
    "Section",
    "SerializationError",
    "TextArtifact",
    "__version__",
    "build_artifact",
    "produced_outputs",
    "register_artifact",
    "required_inputs",
    "topological_order",
    "write_artifact",
    "write_artifacts",
    "write_html",
]
