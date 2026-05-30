from __future__ import annotations

import re

from puzzcombinator import CustomFn, ExactMatch, Manual, NormalizedText, Regex
from puzzcombinator.validation.registry import register_custom_fn


def test_exact_match() -> None:
    v = ExactMatch(answer="Secret")
    assert v.validate("Secret").ok
    assert not v.validate("secret").ok


def test_normalized_text_folds_case_whitespace_punctuation() -> None:
    v = NormalizedText(answer="The Red Door!")
    for variant in ["the red door", "  THE   red DOOR ", "the, red. door?"]:
        result = v.validate(variant)
        assert result.ok, variant
        assert result.normalized_input is not None
    bad = v.validate("the blue door")
    assert not bad.ok
    assert bad.normalized_input == "the blue door"


def test_normalized_text_can_disable_folding() -> None:
    v = NormalizedText(answer="Yes", fold_case=False)
    assert v.validate("Yes").ok
    assert not v.validate("yes").ok


def test_regex_fullmatch_and_flag_survives() -> None:
    v = Regex(pattern=r"[a-z]+\d{2}", flags=re.IGNORECASE)
    assert v.validate("ABC42").ok
    assert not v.validate("ABC4").ok
    # Flags serialize as an int and round-trip through from_params.
    clone = Regex.from_params(v.to_params())
    assert clone.validate("ABC42").ok


def test_manual_is_honor_system() -> None:
    result = Manual(prompt="show the key").validate("whatever")
    assert result.ok
    assert result.message == "requires human confirmation"


def test_custom_fn_uses_registered_predicate() -> None:
    register_custom_fn("is_digits")(str.isdigit)
    v = CustomFn(fn_name="is_digits")
    assert v.validate("12345").ok
    assert not v.validate("12a45").ok
