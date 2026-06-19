# The app (editor) layer

The **app** layer is a *new top layer*: a web GUI for visually authoring a hunt. It
is the GUI half of the rule from `CLAUDE.md` — **"GUI = producer, binder = consumer,
model + serialization = the seam."** It sits **above** everything else and is a pure
**consumer/producer of the serialization seam**: it reads a graph via `graph_to_dict`
and writes a whole hunt back via `to_json` (a saved hunt file is a `HuntDocument`). It
**never modifies** `core/`, `serialization/`, `rendering/`, `puzzles/`, or
`artifacts/` — it only imports them.

> Started 2026-06-13, built bottom-up like the rest of the library. The frontend was
> **migrated from vanilla SVG to React + React Flow (Vite, TypeScript) on 2026-06-18**;
> the Python backend + JSON seam were unchanged. The current React app is read-only
> visualization (drag / pan / zoom); selection, editing, and save are being re-ported.
> See the "Status & roadmap" section at the end.
>
> **This doc covers the Python backend and the seam it serves.** The React frontend's code
> — file map, conventions, and how to add a feature — lives in its own doc at
> [`../../../frontend/FRONTEND.md`](../../../frontend/FRONTEND.md).

### Two channels: hunt data vs. canvas state

The editor deals with **two separate kinds of persisted data**, never mixed:

- **Hunt data** — the treasure hunt itself (graphs, nodes, edges, artifacts). The
  source of truth, owned by `serialization/` + `core.document.HuntDocument`. A node
  carries **no** position.
- **Canvas state** — purely *where/how* a hunt is drawn (node positions, which view,
  collapsed nodes). Its shape lives in **`app/canvas.py`** (`CanvasDocument` / `View` /
  `Position`) as a *separate optional sidecar*, deliberately kept out of `HuntDocument`
  so it can never affect hunt-data round-trip equality. A hunt is fully valid with no
  canvas state — the editor falls back to the auto-arranged `layered_layout`. **Status:
  shape only** — nothing moves nodes yet, so positions aren't persisted; that arrives
  with the canvas-interaction (React Flow) milestone.

## The one principle that shapes everything here

**Put the hard logic in Python where it is pure and unit-testable; keep the browser
side thin.** The only non-trivial computation — deciding where each node is drawn —
lives in a pure Python function with real tests. The browser does fetching and
drawing, nothing clever. This is also what keeps a future swap of the frontend (e.g.
to a node-editor library like React Flow) cheap: the Python backend and the JSON seam
don't change, only the view does.

## Backend (Python)

Three small modules. They depend downward (on `core` + `serialization`, and on
`puzzles`/`artifacts` only to build the demo) and never reach sideways or up.

- **`layout.py` — the pure, testable heart.** `layered_layout(graph) -> {node_id:
  NodePosition}`. A standard layered-DAG layout: a node's **layer** (column / x) is
  the longest path of edges reaching it from any start node, computed by walking
  `core.ordering.topological_order` so every predecessor's layer is already known;
  its **row** (y) is its slot among nodes sharing that layer, in topological order.
  `NodePosition(layer, row, x, y)` carries both the grid indices and the pixel
  coordinates. Pixel geometry (`COLUMN_WIDTH`, `ROW_HEIGHT`, `MARGIN_X/Y`) lives here,
  not in the browser, so positions are fully determined server-side. No I/O, no
  FastAPI, no SVG — just graph in, positions out.

- **`server.py` — the thin FastAPI app.** Deliberately almost logic-free.
  - `GET /api/graph` returns the drawn graph's own `graph_to_dict(graph)` envelope with
    a `"layout"` map (from `layered_layout`) bolted on — see the response shape below.
  - `PUT /api/graph` takes the edited `{nodes, edges}` block, reconstructs it through
    `graph_from_dict` (which validates structure + rebuilds artifacts via the registry),
    and writes it to the `PUZZ_GRAPH` file as a `HuntDocument` (`to_json`). Returns 409
    in demo mode (no file to save to) and 422 on an invalid graph.
  - Which graph: the `PUZZ_GRAPH` environment variable, if set, points at a serialized
    hunt JSON file — a hunt document — loaded via `serialization.from_json` and drawn as
    its `.main` graph; otherwise the built-in demo graph is used (and saving is
    disabled — nowhere to write).
  - The app is **API-only** — it no longer serves the page. In development the React/Vite
    UI runs on `http://localhost:5173` and **proxies** `/api/*` to this app on `:8000`, so
    the browser still sees one origin and **no CORS config is needed**. (Serving a built
    `frontend/dist` from FastAPI is a deployment concern, deferred.)

