"""The FastAPI app: serve the hunt the editor draws and save edits back.

Deliberately thin — every interesting decision lives in the ``serialization`` and
``visualization`` layers. The app's distinctive job is **composition**: a saved hunt
file carries *two independent channels* — hunt data (``graphs``) and the editor's UI
state (``workspace``) — and this layer is the one that stitches them into one document
and splits them back out, handing each to its own codec. The two never see each other.

* ``GET /api/graph`` returns the drawn graph's envelope plus a ``workspace`` block (the
  stored views/tabs, or a synthesized default), with every node's position resolved.
* ``PUT /api/graph`` writes an edited ``{graph, workspace}`` body back to the
  ``PUZZ_GRAPH`` file: ``graph`` through the serialization layer (validated), ``workspace``
  through its own codec, composed into one document.

In development the UI runs on Vite's dev server (``http://localhost:5173``) and proxies
``/api/*`` to this app (``http://localhost:8000``), so the browser sees one origin and
no CORS configuration is needed. (Serving a production ``frontend/dist`` build from here
is a deployment concern, deferred until then.)

Which hunt is drawn: the *active document* is a file path that starts empty. The
``PUZZ_GRAPH`` environment variable, if set, seeds the initial active path (a launch
convenience); ``POST /api/document/new`` and ``POST /api/document/open`` switch it at
runtime. With no active path the editor opens on an **empty graph** (and saving is
disabled until a path exists — start one with *New*). Run the backend with::

    python -m uvicorn puzzcombinator.app.server:app --reload
    PUZZ_GRAPH=/path/to/hunt.json python -m uvicorn puzzcombinator.app.server:app --reload

and the UI with ``npm run dev`` in ``frontend/``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast, get_args

from fastapi import FastAPI, HTTPException

from puzzcombinator.artifacts.registry import artifact_from_dict, artifact_to_dict
from puzzcombinator.core.document import DEFAULT_GRAPH_ID, HuntDocument
from puzzcombinator.core.graph import Graph
from puzzcombinator.errors import GraphError, RegistryError, SerializationError
from puzzcombinator.serialization import (
    document_from_dict,
    document_to_dict,
    graph_from_dict,
    graph_to_dict,
)
from puzzcombinator.serialization.schema import (
    KEY_GRAPH,
    KEY_SCHEMA_VERSION,
    KEY_UNPLACED,
    SCHEMA_VERSION,
)
from puzzcombinator.visualization.defaults import resolve_workspace
from puzzcombinator.visualization.layout import Orientation, layered_layout
from puzzcombinator.visualization.workspace import workspace_from_dict, workspace_to_dict

#: The top-level key under which the UI channel is composed alongside ``graphs``. The
#: composition is the app layer's job, so the joining key is owned here — not in either
#: channel's codec.
KEY_WORKSPACE = "workspace"

#: The layout orientations the arrange endpoint accepts — derived from the ``Orientation``
#: Literal itself, so there is one source of truth for the allowed values.
_ORIENTATIONS: frozenset[str] = frozenset(get_args(Orientation))


#: The active document path. ``None`` means "no document yet" — fall back to the
#: ``PUZZ_GRAPH`` env var (the launch-time seed). New/Open set this to switch documents at
#: runtime; once set, it takes precedence over the env var.
_active_path: str | None = None


def _graph_path() -> str | None:
    """The active document path: the runtime override, else the ``PUZZ_GRAPH`` env seed."""
    return _active_path if _active_path is not None else os.environ.get("PUZZ_GRAPH")


def _load_raw() -> dict[str, Any] | None:
    """The raw saved document (both channels), or ``None`` when there is nothing to load.

    ``None`` covers both "no active path" and "the active path has no file yet" — a freshly
    *New*-ed document loads empty until its first save creates the file.
    """
    path = _graph_path()
    if path and Path(path).exists():
        data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        return data
    return None


app = FastAPI(title="puzzcombinator editor")


@app.get("/api/graph")
def get_graph() -> dict[str, Any]:
    """The drawn graph's envelope + its loose-artifact pool + a position-resolved workspace.

    ``unplaced`` is the drawn graph's scratch pool. The document keys pools by graph id; the
    API is single-graph, so we send the main graph's pool as a flat list. An empty document
    has none.
    """
    raw = _load_raw()
    doc = None if raw is None else document_from_dict(raw)
    graph = Graph(nodes={}, edges={}) if doc is None else doc.main
    pool = () if doc is None else doc.unplaced.get(DEFAULT_GRAPH_ID, ())
    stored = (
        workspace_from_dict(raw[KEY_WORKSPACE])
        if raw is not None and KEY_WORKSPACE in raw
        else None
    )
    workspace = resolve_workspace(stored, {DEFAULT_GRAPH_ID: graph})
    # Compose the channels as explicit siblings — that symmetry is the point.
    return {
        KEY_SCHEMA_VERSION: SCHEMA_VERSION,
        KEY_GRAPH: graph_to_dict(graph)[KEY_GRAPH],
        KEY_UNPLACED: [artifact_to_dict(a) for a in pool],
        KEY_WORKSPACE: workspace_to_dict(workspace),
    }


def _write_document(path: str, body: dict[str, Any]) -> None:
    """Compose a ``{graph, unplaced, workspace}`` body into one document and write it to ``path``.

    The ``graph`` block (``{nodes, edges}``) is reconstructed through the serialization layer
    (which validates structure and rebuilds artifacts via the registry); ``unplaced`` is the
    graph's loose-artifact pool (rebuilt the same way); the ``workspace`` block round-trips
    through its own codec so what is stored is always loadable. Raises 422 on an invalid body.
    Shared by *Save* (to the active path) and *Save As* (to a new path).
    """
    try:
        graph = graph_from_dict({KEY_SCHEMA_VERSION: SCHEMA_VERSION, KEY_GRAPH: body[KEY_GRAPH]})
        pool = tuple(artifact_from_dict(a) for a in body.get(KEY_UNPLACED, []))
        workspace = workspace_from_dict(body[KEY_WORKSPACE])
    except (GraphError, SerializationError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid save body: {exc}") from exc

    # The API's single graph maps to the document's main graph; its pool is keyed there by id
    # (omitted entirely when empty, to keep the file clean). document_to_dict emits both.
    doc = HuntDocument(
        graphs={DEFAULT_GRAPH_ID: graph},
        unplaced={DEFAULT_GRAPH_ID: pool} if pool else {},
    )
    document = {**document_to_dict(doc), KEY_WORKSPACE: workspace_to_dict(workspace)}
    Path(path).write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")


@app.put("/api/graph")
def save_graph(body: dict[str, Any]) -> dict[str, Any]:
    """Persist an edited ``{graph, unplaced, workspace}`` body to the active document file.

    Returns 409 with no active document (nowhere to write — start one with *New* or *Save As*)
    and 422 on an invalid body.
    """
    path = _graph_path()
    if not path:
        raise HTTPException(status_code=409, detail="no active document: use New to start one")
    _write_document(path, body)
    return {"saved": True}


def _require_path(body: dict[str, Any]) -> str:
    """Pull a non-empty ``path`` out of a request body, or 422."""
    path = body.get("path")
    if not isinstance(path, str) or not path.strip():
        raise HTTPException(status_code=422, detail="missing 'path'")
    return path


@app.post("/api/document/new")
def new_document(body: dict[str, Any]) -> dict[str, Any]:
    """Start a fresh empty document at ``{path}`` and switch the editor onto it.

    Writes an empty :class:`HuntDocument` to the path (so the file is immediately a valid,
    loadable document) and makes it the active document. Refuses (409) if the file already
    exists — use *Open* for existing files — so a stray *New* can't clobber a hunt.
    """
    global _active_path
    path = _require_path(body)
    if Path(path).exists():
        raise HTTPException(status_code=409, detail=f"file exists; use Open: {path}")
    document = document_to_dict(HuntDocument.single(Graph(nodes={}, edges={})))
    Path(path).write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    _active_path = path
    return {"path": path}


@app.post("/api/document/open")
def open_document(body: dict[str, Any]) -> dict[str, Any]:
    """Drop the current document and switch the editor onto the file at ``{path}``.

    Validates the file up front — 404 if missing, 422 if it does not parse as a document —
    so we never switch the active document onto a broken file. The frontend reloads after a
    success, which re-issues ``GET /api/graph`` against the now-active path.
    """
    global _active_path
    path = _require_path(body)
    if not Path(path).exists():
        raise HTTPException(status_code=404, detail=f"no such file: {path}")
    try:
        document_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
    except (GraphError, SerializationError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"not a valid hunt document: {exc}") from exc
    _active_path = path
    return {"path": path}


@app.post("/api/document/save-as")
def save_document_as(body: dict[str, Any]) -> dict[str, Any]:
    """Save the current ``{graph, unplaced, workspace}`` to a *new* file and switch onto it.

    The "name this untitled document" action: it writes what is on the canvas (not an empty
    document) to ``{path}`` and makes it the active document, so the next *Save* lands there.
    Refuses (409) if the file already exists — like *New* — so it can't clobber a hunt; 422 on
    a missing path or an invalid body.
    """
    global _active_path
    path = _require_path(body)
    if Path(path).exists():
        raise HTTPException(status_code=409, detail=f"file exists; use Open: {path}")
    _write_document(path, body)
    _active_path = path
    return {"saved": True, "path": path}


@app.post("/api/render")
def render_artifact(body: dict[str, Any]) -> dict[str, Any]:
    """Render a single artifact envelope to its HTML/SVG fragment, for live preview.

    Stateless and file-independent, like :func:`arrange`: the editor sends one artifact's
    ``{type, id, name, payload}`` envelope (a piece of its live, possibly-unsaved graph) and
    gets back the :class:`~puzzcombinator.rendering.fragment.RenderFragment` fields —
    ``{markup, kind, styles}`` — to drop into a sandboxed preview. Rendering stays the
    backend's single source of truth (the artifact's pure ``render``); the frontend never
    learns a concrete artifact's markup. Artifact-agnostic: the envelope flows through the
    registry, so a new artifact type previews with no edit here. Returns 422 on an unknown
    type or a malformed envelope/payload.
    """
    try:
        fragment = artifact_from_dict(body).render()
    except (RegistryError, SerializationError, GraphError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"cannot render: {exc}") from exc
    return {"markup": fragment.markup, "kind": fragment.kind, "styles": fragment.styles}


@app.post("/api/arrange")
def arrange(body: dict[str, Any]) -> dict[str, Any]:
    """Auto-layout the *live* graph and return fresh positions for the editor to apply.

    Stateless and file-independent: the editor sends its current (possibly unsaved)
    ``graph`` block plus an ``orientation`` (default ``"horizontal"``), and gets back a
    ``{node_id: {x, y}}`` map shaped exactly like a view's ``positions`` — so the browser
    applies it directly without touching the saved file. Layout stays the single tested
    source of truth in :func:`~puzzcombinator.visualization.layout.layered_layout`.
    Returns 422 on an invalid graph (e.g. a cycle) or an unknown orientation.
    """
    orientation = body.get("orientation", "horizontal")
    if orientation not in _ORIENTATIONS:
        raise HTTPException(status_code=422, detail=f"unknown orientation: {orientation!r}")
    try:
        graph = graph_from_dict({KEY_SCHEMA_VERSION: SCHEMA_VERSION, KEY_GRAPH: body[KEY_GRAPH]})
        positions = layered_layout(graph, cast(Orientation, orientation))
    except (GraphError, SerializationError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"cannot arrange: {exc}") from exc
    return {"positions": {nid: {"x": p.x, "y": p.y} for nid, p in positions.items()}}
