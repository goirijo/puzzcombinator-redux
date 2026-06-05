"""Fragment-layer tests: the migrated, audience-free rendering primitive.

This covers `RenderFragment` itself. The binder + puzzle integration tests that once
shared this file moved to `test_binder.py` (skipped until those layers migrate).
"""

from __future__ import annotations

from puzzcombinator.rendering.fragment import RenderFragment


def test_svg_fragment_is_embeddable() -> None:
    fragment = RenderFragment.svg("<svg><rect/></svg>")
    assert fragment.kind == "svg"
    assert fragment.markup.startswith("<svg")
