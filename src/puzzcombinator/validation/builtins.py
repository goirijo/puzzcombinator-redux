"""Built-in validators, self-registering on import."""

from __future__ import annotations

import re
import string
from typing import Any

from puzzcombinator.validation.base import ValidationResult, Validator
from puzzcombinator.validation.registry import get_custom_fn, register_validator

_PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation)


def _normalize(
    text: str,
    *,
    fold_case: bool,
    strip_whitespace: bool,
    strip_punctuation: bool,
) -> str:
    """Apply the configured normalizations in a stable order."""
    if strip_punctuation:
        text = text.translate(_PUNCTUATION_TABLE)
    if fold_case:
        text = text.casefold()
    if strip_whitespace:
        text = " ".join(text.split())
    return text


@register_validator
class ExactMatch(Validator):
    """Accept only a byte-for-byte equal submission."""

    type_name = "exact_match"

    def __init__(self, answer: str) -> None:
        self.answer = answer

    def validate(self, submission: str) -> ValidationResult:
        ok = submission == self.answer
        return ValidationResult(
            ok=ok,
            normalized_input=submission,
            message=None if ok else "does not match exactly",
        )

    def to_params(self) -> dict[str, Any]:
        return {"answer": self.answer}

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> ExactMatch:
        return cls(answer=params["answer"])


@register_validator
class NormalizedText(Validator):
    """Accept a submission that matches after case/whitespace/punctuation folding."""

    type_name = "normalized_text"

    def __init__(
        self,
        answer: str,
        fold_case: bool = True,
        strip_whitespace: bool = True,
        strip_punctuation: bool = True,
    ) -> None:
        self.answer = answer
        self.fold_case = fold_case
        self.strip_whitespace = strip_whitespace
        self.strip_punctuation = strip_punctuation

    def _norm(self, text: str) -> str:
        return _normalize(
            text,
            fold_case=self.fold_case,
            strip_whitespace=self.strip_whitespace,
            strip_punctuation=self.strip_punctuation,
        )

    def validate(self, submission: str) -> ValidationResult:
        normalized = self._norm(submission)
        ok = normalized == self._norm(self.answer)
        return ValidationResult(
            ok=ok,
            normalized_input=normalized,
            message=None if ok else "does not match",
        )

    def to_params(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "fold_case": self.fold_case,
            "strip_whitespace": self.strip_whitespace,
            "strip_punctuation": self.strip_punctuation,
        }

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> NormalizedText:
        return cls(
            answer=params["answer"],
            fold_case=params.get("fold_case", True),
            strip_whitespace=params.get("strip_whitespace", True),
            strip_punctuation=params.get("strip_punctuation", True),
        )


@register_validator
class Regex(Validator):
    """Accept a submission that fully matches a regular expression."""

    type_name = "regex"

    def __init__(self, pattern: str, flags: int = 0) -> None:
        self.pattern = pattern
        self.flags = int(flags)

    def validate(self, submission: str) -> ValidationResult:
        ok = re.fullmatch(self.pattern, submission, self.flags) is not None
        return ValidationResult(
            ok=ok,
            normalized_input=submission,
            message=None if ok else "does not match pattern",
        )

    def to_params(self) -> dict[str, Any]:
        return {"pattern": self.pattern, "flags": self.flags}

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> Regex:
        return cls(pattern=params["pattern"], flags=int(params.get("flags", 0)))


@register_validator
class Manual(Validator):
    """Honor-system validator for physical puzzles that need human confirmation.

    Always returns ``ok=True`` with a message a runtime can route to a
    game-master for real verification.
    """

    type_name = "manual"

    def __init__(self, prompt: str | None = None) -> None:
        self.prompt = prompt

    def validate(self, submission: str) -> ValidationResult:
        return ValidationResult(
            ok=True,
            normalized_input=submission,
            message="requires human confirmation",
        )

    def to_params(self) -> dict[str, Any]:
        return {"prompt": self.prompt}

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> Manual:
        return cls(prompt=params.get("prompt"))


@register_validator
class CustomFn(Validator):
    """Delegate to a host-registered predicate, referenced by name.

    Serializes only ``fn_name``; the implementation must be registered via
    :func:`~puzzcombinator.validation.registry.register_custom_fn` before the
    hunt is loaded, else validation raises ``RegistryError``.
    """

    type_name = "custom_fn"

    def __init__(self, fn_name: str) -> None:
        self.fn_name = fn_name

    def validate(self, submission: str) -> ValidationResult:
        fn = get_custom_fn(self.fn_name)
        ok = bool(fn(submission))
        return ValidationResult(
            ok=ok,
            normalized_input=submission,
            message=None if ok else "rejected by custom validator",
        )

    def to_params(self) -> dict[str, Any]:
        return {"fn_name": self.fn_name}

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> CustomFn:
        return cls(fn_name=params["fn_name"])
