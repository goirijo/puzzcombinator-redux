"""Registry mapping puzzle ``type_name`` to its class, for deserialization."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from puzzcombinator.errors import RegistryError

if TYPE_CHECKING:
    from puzzcombinator.puzzles.base import Puzzle
    from puzzcombinator.validation.base import Validator

_PUZZLE_TYPES: dict[str, type[Puzzle]] = {}


def register_puzzle[P: type[Puzzle]](cls: P) -> P:
    """Class decorator: register a puzzle subclass under its ``type_name``."""
    _PUZZLE_TYPES[cls.type_name] = cls
    return cls


def build_puzzle(
    type_name: str,
    id: str,
    payload: dict[str, Any],
    validators: list[Validator],
    require_all: bool = False,
) -> Puzzle:
    """Reconstruct a puzzle from its serialized parts."""
    try:
        cls = _PUZZLE_TYPES[type_name]
    except KeyError:
        raise RegistryError(
            f"unknown puzzle type {type_name!r}; known: {sorted(_PUZZLE_TYPES)}"
        ) from None
    return cls.from_payload(id, payload, validators, require_all)
