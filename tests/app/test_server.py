"""Tests for the FastAPI app — exercises the real routes via the in-process client.

No network and no running server: FastAPI's TestClient calls the app directly. These
focus on the app's distinctive job — **composing** the two channels (hunt data +
workspace) into one document and splitting them back out.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from puzzcombinator import GraphBuilder, HuntDocument, TextArtifact
from puzzcombinator.app import server
from puzzcombinator.app.server import app
from puzzcombinator.serialization import to_json

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_active_path():
    """The active-document override is module state that takes precedence over PUZZ_GRAPH.
    Reset it after every test so a New/Open in one test can't leak into the env-based tests."""
    yield
    server._active_path = None


def _seed_hunt(tmp_path, monkeypatch, graph) -> None:
    """Write a graph as a hunt file (hunt data only, no workspace) and point env at it."""
    path = tmp_path / "hunt.json"
    path.write_text(to_json(HuntDocument.single(graph)), encoding="utf-8")
    monkeypatch.setenv("PUZZ_GRAPH", str(path))


def test_get_with_no_active_document_returns_empty_graph(monkeypatch) -> None:
    # No PUZZ_GRAPH and no New/Open override -> the editor opens on an empty graph (no demo).
    monkeypatch.delenv("PUZZ_GRAPH", raising=False)
    body = client.get("/api/graph").json()
    assert body["schema_version"] == "3"
    assert body["graph"] == {"nodes": [], "edges": []}
    assert body["unplaced"] == []
    # The UI channel still rides alongside as an explicit sibling (a synthesized default).
    ws = body["workspace"]
    assert set(ws) == {"views", "tabs", "active_tab"}


def test_get_synthesizes_default_workspace_when_absent(tmp_path, monkeypatch) -> None:
    # A file with hunt data but no workspace -> the server bootstraps a default: one
    # auto-arranged view over the graph, one active tab pointing at it.
    b = GraphBuilder()
    b.node("only_start")
    b.node("lonely")
    _seed_hunt(tmp_path, monkeypatch, b.build())

    ws = client.get("/api/graph").json()["workspace"]
    assert ws["active_tab"] is not None
    tab = next(t for t in ws["tabs"] if t["id"] == ws["active_tab"])
    view = ws["views"][tab["view"]]
    assert view["graph"] == "main"
    # Every node has a resolved position, and the tab has a viewport.
    assert set(view["positions"]) == {"only_start", "lonely"}
    assert {"x", "y"} <= set(view["positions"]["only_start"])
    assert {"x", "y", "zoom"} <= set(tab["viewport"])


def test_loads_graph_from_env_file(tmp_path, monkeypatch) -> None:
    b = GraphBuilder()
    b.node("only_start")
    b.node("lonely")
    _seed_hunt(tmp_path, monkeypatch, b.build())

    ids = {n["id"] for n in client.get("/api/graph").json()["graph"]["nodes"]}
    assert ids == {"only_start", "lonely"}


def test_put_persists_node_edits(tmp_path, monkeypatch) -> None:
    # Seed a hunt file, edit a node label via PUT, and confirm a fresh GET sees it.
    b = GraphBuilder()
    start = b.node("start", label="Welcome")
    end = b.node("end")
    _seed_hunt(tmp_path, monkeypatch, b.connect(start, end, TextArtifact("go", id="t1")).build())

    body = client.get("/api/graph").json()
    for node in body["graph"]["nodes"]:
        if node["id"] == "start":
            node["label"] = "Edited"
    # PUT sends both channels back, symmetrically.
    response = client.put(
        "/api/graph", json={"graph": body["graph"], "workspace": body["workspace"]}
    )
    assert response.status_code == 200
    assert response.json() == {"saved": True}

    reloaded = client.get("/api/graph").json()["graph"]
    edited = next(n for n in reloaded["nodes"] if n["id"] == "start")
    assert edited["label"] == "Edited"
    # The edge's artifact survived the save round-trip (content preserved verbatim).
    assert reloaded["edges"][0]["content"][0]["id"] == "t1"