- **`demo.py` — a built-in sample hunt.** `build_demo_graph()` assembles a small
  branch-and-merge hunt with `GraphBuilder`, so the page always has something
  non-trivial to draw with zero setup and no dependency on the (still-stale) example
  scripts or binder.

### The API response shape (the seam the browser reads)

`GET /api/graph` returns the single drawn graph's envelope with one extra key:

```jsonc
{
  "schema_version": "3",
  "graph": {
    "nodes": [{ "id", "action", "label", "notes" }],
    "edges": [{ "id", "source", "target", "content": [{ "type", "id", "name", "payload" }] }]
  },
  "layout": { "<node_id>": { "layer", "row", "x", "y" } }   // added by the server
}
```

This is the graph-level envelope (`graph_to_dict`), not the document envelope — the
browser has no graph-selection concept yet, so it gets the one graph it draws. `PUT
/api/graph` sends just the `graph` block (`{nodes, edges}`) back. The browser never sees
`Graph`/`Puzzle` objects — only this JSON. That decoupling is what lets the view be
replaced without touching the model.

## The frontend

The React/Vite/TypeScript UI that consumes this seam lives in
**[`frontend/`](../../../frontend/FRONTEND.md)** and is documented there — its file map, the
pure-modules-vs-one-stateful-file structure, the `DTO`/`Hunt` naming + styling conventions,
and how to add a feature. From the backend's side all that matters is the contract above: the
UI `GET`s the graph envelope and `PUT`s an edited `{nodes, edges}` block back.

### Data flow in one line

`server` builds/loads a `Graph` → `graph_to_dict` + `layered_layout` → JSON over `GET
/api/graph` → the frontend draws it; on Save the frontend `PUT`s the edited block back and
`server` writes it to the `PUZZ_GRAPH` file as a `HuntDocument`.

## Running the backend

```bash
pip install -e ".[gui]"                                   # fastapi + uvicorn
python -m uvicorn puzzcombinator.app.server:app --reload  # API on http://127.0.0.1:8000
# draw a real hunt instead of the demo:
PUZZ_GRAPH=/path/to/hunt.json python -m uvicorn puzzcombinator.app.server:app --reload
```

Use `python -m uvicorn …` (not bare `uvicorn`) so it works regardless of `PATH`. This serves
the **API only**; start the UI separately (`npm run dev` in `frontend/` — see
[`frontend/FRONTEND.md`](../../../frontend/FRONTEND.md)) and open **http://127.0.0.1:5173**,
which proxies `/api` to this app.

## Tests

In `tests/app/`:
- **`test_layout.py`** — the pure layout function (linear / branch+merge / disconnected
  / empty). This is the component we trust most, because it has no I/O.
- **`test_server.py`** — the real routes via FastAPI's in-process `TestClient` (GET
  response shape, layout coordinates, `PUZZ_GRAPH` override, and the `PUT` save→reload
  round-trip + its demo-mode rejection).

Frontend testing is covered in [`frontend/FRONTEND.md`](../../../frontend/FRONTEND.md).

## Layering rules (don't violate without discussing)

- **App is the top layer.** It imports `core`/`serialization` (and `puzzles`/`artifacts`
  for the demo) and changes none of them. If a need pushes you to edit a lower layer,
  that's a signal to rethink the seam, not to reach down.
- **The JSON seam is the contract.** Anything the browser needs goes through the
  `GET`/`PUT /api/graph` shapes. Don't invent a side channel.
