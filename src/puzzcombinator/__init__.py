"""puzzcombinator — a modular library for *authoring* treasure-hunt games.

The library is a design-time tool: it helps a designer create puzzles, compose
them into a hunt graph, and produce printable artifacts. It does not play or
grade a hunt — correctness is verified implicitly when a player uses one
puzzle's output as the next puzzle's input (or, physically, the key fits the
lock). Live progress tracking is a separate, future layer.

Importing this package also imports the built-in puzzles so they self-register
in the puzzle-type registry (needed for deserialization).
"""

from __future__ import annotations

__version__ = "0.0.1"

from puzzcombinator.core.builder import GraphBuilder
from puzzcombinator.core.graph import Content, Edge, Graph, Node
from puzzcombinator.core.ordering import (
    chronological_order,
    produced_outputs,
    required_inputs,
)
from puzzcombinator.errors import (
    GraphError,
    PuzzcombinatorError,
    RegistryError,
    SerializationError,
)
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.cipher import CaesarCipherPuzzle
from puzzcombinator.puzzles.crossword import CrosswordPuzzle
from puzzcombinator.puzzles.image import ImagePuzzle
from puzzcombinator.puzzles.r4 import R4DecoderPuzzle
from puzzcombinator.puzzles.registry import build_puzzle, register_puzzle
from puzzcombinator.rendering.binder import (
    game_master_binder,
    hunt_bundle,
    player_pages,
    write_bundle,
)
from puzzcombinator.rendering.fragment import Artifact, Audience, RenderFragment

__all__ = [
    "Artifact",
    "Audience",
    "CaesarCipherPuzzle",
    "Content",
    "CrosswordPuzzle",
    "Edge",
    "Graph",
    "GraphBuilder",
    "GraphError",
    "ImagePuzzle",
    "Node",
    "Puzzle",
    "PuzzcombinatorError",
    "R4DecoderPuzzle",
    "RegistryError",
    "RenderFragment",
    "SerializationError",
    "__version__",
    "build_puzzle",
    "chronological_order",
    "game_master_binder",
    "hunt_bundle",
    "player_pages",
    "produced_outputs",
    "register_puzzle",
    "required_inputs",
    "write_bundle",
]