def test_put_persists_workspace_positions(tmp_path, monkeypatch) -> None:
    # Move a node and confirm the stored position survives — and is NOT overwritten by
    # auto-layout on the next GET (stored placement wins).
    b = GraphBuilder()
    b.node("start")
    b.node("end")
    _seed_hunt(tmp_path, monkeypatch, b.build())

    body = client.get("/api/graph").json()
    ws = body["workspace"]
    view_id = next(iter(ws["views"]))
    ws["views"][view_id]["positions"]["start"] = {"x": 999.0, "y": 42.0}

    saved = client.put("/api/graph", json={"graph": body["graph"], "workspace": ws})
    assert saved.status_code == 200

    reloaded = client.get("/api/graph").json()["workspace"]
    assert reloaded["views"][view_id]["positions"]["start"] == {"x": 999.0, "y": 42.0}


def test_get_returns_empty_pool_when_file_has_none(tmp_path, monkeypatch) -> None:
    b = GraphBuilder()
    b.node("start")
    _seed_hunt(tmp_path, monkeypatch, b.build())
    assert client.get("/api/graph").json()["unplaced"] == []


def test_get_exposes_seeded_unplaced_pool(tmp_path, monkeypatch) -> None:
    # A hunt file whose document carries a loose-artifact pool surfaces it on GET.
    b = GraphBuilder()
    b.node("start")
    doc = HuntDocument(
        graphs={"main": b.build()},
        unplaced={"main": (TextArtifact("loose", id="u1"),)},
    )
    path = tmp_path / "hunt.json"
    path.write_text(to_json(doc), encoding="utf-8")
    monkeypatch.setenv("PUZZ_GRAPH", str(path))

    pool = client.get("/api/graph").json()["unplaced"]
    assert [a["id"] for a in pool] == ["u1"]
    assert pool[0]["payload"]["text"] == "loose"


def test_put_persists_unplaced_pool(tmp_path, monkeypatch) -> None:
    # The pool survives a load→edit→save→reload cycle (the passthrough that keeps a save
    # from wiping loose artifacts the editor isn't rendering yet).
    b = GraphBuilder()
    b.node("start")
    _seed_hunt(tmp_path, monkeypatch, b.build())

    from puzzcombinator.artifacts.registry import artifact_to_dict

    body = client.get("/api/graph").json()
    body["unplaced"] = [artifact_to_dict(TextArtifact("scratch", id="u1"))]
    saved = client.put(
        "/api/graph",
        json={"graph": body["graph"], "unplaced": body["unplaced"], "workspace": body["workspace"]},
    )
    assert saved.status_code == 200

    reloaded = client.get("/api/graph").json()["unplaced"]
    assert [a["id"] for a in reloaded] == ["u1"]
    assert reloaded[0]["payload"]["text"] == "scratch"


def test_put_with_no_active_document_is_rejected(monkeypatch) -> None:
    # With no active document there is nowhere to save; the server says so (409) rather than
    # silently writing somewhere.
    monkeypatch.delenv("PUZZ_GRAPH", raising=False)
    body = client.get("/api/graph").json()
    response = client.put(
        "/api/graph", json={"graph": body["graph"], "workspace": body["workspace"]}
    )
    assert response.status_code == 409


def test_new_creates_empty_document_and_enables_save(tmp_path, monkeypatch) -> None:
    # New writes an empty document to a fresh path and switches onto it: GET then draws an
    # empty graph and a save (which was 409 with no active document) now succeeds.
    monkeypatch.delenv("PUZZ_GRAPH", raising=False)
    target = tmp_path / "fresh.json"
    created = client.post("/api/document/new", json={"path": str(target)})
    assert created.status_code == 200
    assert target.exists()

    body = client.get("/api/graph").json()
    assert body["graph"] == {"nodes": [], "edges": []}

    saved = client.put("/api/graph", json={"graph": body["graph"], "workspace": body["workspace"]})
    assert saved.status_code == 200


