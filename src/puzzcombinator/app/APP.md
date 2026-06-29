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

### Two channels: hunt data vs. workspace state

The editor deals with **two separate kinds of persisted data**, never mixed, and `app`
is the layer that **composes them into one saved file**:

- **Hunt data** — the treasure hunt itself (graphs, nodes, edges, artifacts). The
  source of truth, owned by `serialization/` + `core.document.HuntDocument`. A node
  carries **no** position.
- **Workspace state** — purely *where/how* a hunt is drawn (node positions, which views
  and tabs are open). It lives **outside this layer**, in
  [`visualization/workspace.py`](../visualization/VISUALIZATION.md) (`Workspace` / `View`
  / `Tab` / `Position` / `Viewport`), with its own self-contained codec that references
  nodes by opaque id and never touches the hunt-data model. A hunt is fully valid with no
  workspace state — the editor falls back to the auto-arranged `layered_layout` (also in
  `visualization/`).

`app` keeps the channels independent (it hands `graphs` to `serialization` and the
`workspace` blob to `visualization`, then stitches the two dicts into one file); the
codecs never see each other, so the file *could* be split in two.

## The one principle that shapes everything here

**Put the hard logic in Python where it is pure and unit-testable; keep the browser
side thin.** The only non-trivial computation — deciding where each node is drawn —
lives in a pure Python function with real tests. The browser does fetching and
drawing, nothing clever. This is also what keeps a future swap of the frontend (e.g.
to a node-editor library like React Flow) cheap: the Python backend and the JSON seam
don't change, only the view does.

## Backend (Python)

One small module. It depends downward (on `core` + `serialization` + `visualization`) and
never reaches sideways or up. The **drawing logic itself is not here** — `layered_layout`
and the workspace model live one layer down in
[`visualization/`](../visualization/VISUALIZATION.md); `app` only imports and composes them.

