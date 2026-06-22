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

Which hunt is drawn: set the ``PUZZ_GRAPH`` environment variable to a serialized hunt
JSON file to draw — and save — a real hunt; otherwise the built-in demo graph is used
(and saving is disabled, since there is nowhere to write). Run the backend with::

    python -m uvicorn puzzcombinator.app.server:app --reload
    PUZZ_GRAPH=/path/to/hunt.json python -m uvicorn puzzcombinator.app.server:app --reload

and the UI with ``npm run dev`` in ``frontend/``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from puzzcombinator.app.demo import build_demo_graph
from puzzcombinator.core.document import DEFAULT_GRAPH_ID, HuntDocument
from puzzcombinator.errors import GraphError, SerializationError
from puzzcombinator.serialization import (
    document_from_dict,
    document_to_dict,
    graph_from_dict,
    graph_to_dict,
)
from puzzcombinator.serialization.schema import (
    KEY_GRAPH,
    KEY_GRAPHS,
    KEY_SCHEMA_VERSION,
    SCHEMA_VERSION,
)
from puzzcombinator.visualization.defaults import resolve_workspace
from puzzcombinator.visualization.workspace import workspace_from_dict, workspace_to_dict

#: The top-level key under which the UI channel is composed alongside ``graphs``. The
#: composition is the app layer's job, so the joining key is owned here — not in either
#: channel's codec.
KEY_WORKSPACE = "workspace"


def _graph_path() -> str | None:
    """The ``PUZZ_GRAPH`` file path, or ``None`` in demo mode."""
    return os.environ.get("PUZZ_GRAPH")


def _load_raw() -> dict[str, Any] | None:
    """The raw saved document (both channels), or ``None`` in demo mode."""
    path = _graph_path()
    if path:
        data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        return data
    return None


app = FastAPI(title="puzzcombinator editor")


@app.get("/api/graph")
def get_graph() -> dict[str, Any]:
    """The drawn graph's envelope + a workspace with every node's position resolved."""
    raw = _load_raw()
    graph = build_demo_graph() if raw is None else document_from_dict(raw).main
    stored = (
        workspace_from_dict(raw[KEY_WORKSPACE])
        if raw is not None and KEY_WORKSPACE in raw
        else None
    )
    workspace = resolve_workspace(stored, {DEFAULT_GRAPH_ID: graph})
    # Compose the two channels as explicit siblings — that symmetry is the point.
    return {
        KEY_SCHEMA_VERSION: SCHEMA_VERSION,
        KEY_GRAPH: graph_to_dict(graph)[KEY_GRAPH],
        KEY_WORKSPACE: workspace_to_dict(workspace),
    }


@app.put("/api/graph")
def save_graph(body: dict[str, Any]) -> dict[str, Any]:
    """Persist an edited ``{graph, workspace}`` body to the ``PUZZ_GRAPH`` file.

    The ``graph`` block (``{nodes, edges}``) is reconstructed through the serialization
    layer (which validates structure and rebuilds artifacts via the registry); the
    ``workspace`` block round-trips through its own codec so what is stored is always
    loadable. The two channels are composed into one document as explicit siblings.
    Returns 409 in demo mode (no file to save to) and 422 on an invalid body.
    """
    path = _graph_path()
    if not path:
        raise HTTPException(
            status_code=409, detail="demo mode: set PUZZ_GRAPH to a file to enable saving"
        )
    try:
        graph = graph_from_dict({KEY_SCHEMA_VERSION: SCHEMA_VERSION, KEY_GRAPH: body[KEY_GRAPH]})
        workspace = workspace_from_dict(body[KEY_WORKSPACE])
    except (GraphError, SerializationError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid save body: {exc}") from exc

    document = {
        KEY_SCHEMA_VERSION: SCHEMA_VERSION,
        KEY_GRAPHS: document_to_dict(HuntDocument.single(graph))[KEY_GRAPHS],
        KEY_WORKSPACE: workspace_to_dict(workspace),
    }
    Path(path).write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"saved": True}
