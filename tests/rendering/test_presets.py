from __future__ import annotations

from puzzcombinator.rendering import presets
from puzzcombinator.rendering.presets import CARD_CSS


def test_text_escapes_and_wraps() -> None:
    frag = presets.text("a < b & c", title="Clue", id="p1")
    assert frag.kind == "html"
    assert "a &lt; b &amp; c" in frag.markup
    assert "<h3>Clue</h3>" in frag.markup
    assert 'data-id="p1"' in frag.markup
    assert frag.styles == CARD_CSS


def test_text_monospace_uses_pre() -> None:
    frag = presets.text("48.8584 N, 2.2945 E", monospace=True)
    assert "<pre>48.8584 N, 2.2945 E</pre>" in frag.markup
    # no title and no id -> neither rendered
    assert "<h3>" not in frag.markup
    assert "data-id" not in frag.markup


def test_text_plain_uses_paragraph() -> None:
    frag = presets.text("ROAD")
    assert "<p>ROAD</p>" in frag.markup
    assert "<pre>" not in frag.markup


def test_image_builds_figure_with_caption() -> None:
    uri = "data:image/png;base64,AAAA"
    frag = presets.image(uri, alt="a map", caption="where next?", title="Photo")
    assert f'src="{uri}"' in frag.markup
    assert 'alt="a map"' in frag.markup
    assert "<figcaption>where next?</figcaption>" in frag.markup
    assert frag.styles == CARD_CSS


def test_image_without_caption_omits_figcaption() -> None:
    frag = presets.image("data:image/png;base64,AAAA")
    assert "<figcaption>" not in frag.markup


def test_card_inserts_body_verbatim() -> None:
    frag = presets.card("<svg></svg>", title="Custom")
    assert '<div class="pc-body"><svg></svg></div>' in frag.markup
    assert "<h3>Custom</h3>" in frag.markup


def test_shared_css_dedups_across_fragments() -> None:
    # All presets carry the identical CSS string, so a set collapses them to one.
    frags = [presets.text("x"), presets.image("data:,"), presets.card("<b>y</b>")]
    assert len({f.styles for f in frags}) == 1
