"""The pluggable validator interface.

A :class:`Validator` checks a player's submission against a puzzle's expected
answer. Validators are independent of both the graph and puzzles — they don't
know they live on a puzzle — so they compose freely and a future runtime can
call them directly.

``to_params`` / ``from_params`` are the serialization seam: each validator
expresses itself as JSON-safe data and rebuilds from it, so the codec never has
to reflect over ``__init__``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(frozen=True)
class ValidationResult:
    """The outcome of validating a submission. A pure value: no player reference."""

    ok: bool
    normalized_input: str | None = None
    message: str | None = None


class Validator(ABC):
    """Base class for all validators."""

    #: Stable registry key, e.g. ``"normalized_text"``.
    type_name: ClassVar[str]

    @abstractmethod
    def validate(self, submission: str) -> ValidationResult:
        """Check ``submission`` and return a :class:`ValidationResult`."""

    @abstractmethod
    def to_params(self) -> dict[str, Any]:
        """Return JSON-safe constructor arguments for this validator."""

    @classmethod
    @abstractmethod
    def from_params(cls, params: dict[str, Any]) -> Validator:
        """Rebuild a validator from :meth:`to_params` output."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Validator) or type(self) is not type(other):
            return NotImplemented
        return self.to_params() == other.to_params()

    def __hash__(self) -> int:
        return hash((type(self).__name__, tuple(sorted(self.to_params().items()))))
