"""Shared exception hierarchy.

This is a dependency-free leaf module so every layer (``core``, ``validation``,
``puzzles``, ``serialization``) can raise typed errors without creating an
import cycle between the layers themselves.
"""

from __future__ import annotations


class PuzzcombinatorError(Exception):
    """Base class for all errors raised by the library."""


class GraphError(PuzzcombinatorError):
    """Raised for structural problems in a hunt graph.

    Examples: dangling edges, duplicate ids, or a cycle.
    """


class RegistryError(PuzzcombinatorError):
    """Raised when a type name or custom-function name is not registered."""


class SerializationError(PuzzcombinatorError):
    """Raised when (de)serializing a hunt fails (e.g. unknown schema version)."""