- **Hard logic in Python, thin browser.** New computed structure (layout, validation,
  ordering hints) belongs in a pure Python function with a test — not in TS.
- **Frontend layering** — the UI's own rules (pure modules vs. one stateful file, no inline
  styles, `DTO`/`Hunt` naming) live in [`frontend/FRONTEND.md`](../../../frontend/FRONTEND.md).

## Adding to the backend

- **A new computed structure the UI needs** (validation, an ordering hint, a richer layout):
  write it as a **pure function with a test** — like `layout.py` — and expose it through the
  existing `GET /api/graph` response, not a side channel.
- **A new endpoint** (list hunts, a binder export, …): add a route to `server.py`, but
  reconstruct/serialize through the `serialization` layer (never hand-roll JSON) and keep the
  route thin — the real work belongs in a tested module below it.
- **Touch no lower layer.** If a change pushes you to edit `core`/`serialization`/`rendering`,
  that's a signal to rethink the seam, not to reach down.

## Status & roadmap

- **Done (vanilla, pre-migration):** click-to-select + node inspector, in-browser editing
  of `label`/`action`/`notes`, and persistence via `PUT /api/graph` + a Save control. The
  backend for all of this still exists; only the *UI* for it was dropped in the React swap
  and is being re-ported.
- **Done (React):** read-only graph visualization (server-laid-out nodes, labeled arrow
  edges, start/end coloring) with React Flow's built-in **drag / pan / zoom**.
- **Next:** re-port the editing UI in React — click-to-select + an inspector panel for
  `label`/`action`/`notes`, then wire Save back to the existing `PUT /api/graph`.
- **Then:** persist manual drag positions to the canvas/views sidecar (shape defined in
  `canvas.py`; positions override `layered_layout`), drag-to-connect, create/delete nodes.
- **Later (deferred):** an artifact/puzzle palette, editing artifact payloads, rendering
  artifact HTML in-panel, generating a binder from the editor, multiple graphs/views (the
  format already anticipates both).

## UX ideas & wishlist (a living backlog)

A running record of features and refinements worth considering as the editor evolves.
**Not an immediate to-do list** — the "Status & roadmap" section above is what's
actually planned. Add to this freely; promote an item up to the roadmap when it's
time to build it. Rough grouping, not priority order.

- **Canvas & layout:** pan/zoom, fit-to-screen / reset-view, manual node dragging with
  positions persisted to the canvas/views sidecar (shape already defined in `canvas.py`;
  positions override `layered_layout`, which doubles as the auto-relayout/arrange
  button), a minimap for large hunts, collapse/expand a subgraph, geo-coordinates +
  arrange-on-a-map (real-world hunt data, distinct from canvas x/y), multiple named
  views of one graph.
- **Graph editing:** create / delete / duplicate nodes, draw connections by dragging
  between nodes, multi-select + bulk actions, undo/redo, keyboard shortcuts, snap-to-grid.
- **Artifacts:** a palette of artifact + puzzle types to drag onto edges, inline
  editing of artifact payloads, a live preview of an artifact's rendered output,
  visualizing/handling the same artifact reused across multiple edges, scattering a
  puzzle's pieces across edges from the UI.
- **Feedback & correctness:** surface model validation live (cycles, dangling edges,
  duplicate ids within an edge), an unsaved-changes / dirty indicator (done), show the
  topological solve order, highlight start/end nodes (done) and any unreachable nodes.
- **Hunt management:** new / open / save-as multiple hunt files, recent-files list,
  import/export JSON (and YAML), and — once the binder lands — generate the printable
  player pages + answer key from the editor.
- **Quality of life:** search/filter nodes by action or label, node notes shown on the
  canvas, theming/dark mode, autosave.
- **Theming (user request):** a dedicated tab/menu for switching themes — at least
  light/dark, plus the ability to load your own custom theme. (The CSS already centralizes
  colors in `:root` variables in `style.css`, so a theme is essentially a swappable set of
  those variables — a good foundation for this.)
- **Long-term (hosting):** the service goal — accounts, shareable hunt links,
  real-time multi-author editing, a gallery of templates.
