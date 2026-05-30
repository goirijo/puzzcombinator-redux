from __future__ import annotations

import pytest

from puzzcombinator import NormalizedText, build_validator
from puzzcombinator.errors import RegistryError
from puzzcombinator.validation.registry import get_custom_fn, register_custom_fn


def test_build_validator_dispatches_by_type() -> None:
    v = build_validator("normalized_text", {"answer": "hi"})
    assert isinstance(v, NormalizedText)
    assert v.answer == "hi"


def test_unknown_validator_type_raises() -> None:
    with pytest.raises(RegistryError, match="unknown validator type 'nope'"):
        build_validator("nope", {})


def test_unknown_custom_fn_raises() -> None:
    with pytest.raises(RegistryError, match="unknown custom validator fn 'ghost'"):
        get_custom_fn("ghost")


def test_register_and_get_custom_fn() -> None:
    @register_custom_fn("always_true")
    def _always(_: str) -> bool:
        return True

    assert get_custom_fn("always_true")("x") is True
