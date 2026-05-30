"""Pluggable answer validation."""

from __future__ import annotations

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
    "CustomFn",
    "ExactMatch",
    "Manual",
    "NormalizedText",
    "Regex",
    "ValidationResult",
    "Validator",
    "build_validator",
    "get_custom_fn",
    "register_custom_fn",
    "register_validator",
]