- **`server.py` — the thin FastAPI app, and the channel-composition layer.** Almost
  logic-free except for stitching the two channels together.
  - `GET /api/graph` returns the drawn graph's envelope plus a `workspace` block — the
    stored views/tabs, or a synthesized default — with every node's position resolved
    (`visualization.defaults.resolve_workspace`). See the response shape below.
  - `PUT /api/graph` takes a `{graph, workspace}` body: the `graph` block reconstructs
    through `graph_from_dict` (which validates structure + rebuilds artifacts via the
    registry); the `workspace` round-trips through its own codec; the two compose into
    one `HuntDocument`-shaped file with a sibling `workspace` key. Returns 409 when there
    is no active document (nowhere to write — start one with *New*) and 422 on an invalid body.
  - `POST /api/document/new` takes a `{path}` body, writes an **empty** document to that
    path and switches the active document onto it. 422 on a missing path; **409 if the file
    already exists** (use *Open* for existing files, so a stray *New* can't clobber a hunt).
  - `POST /api/document/open` takes a `{path}` body and switches the active document onto an
    existing file. Validates it up front — 404 if missing, 422 if it does not parse as a
    document — so the active document never points at a broken file.
  - `POST /api/arrange` takes a `{graph, orientation}` body and returns a
    `{positions: {node_id: {x, y}}}` map from `visualization.layout.layered_layout` —
    auto-layout for the *live* (possibly unsaved) graph, so the editor can re-arrange
    without writing the file. `orientation` is `"horizontal"` (default) or `"vertical"`;
    422 on an unknown orientation or an un-layoutable graph (e.g. a cycle).
  - `POST /api/render` takes one artifact's `{type, id, name, payload}` envelope and returns
    its rendered fragment `{markup, kind, styles}` — the artifact's pure `render()`, run
    through the registry so it is artifact-agnostic (a new type previews with no edit here).
    Stateless and file-independent like `arrange`; the editor uses it for live artifact
    preview. 422 on an unknown type or a malformed payload.
  - The **active document** is a file path that starts empty. `PUZZ_GRAPH`, if set, seeds
    the initial path (a launch convenience); New/Open switch it at runtime and take
    precedence. With no active path — and before a *New*-ed file's first save — `GET` draws
    an **empty graph**, and saving is disabled (nowhere to write).
  - The app is **API-only** — it no longer serves the page. In development the React/Vite
    UI runs on `http://localhost:5173` and **proxies** `/api/*` to this app on `:8000`, so
    the browser still sees one origin and **no CORS config is needed**. (Serving a built
    `frontend/dist` from FastAPI is a deployment concern, deferred.)

### The API response shape (the seam the browser reads)

`GET /api/graph` returns the two channels as explicit siblings:

```jsonc
{
  "schema_version": "3",
  "graph": {                                                 // hunt data (one graph)
    "nodes": [{ "id", "action", "label", "notes" }],
    "edges": [{ "id", "source", "target", "content": [{ "type", "id", "name", "payload" }] }]
  },
  "unplaced": [{ "type", "id", "name", "payload" }],         // hunt data: the loose pool
  "workspace": {                                             // UI channel (visualization)
    "views": { "<view_id>": { "graph", "title", "positions": { "<node_id>": {"x","y"} },
                              "show_unplaced": true } },
    "tabs":  [ { "id", "view", "viewport": {"x","y","zoom"} } ],
    "active_tab": "<tab_id>"
  }
}
```

`graph` is the graph-level envelope's body (`graph_to_dict(graph)[KEY_GRAPH]`), not the
document map — the browser draws one graph. `unplaced` is that graph's loose-artifact pool
(`HuntDocument.unplaced`) as a **flat list** on the wire, even though on disk the document
keys it per graph id — because `server` is single-graph. `PUT /api/graph` sends the same
channels back: `{ "graph": { nodes, edges }, "unplaced": [ … ], "workspace": { … } }`, and
`server` rebuilds a `HuntDocument` carrying the pool. The browser never sees `Graph`/`Puzzle`
objects — only this JSON. That decoupling is what lets the view be replaced without touching
the model. The saved **file** is the document form (`{schema_version, graphs, unplaced,
workspace}`); `server` is the one place that maps between the single-graph wire shape and the
document-on-disk shape.

## The frontend

The React/Vite/TypeScript UI that consumes this seam lives in
**[`frontend/`](../../../frontend/FRONTEND.md)** and is documented there — its file map, the
pure-modules-vs-one-stateful-file structure, the `DTO`/`Hunt` naming + styling conventions,
and how to add a feature. From the backend's side all that matters is the contract above: the
UI `GET`s the `{graph, workspace}` pair and `PUT`s an edited `{graph, workspace}` back.

### Data flow in one line

`server` loads both channels from the active document file → graph via `serialization`,
workspace via `visualization` (default-synthesized + position-resolved if absent) → JSON
over `GET /api/graph` → the frontend draws it; on Save the frontend `PUT`s both channels
back and `server` composes them into the active document.

## Running the backend

```bash
pip install -e ".[gui]"                                   # fastapi + uvicorn
python -m uvicorn puzzcombinator.app.server:app --reload  # API on http://127.0.0.1:8000
# seed the initial document (else the editor opens empty; New/Open switch it at runtime):
PUZZ_GRAPH=/path/to/hunt.json python -m uvicorn puzzcombinator.app.server:app --reload
```

Use `python -m uvicorn …` (not bare `uvicorn`) so it works regardless of `PATH`. This serves
the **API only**; start the UI separately (`npm run dev` in `frontend/` — see
[`frontend/FRONTEND.md`](../../../frontend/FRONTEND.md)) and open **http://127.0.0.1:5173**,
which proxies `/api` to this app.

## Tests

In `tests/app/`:
- **`test_server.py`** — the real routes via FastAPI's in-process `TestClient` (GET
  response shape, layout coordinates, `PUZZ_GRAPH` seed, New/Open document switching, and
  the `PUT` save→reload round-trip + its no-active-document rejection).

The pure layout + workspace round-trip tests moved with their code, to
`tests/visualization/` (see [`VISUALIZATION.md`](../visualization/VISUALIZATION.md)).

Frontend testing is covered in [`frontend/FRONTEND.md`](../../../frontend/FRONTEND.md).

## Layering rules (don't violate without discussing)

- **App is the top layer.** It imports `core`/`serialization`/`visualization` and changes
  none of them. If a need pushes you to edit a lower layer, that's a signal to rethink the
  seam, not to reach down.
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
- **Then:** persist manual drag positions to the workspace channel (shape in
  `visualization/workspace.py`; positions override `layered_layout`), drag-to-connect,
  create/delete nodes.
- **Later (deferred):** an artifact/puzzle palette, editing artifact payloads, rendering
  artifact HTML in-panel, generating a binder from the editor, multiple graphs/views (the
  format already anticipates both).

## UX ideas & wishlist (a living backlog)

A running record of features and refinements worth considering as the editor evolves.
**Not an immediate to-do list** — the "Status & roadmap" section above is what's
actually planned. Add to this freely; promote an item up to the roadmap when it's
time to build it. Rough grouping, not priority order.

- **Canvas & layout:** pan/zoom, fit-to-screen / reset-view, manual node dragging with
  positions persisted to the workspace channel (shape in `visualization/workspace.py`;
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
