"""Tests for the composable binder: Section / Chapter / Binder.

A binder is just *a collection of renderings that logically belong together* — the
designer chooses what goes in. These exercise the two headline cases (a list of
artifacts; a page per node) plus the composition mechanics: chapter grouping, the
two-level dividers, HTML escaping, and the cross-document CSS de-duplication that lets
each artifact carry its own styles.
"""

from __future__ import annotations

from puzzcombinator import (
    Binder,
    CaesarCipherPuzzle,
    Chapter,
    CrosswordPuzzle,
    GraphBuilder,
    Section,
    TextArtifact,
    topological_order,
)


def _cipher() -> CaesarCipherPuzzle:
    return CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")


def _crossword() -> CrosswordPuzzle:
    return CrosswordPuzzle(
        solution=["STAR", "H##A", "O##I", "PLOD"],
        across={1: "Celestial body", 3: "Walk heavily"},
        down={1: "Place to buy things", 2: "Sudden attack"},
        highlight=[(0, 3), (2, 0), (0, 2), (3, 3)],
        id="cw",
    )


# -- Section --------------------------------------------------------------


def test_section_from_artifact_wraps_markup_and_keeps_styles() -> None:
    artifact = _cipher().artifacts("cipher")
    section = Section.from_artifact(artifact)
    assert 'class="binder-section"' in section.markup
    assert 'data-id="c1-cipher"' in section.markup
    assert artifact.render().markup in section.markup
    # the artifact's own CSS is carried, not yet joined
    assert section.styles == (artifact.render().styles,)


def test_section_from_node_shows_header_notes_and_both_sides() -> None:
    builder = GraphBuilder()
    a = builder.node(label="Welcome")
    b = builder.node(action="solve", label="Caesar gate", notes="leave on the bench")
    c = builder.node(label="Treasure")
    graph = (
        builder.connect(a, b, TextArtifact("decode me", id="in"))
        .connect(b, c, TextArtifact("go to the fountain", id="out"))
        .build()
    )
    section = Section.from_node(graph, b)
    assert "Caesar gate" in section.markup
    assert "solve" in section.markup
    assert "leave on the bench" in section.markup  # notes
    assert "Receives" in section.markup and "decode me" in section.markup
    assert "Produces" in section.markup and "go to the fountain" in section.markup


def test_section_from_node_can_omit_a_side() -> None:
    builder = GraphBuilder()
    a = builder.node(label="start")
    b = builder.node(action="solve")
    c = builder.node(label="end")
    graph = (
        builder.connect(a, b, TextArtifact("decode me", id="in"))
        .connect(b, c, TextArtifact("go to the fountain", id="out"))
        .build()
    )
    section = Section.from_node(graph, b, outgoing=False)
    assert "Receives" in section.markup
    assert "Produces" not in section.markup
    assert "go to the fountain" not in section.markup


def test_section_from_node_escapes_text() -> None:
    builder = GraphBuilder()
    a = builder.node(label="<script>alert(1)</script>")
    b = builder.node(label="end")
    graph = builder.connect(a, b, TextArtifact("hi")).build()
    section = Section.from_node(graph, a)
    assert "<script>" not in section.markup
    assert "&lt;script&gt;" in section.markup


# -- Chapter --------------------------------------------------------------


def test_chapter_of_artifacts_makes_one_section_each_with_title() -> None:
    chapter = Chapter.of_artifacts(
        [_cipher().artifacts("cipher"), _crossword().artifacts("crossword")],
        title="Player puzzles",
    )
    assert len(chapter.sections) == 2
    body = chapter._body(section_divider="")
    assert "<h2>Player puzzles</h2>" in body
    assert 'class="binder-chapter"' in body


def test_chapter_without_title_has_no_heading() -> None:
    chapter = Chapter.of_artifacts([_cipher().artifacts("cipher")])
    assert "<h2>" not in chapter._body(section_divider="")


# -- Binder: use case 1 (a collection of artifacts) -----------------------


def test_binder_of_artifacts_shows_every_solution() -> None:
    binder = Binder.of_artifacts(
        [_cipher().artifacts("solution"), _crossword().artifacts("solution")],
        title="Answer key",
    )
    html = binder.render()
    assert "<!DOCTYPE html>" in html
    assert "<title>Answer key</title>" in html
    assert "FOUNTAIN" in html  # cipher solution
    assert "ROAD" in html  # crossword hidden word


# -- Binder: use case 2 (a page per node) ---------------------------------


def test_binder_of_nodes_pages_in_topological_order() -> None:
    cipher = _cipher()
    builder = GraphBuilder()
    start = builder.node("start", label="Welcome")
    solve = builder.node("solve", action="solve", notes="leave on the bench")
    end = builder.node("end", label="Treasure")
    graph = (
        builder.connect(start, solve, *cipher.artifacts().values())
        .connect(solve, end, TextArtifact("Go to the fountain."))
        .build()
    )
    html = Binder.of_nodes(graph, topological_order(graph)).render()
    assert "Welcome" in html and "Treasure" in html
    assert "leave on the bench" in html  # node notes
    assert "Go to the fountain." in html  # produced clue
    assert "FOUNTAIN" in html  # the solution piece placed on the edge is shown
    # solve order: Welcome's page precedes Treasure's
    assert html.index("Welcome") < html.index("Treasure")


# -- Binder: composition mechanics ----------------------------------------


def test_binder_breaks_between_chapters_and_rules_within() -> None:
    from puzzcombinator.rendering.binder import PAGE_BREAK, RULE

    cipher = _cipher()
    binder = Binder(
        (
            Chapter.of_artifacts([cipher.artifacts("cipher"), cipher.artifacts("shift")]),
            Chapter.of_artifacts([cipher.artifacts("solution")]),
        )
    )
    html = binder.render()
    assert PAGE_BREAK in html  # page break element between the two chapters
    assert RULE in html  # thin rule between the two sections of chapter 1


def test_each_artifact_css_appears_once() -> None:
    # Two cipher pieces carry the same CSS block; the head must hold it a single time.
    cipher = _cipher()
    block = cipher.artifacts("cipher").render().styles
    assert block  # the cipher carries CSS, so this test is meaningful
    html = Binder.of_artifacts([cipher.artifacts("cipher"), cipher.artifacts("solution")]).render()
    assert html.count(block) == 1


def test_dividers_are_customizable() -> None:
    cipher = _cipher()
    binder = Binder(
        (
            Chapter.of_artifacts([cipher.artifacts("cipher"), cipher.artifacts("shift")]),
            Chapter.of_artifacts([cipher.artifacts("solution")]),
        ),
        chapter_divider="<!--CHAP-->",
        section_divider="<!--SECT-->",
    )
    from puzzcombinator.rendering.binder import PAGE_BREAK

    html = binder.render()
    assert "<!--CHAP-->" in html  # between the two chapters
    assert "<!--SECT-->" in html  # between the two sections of chapter 1
    assert PAGE_BREAK not in html  # the default page-break element was replaced
