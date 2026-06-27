from __future__ import annotations

import pytest

from puzzcombinator import GraphBuilder, TextArtifact
from puzzcombinator.errors import GraphError


def test_build_returns_graph() -> None:
    builder = GraphBuilder()
    a = builder.node("a", action="start")
    b = builder.node("b", action="finish")
    graph = builder.connect(a, b, TextArtifact("hi")).build()
    assert set(graph.nodes) == {"a", "b"}
    assert list(graph.edges) == ["a->b"]
    assert graph.nodes["a"].action == "start"
    content = graph.edges["a->b"].content
    assert len(content) == 1
    assert content[0].text == "hi"


def test_node_returns_its_id_as_a_handle() -> None:
    builder = GraphBuilder()
    a = builder.node("a")
    # The returned handle *is* the node id — explicit here, so it equals "a".
    assert a == "a"
    b = builder.node("b")
    graph = builder.connect(a, b, TextArtifact("hi")).build()
    assert graph.edges["a->b"].content


def test_omitted_node_id_is_auto_generated_and_unique() -> None:
    builder = GraphBuilder()
    a = builder.node(label="first")
    b = builder.node(label="second")
    # No ids invented by the caller; the builder hands back distinct ones.
    assert a != b
    graph = builder.connect(a, b).build()
    assert set(graph.nodes) == {a, b}


def test_auto_node_id_skips_an_explicitly_taken_id() -> None:
    builder = GraphBuilder()
    taken = builder.node("n1")  # squat on the first counter value
    auto = builder.node()  # must not collide with it
    assert taken == "n1"
    assert auto != "n1"


def test_unstored_auto_handle_cannot_be_guessed() -> None:
    # The mistake: omit the id (so it is auto-generated), DON'T capture the
    # returned handle, then reference the node by a literal you assume (its
    # label, say). The real id was never stored, so the edge dangles and build()
    # fails. (With an explicit id the literal would happen to match — which is why
    # bypassing the handle silently "works" there and hides the bug.)
    builder = GraphBuilder()
    builder.node(label="The library")  # handle deliberately not captured
    builder.node(label="Solve it")
    builder.connect("The library", "Solve it")  # labels are not ids
    with pytest.raises(GraphError, match="unknown source node"):
        builder.build()


def test_auto_edge_id_disambiguates() -> None:
    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    graph = builder.connect(a, b).connect(a, b).build()
    assert set(graph.edges) == {"a->b", "a->b#2"}


def test_auto_edge_id_disambiguates_three_times() -> None:
    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    graph = builder.connect(a, b).connect(a, b).connect(a, b).build()
    assert set(graph.edges) == {"a->b", "a->b#2", "a->b#3"}


def test_connect_puts_artifacts_on_edge() -> None:
    from puzzcombinator import CaesarCipherPuzzle

    cipher = CaesarCipherPuzzle.from_plaintext(plaintext="HI", shift=1, id="c1")
    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    graph = builder.connect(a, b, *cipher.artifacts().values()).build()
    content = graph.edges["a->b"].content
    assert [art.name for art in content] == ["cipher", "shift", "solution"]
    assert content[0].ciphertext == cipher.ciphertext


def test_connect_rejects_a_bare_string() -> None:
    # A str is iterable, so without the guard "go north" would be scattered into one
    # character-artifact per letter. It must fail loudly instead.
    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    with pytest.raises(GraphError, match="got a string"):
        builder.connect(a, b, "go north")  # type: ignore[arg-type]


def test_explicit_edge_id_is_kept() -> None:
    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    graph = builder.connect(a, b, id="link").build()
    assert "link" in graph.edges


def test_duplicate_node_id_raises() -> None:
    builder = GraphBuilder()
    builder.node("a")
    with pytest.raises(GraphError, match="duplicate node id"):
        builder.node("a")


def test_duplicate_edge_id_raises() -> None:
    builder = GraphBuilder()
    a = builder.node("a")
    b = builder.node("b")
    builder.connect(a, b, id="x")
    with pytest.raises(GraphError, match="duplicate edge id"):
        builder.connect(a, b, id="x")


def test_dangling_edge_raises_on_build() -> None:
    builder = GraphBuilder()
    a = builder.node("a")
    builder.connect(a, "ghost")
    with pytest.raises(GraphError, match="unknown target node"):
        builder.build()
