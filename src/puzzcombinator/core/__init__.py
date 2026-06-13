"""Puzzle-agnostic graph engine for treasure hunts."""

from __future__ import annotations

from puzzcombinator.core.builder import GraphBuilder
from puzzcombinator.core.document import HuntDocument
from puzzcombinator.core.graph import Edge, Graph, Node
from puzzcombinator.core.ordering import (
    produced_outputs,
    required_inputs,
    topological_order,
)

__all__ = [
    "Edge",
    "Graph",
    "GraphBuilder",
    "HuntDocument",
    "Node",
    "produced_outputs",
    "required_inputs",
    "topological_order",
]
