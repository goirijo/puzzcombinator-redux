"""The puzzle abstraction.

A :class:`Puzzle` is what a node *does*: it owns the puzzle data, the
validator(s) that gate its output, and its printable rendering. It deliberately
knows nothing about :class:`~puzzcombinator.core.graph.Node` — the graph holds a
puzzle by composition — which keeps the graph layer puzzle-agnostic.

The model is stateless: :meth:`check` is pure, so a future runtime layers
sessions/progression on top by calling it without the puzzle ever holding state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, ClassVar

from puzzcombinator.rendering.fragment import Audience, RenderFragment
from puzzcombinator.validation.base import ValidationResult, Validator


class Puzzle(ABC):
    """Base class for all puzzle types."""

    #: Stable registry key, e.g. ``"caesar_cipher"``.
    type_name: ClassVar[str]

    def __init__(
        self,
        id: str,
        validators: Iterable[Validator],
        require_all: bool = False,
    ) -> None:
        self.id = id
        self.validators: list[Validator] = list(validators)
        #: When True, every validator must pass; otherwise any one suffices.
        self.require_all = require_all

    def check(self, submission: str) -> ValidationResult:
        """Validate a submission against this puzzle's validators (pure)."""
        results = [v.validate(submission) for v in self.validators]
        if not results:
            return ValidationResult(
                ok=False, normalized_input=submission, message="no validators configured"
            )
        ok = all(r.ok for r in results) if self.require_all else any(r.ok for r in results)
        representative = next((r for r in results if r.ok), results[0])
        return ValidationResult(
            ok=ok,
            normalized_input=representative.normalized_input,
            message=None if ok else "incorrect",
        )

    def is_solved(self, submission: str) -> bool:
        return self.check(submission).ok

    @abstractmethod
    def to_payload(self) -> dict[str, Any]:
        """Return this puzzle's JSON-safe, type-specific fields."""

    @classmethod
    @abstractmethod
    def from_payload(
        cls,
        id: str,
        payload: dict[str, Any],
        validators: list[Validator],
        require_all: bool = False,
    ) -> Puzzle:
        """Rebuild a puzzle from :meth:`to_payload` output plus its validators."""

    @abstractmethod
    def render(self, audience: Audience) -> RenderFragment:
        """Produce a printable fragment for the given audience."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Puzzle) or type(self) is not type(other):
            return NotImplemented
        return (
            self.id == other.id
            and self.require_all == other.require_all
            and self.validators == other.validators
            and self.to_payload() == other.to_payload()
        )

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.id))
