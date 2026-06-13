"""The FastAPI app: serve the editor page, the graph it draws, and save edits back.

Deliberately thin — every interesting decision lives in :mod:`layout` and the
serialization layer. Three jobs:

* ``GET /api/graph`` returns the drawn graph's own envelope
  (``{schema_version, graph: {nodes, edges}}``) plus a ``layout`` map of node positions.
* ``PUT /api/graph`` writes an edited graph back to the ``PUZZ_GRAPH`` file as a hunt
  document (a saved hunt file is a whole document, even when it holds one graph).
* everything else is served as static files from ``static/`` (the page, JS, CSS).

The page and the API share one origin (``http://localhost:8000``), so the browser's
same-origin rule is satisfied and we need no CORS configuration.

Which graph is drawn: set the ``PUZZ_GRAPH`` environment variable to a serialized
hunt JSON file (as written by ``serialization.to_json``) to draw — and save — a real
hunt; otherwise the built-in demo graph is used (and saving is disabled, since there
is nowhere to write). Run with::

    python -m uvicorn puzzcombinator.app.server:app --reload
    PUZZ_GRAPH=/path/to/hunt.json python -m uvicorn puzzcombinator.app.server:app --reload
"""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from puzzcombinator.app.demo import build_demo_graph
from puzzcombinator.app.layout import layered_layout
from puzzcombinator.core.document import HuntDocument
from puzzcombinator.core.graph import Graph
from puzzcombinator.errors import GraphError, SerializationError
from puzzcombinator.serialization import from_json, graph_from_dict, graph_to_dict, to_json
from puzzcombinator.serialization.schema import KEY_GRAPH, KEY_SCHEMA_VERSION, SCHEMA_VERSION

_STATIC_DIR = Path(__file__).parent / "static"


def _graph_path() -> str | None:
    """The ``PUZZ_GRAPH`` file path, or ``None`` in demo mode."""
    return os.environ.get("PUZZ_GRAPH")


def _load_graph() -> Graph:
    """The graph to draw: the ``PUZZ_GRAPH`` file's main graph if set, else the demo."""
    path = _graph_path()
    if path:
        return from_json(Path(path).read_text(encoding="utf-8")).main
    return build_demo_graph()


app = FastAPI(title="puzzcombinator editor")


@app.get("/api/graph")
def get_graph() -> dict[str, Any]:
    """The drawn graph's envelope + computed node positions, ready for the browser."""
    graph = _load_graph()
    return {
        **graph_to_dict(graph),
        "layout": {nid: asdict(pos) for nid, pos in layered_layout(graph).items()},
    }


@app.put("/api/graph")
def save_graph(graph_block: dict[str, Any]) -> dict[str, Any]:
    """Persist an edited graph (the ``{nodes, edges}`` block) to the ``PUZZ_GRAPH`` file.

    Reconstructs the graph through the serialization layer (which validates structure
    and rebuilds artifact payloads via the registry), then writes it back as a hunt
    document. Returns 409 in demo mode (no file to save to) and 422 on an invalid graph.
    """
    path = _graph_path()
    if not path:
        raise HTTPException(
            status_code=409, detail="demo mode: set PUZZ_GRAPH to a file to enable saving"
        )
    envelope = {KEY_SCHEMA_VERSION: SCHEMA_VERSION, KEY_GRAPH: graph_block}
    try:
        graph = graph_from_dict(envelope)
    except (GraphError, SerializationError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid graph: {exc}") from exc
    Path(path).write_text(to_json(HuntDocument.single(graph)), encoding="utf-8")
    return {"saved": True}


# Mounted last so the API routes above take precedence. ``html=True`` serves
# ``index.html`` at "/".
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
