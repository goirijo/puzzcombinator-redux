"""Round-trip every built-in validator through its params seam + eq/hash."""

from __future__ import annotations

import re

import pytest

from puzzcombinator import CustomFn, ExactMatch, Manual, NormalizedText, Regex
from puzzcombinator.validation.base import Validator
from puzzcombinator.validation.registry import build_validator

CASES: list[Validator] = [
    ExactMatch(answer="Secret"),
    NormalizedText(answer="Red Door", fold_case=False, strip_punctuation=False),
    Regex(pattern=r"\d+", flags=re.IGNORECASE),
    Manual(prompt="confirm in person"),
    CustomFn(fn_name="some_fn"),
]


@pytest.mark.parametrize("validator", CASES, ids=lambda v: v.type_name)
def test_params_roundtrip(validator: Validator) -> None:
    rebuilt = build_validator(validator.type_name, validator.to_params())
    assert rebuilt == validator
    assert type(rebuilt) is type(validator)


def test_eq_against_non_validator_is_not_equal() -> None:
    assert ExactMatch(answer="x") != "x"
    assert ExactMatch(answer="x") != NormalizedText(answer="x")


def test_validators_are_hashable() -> None:
    bucket = {ExactMatch(answer="a"), ExactMatch(answer="a"), ExactMatch(answer="b")}
    assert len(bucket) == 2
