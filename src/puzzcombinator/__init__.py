"""puzzcombinator — a modular library for building treasure-hunt games.

Importing this package also imports the built-in validators and puzzles so they
self-register in their type registries (needed for deserialization).
"""

from __future__ import annotations

__version__ = "0.0.1"

from puzzcombinator.core.builder import GraphBuilder
from puzzcombinator.core.graph import Content, Edge, Graph, Node, NodeKind
from puzzcombinator.core.ordering import (
    chronological_order,
    required_inputs,
    unlocked_outputs,
)
from puzzcombinator.errors import (
    GraphError,
    PuzzcombinatorError,
    RegistryError,
    SerializationError,
)
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.cipher import CaesarCipherPuzzle
from puzzcombinator.puzzles.registry import build_puzzle, register_puzzle
from puzzcombinator.rendering.binder import render_binder
from puzzcombinator.rendering.fragment import Audience, RenderFragment
from puzzcombinator.validation.base import ValidationResult, Validator
from puzzcombinator.validation.builtins import (
    CustomFn,
    ExactMatch,
    Manual,
    NormalizedText,
    Regex,
)
from puzzcombinator.validation.registry import (
    build_validator,
    get_custom_fn,
    register_custom_fn,
    register_validator,
)

__all__ = [
    "Audience",
    "CaesarCipherPuzzle",
    "Content",
    "CustomFn",
    "Edge",
    "ExactMatch",
    "Graph",
    "GraphBuilder",
    "GraphError",
    "Manual",
    "Node",
    "NodeKind",
    "NormalizedText",
    "Puzzle",
    "PuzzcombinatorError",
    "Regex",
    "RegistryError",
    "RenderFragment",
    "SerializationError",
    "ValidationResult",
    "Validator",
    "__version__",
    "build_puzzle",
    "build_validator",
    "chronological_order",
    "get_custom_fn",
    "register_custom_fn",
    "register_puzzle",
    "register_validator",
    "render_binder",
    "required_inputs",
    "unlocked_outputs",
]
