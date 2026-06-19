"""Tests for the FastAPI app — exercises the real routes via the in-process client.

No network and no running server: FastAPI's TestClient calls the app directly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from puzzcombinator.app.server import app

client = TestClient(app)


def test_api_graph_returns_graph_envelope_and_layout() -> None:
    body = client.get("/api/graph").json()
    # GET returns the drawn graph's own envelope plus a layout map.
    assert body["schema_version"] == "3"
    assert {n["id"] for n in body["graph"]["nodes"]} >= {"start", "solve", "combine", "end"}
    assert set(body["layout"]) == {n["id"] for n in body["graph"]["nodes"]}


def test_api_graph_layout_entries_have_coordinates() -> None:
    layout = client.get("/api/graph").json()["layout"]
    start = layout["start"]
    assert start["layer"] == 0
    assert {"layer", "row", "x", "y"} <= set(start)


def test_loads_graph_from_env_file(tmp_path, monkeypatch) -> None:
    # Point PUZZ_GRAPH at a serialized two-node hunt document and confirm it's drawn
    # instead of the demo.
    from puzzcombinator import GraphBuilder, HuntDocument
    from puzzcombinator.serialization import to_json

    b = GraphBuilder()
    b.node("only_start")
    b.node("lonely")
    path = tmp_path / "hunt.json"
    path.write_text(to_json(HuntDocument.single(b.build())), encoding="utf-8")
    monkeypatch.setenv("PUZZ_GRAPH", str(path))

    ids = {n["id"] for n in client.get("/api/graph").json()["graph"]["nodes"]}
    assert ids == {"only_start", "lonely"}


def test_put_persists_node_edits(tmp_path, monkeypatch) -> None:
    # Seed a hunt file, edit a node label via PUT, and confirm a fresh GET sees it.
    from puzzcombinator import GraphBuilder, HuntDocument, TextArtifact
    from puzzcombinator.serialization import to_json

    b = GraphBuilder()
    start = b.node("start", label="Welcome")
    end = b.node("end")
    graph = b.connect(start, end, TextArtifact("go", id="t1")).build()
    path = tmp_path / "hunt.json"
    path.write_text(to_json(HuntDocument.single(graph)), encoding="utf-8")
    monkeypatch.setenv("PUZZ_GRAPH", str(path))

    block = client.get("/api/graph").json()["graph"]
    for node in block["nodes"]:
        if node["id"] == "start":
            node["label"] = "Edited"
    response = client.put("/api/graph", json=block)
    assert response.status_code == 200
    assert response.json() == {"saved": True}

    reloaded = client.get("/api/graph").json()["graph"]
    edited = next(n for n in reloaded["nodes"] if n["id"] == "start")
    assert edited["label"] == "Edited"
    # The edge's artifact survived the save round-trip (content preserved verbatim).
    assert reloaded["edges"][0]["content"][0]["id"] == "t1"


def test_put_in_demo_mode_is_rejected(monkeypatch) -> None:
    # With no PUZZ_GRAPH there is nowhere to save; the server says so rather than
    # silently writing the demo somewhere.
    monkeypatch.delenv("PUZZ_GRAPH", raising=False)
    block = client.get("/api/graph").json()["graph"]
    response = client.put("/api/graph", json=block)
    assert response.status_code == 409