def test_new_refuses_existing_file(tmp_path) -> None:
    # New must not clobber an existing file — that's Open's job.
    target = tmp_path / "exists.json"
    target.write_text("{}", encoding="utf-8")
    response = client.post("/api/document/new", json={"path": str(target)})
    assert response.status_code == 409


def test_new_rejects_missing_path() -> None:
    assert client.post("/api/document/new", json={}).status_code == 422


def test_open_switches_active_document(tmp_path, monkeypatch) -> None:
    # Seed document A via env, then Open document B on disk: GET reflects B, not A.
    a = GraphBuilder()
    a.node("from_a")
    _seed_hunt(tmp_path, monkeypatch, a.build())

    b = GraphBuilder()
    b.node("from_b")
    other = tmp_path / "b.json"
    other.write_text(to_json(HuntDocument.single(b.build())), encoding="utf-8")

    opened = client.post("/api/document/open", json={"path": str(other)})
    assert opened.status_code == 200
    ids = {n["id"] for n in client.get("/api/graph").json()["graph"]["nodes"]}
    assert ids == {"from_b"}


def test_open_missing_file_is_404(tmp_path) -> None:
    response = client.post("/api/document/open", json={"path": str(tmp_path / "nope.json")})
    assert response.status_code == 404


def test_open_malformed_file_is_422(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    response = client.post("/api/document/open", json={"path": str(bad)})
    assert response.status_code == 422


def test_save_as_writes_current_graph_and_switches(tmp_path, monkeypatch) -> None:
    # The untitled-document workflow: start empty, build a node, Save As to a new path. The
    # file gets the *current* graph (not an empty doc), and a later plain Save lands there.
    monkeypatch.delenv("PUZZ_GRAPH", raising=False)
    body = client.get("/api/graph").json()  # the empty startup document
    body["graph"]["nodes"].append({"id": "n1", "action": None, "label": "Hi", "notes": None})

    target = tmp_path / "named.json"
    saved = client.post(
        "/api/document/save-as",
        json={
            "path": str(target),
            "graph": body["graph"],
            "unplaced": body["unplaced"],
            "workspace": body["workspace"],
        },
    )
    assert saved.status_code == 200
    assert target.exists()
    # The new file is now active: GET reflects the saved node, and a plain Save succeeds.
    assert {n["id"] for n in client.get("/api/graph").json()["graph"]["nodes"]} == {"n1"}
    reput = client.get("/api/graph").json()
    assert (
        client.put(
            "/api/graph", json={"graph": reput["graph"], "workspace": reput["workspace"]}
        ).status_code
        == 200
    )


def test_save_as_refuses_existing_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PUZZ_GRAPH", raising=False)
    target = tmp_path / "taken.json"
    target.write_text("{}", encoding="utf-8")
    body = client.get("/api/graph").json()
    response = client.post(
        "/api/document/save-as",
        json={"path": str(target), "graph": body["graph"], "workspace": body["workspace"]},
    )
    assert response.status_code == 409


def test_save_as_rejects_missing_path() -> None:
    assert client.post("/api/document/save-as", json={}).status_code == 422


def test_save_as_rejects_invalid_graph(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PUZZ_GRAPH", raising=False)
    body = client.get("/api/graph").json()
    # A dangling edge (no such target) must be rejected by the serialization layer.
    body["graph"]["edges"].append({"id": "x", "source": "n1", "target": "ghost", "content": []})
    response = client.post(
        "/api/document/save-as",
        json={
            "path": str(tmp_path / "x.json"),
            "graph": body["graph"],
            "workspace": body["workspace"],
        },
    )
    assert response.status_code == 422


def test_arrange_returns_positions_for_each_node(tmp_path, monkeypatch) -> None:
    # The editor posts its live graph block; the server replies with a position per node.
    b = GraphBuilder()
    start = b.node("start")
    end = b.node("end")
    _seed_hunt(tmp_path, monkeypatch, b.connect(start, end, TextArtifact("go", id="t1")).build())
    graph = client.get("/api/graph").json()["graph"]

    body = client.post("/api/arrange", json={"graph": graph, "orientation": "horizontal"}).json()
    assert set(body["positions"]) == {"start", "end"}
    assert {"x", "y"} == set(body["positions"]["start"])


def test_arrange_horizontal_and_vertical_differ(tmp_path, monkeypatch) -> None:
    # Same chain, two orientations: horizontal advances x along the chain, vertical y.
    b = GraphBuilder()
    start = b.node("start")
    end = b.node("end")
    _seed_hunt(tmp_path, monkeypatch, b.connect(start, end, TextArtifact("go", id="t1")).build())
    graph = client.get("/api/graph").json()["graph"]

    horiz = client.post("/api/arrange", json={"graph": graph, "orientation": "horizontal"}).json()
    vert = client.post("/api/arrange", json={"graph": graph, "orientation": "vertical"}).json()
    # Horizontal: the chain spreads along x (end is to the right, same y as start).
    assert horiz["positions"]["end"]["x"] > horiz["positions"]["start"]["x"]
    assert horiz["positions"]["end"]["y"] == horiz["positions"]["start"]["y"]
    # Vertical: the chain spreads along y (end is below, same x as start).
    assert vert["positions"]["end"]["y"] > vert["positions"]["start"]["y"]
    assert vert["positions"]["end"]["x"] == vert["positions"]["start"]["x"]


def test_arrange_defaults_to_horizontal(tmp_path, monkeypatch) -> None:
    b = GraphBuilder()
    start = b.node("start")
    end = b.node("end")
    _seed_hunt(tmp_path, monkeypatch, b.connect(start, end, TextArtifact("go", id="t1")).build())
    graph = client.get("/api/graph").json()["graph"]

    omitted = client.post("/api/arrange", json={"graph": graph}).json()
    horiz = client.post("/api/arrange", json={"graph": graph, "orientation": "horizontal"}).json()
    assert omitted["positions"] == horiz["positions"]


def test_arrange_rejects_unknown_orientation(tmp_path, monkeypatch) -> None:
    b = GraphBuilder()
    b.node("start")
    _seed_hunt(tmp_path, monkeypatch, b.build())
    graph = client.get("/api/graph").json()["graph"]
    response = client.post("/api/arrange", json={"graph": graph, "orientation": "diagonal"})
    assert response.status_code == 422


def test_arrange_rejects_cyclic_graph() -> None:
    # A 2-node cycle has no topological order — layout must refuse it, not hang.
    graph = {
        "nodes": [
            {"id": "a", "action": None, "label": None, "notes": None},
            {"id": "b", "action": None, "label": None, "notes": None},
        ],
        "edges": [
            {"id": "e1", "source": "a", "target": "b", "content": []},
            {"id": "e2", "source": "b", "target": "a", "content": []},
        ],
    }
    response = client.post("/api/arrange", json={"graph": graph, "orientation": "horizontal"})
    assert response.status_code == 422


def test_put_rejects_invalid_graph(tmp_path, monkeypatch) -> None:
    b = GraphBuilder()
    b.node("start")
    _seed_hunt(tmp_path, monkeypatch, b.build())
    body = client.get("/api/graph").json()
    # A dangling edge (target node missing) must be rejected by the serialization layer.
    body["graph"]["edges"].append({"id": "x", "source": "start", "target": "ghost", "content": []})
    response = client.put(
        "/api/graph", json={"graph": body["graph"], "workspace": body["workspace"]}
    )
    assert response.status_code == 422
