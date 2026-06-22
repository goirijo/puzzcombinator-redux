# The visualization layer

`visualization/` is the Python home for **how a hunt is drawn** — the deliberate
counterweight to the data layers. `core`/`artifacts`/`puzzles`/`serialization`/
`rendering` own the hunt's *source of truth* and know nothing about drawing; everything
about *representation* — node coordinates, the editor's views and tabs — lives here, in
its own clearly-labeled package. The split is meant to be visible in the file tree: data
there, visualization here.

It depends **downward on `core` only** (the layout query needs a graph) and on nothing
sideways or up. `core`/`serialization` never import it and never learn it exists; the
`app` layer sits above and composes it with `serialization` into a saved file.

## Two modules

### `layout.py` — auto-arrangement (pure)

`layered_layout(graph) -> {node_id: NodePosition}`. A standard layered-DAG layout: a
node's **layer** (column / x) is the longest path of edges reaching it from any start
node, computed by walking `core.ordering.topological_order` so every predecessor's layer
is already known; its **row** (y) is its slot among nodes sharing that layer.
`NodePosition(layer, row, x, y)` carries both the grid indices and pixel coordinates;
pixel geometry (`COLUMN_WIDTH`, `ROW_HEIGHT`, `MARGIN_X/Y`) lives here. No I/O — graph in,
positions out — which is why it is the most-trusted, most-tested piece. It is the
fallback an editor uses for any node a designer has **not** placed by hand.

### `workspace.py` — the workspace channel (the editor's UI state)

The **second persisted channel**, alongside hunt data. The mental model is **vim**:

- A **view** is a *buffer* — a created, persistent arrangement of one graph: node
  `positions` and a `title`. It exists whether or not anything displays it.
- A **tab** is a *window* — a display slot referencing a view by id, carrying its own
  `viewport` (pan/zoom). Several tabs may show one view; closing a tab doesn't destroy
  the view.
- A **`Workspace`** is the whole channel: `{ views, tabs, active_tab }`.

**Channel independence is the invariant.** `workspace.py` references nodes by **opaque
id**, never imports the hunt-data model, and has its **own self-contained codec**
(`workspace_to_dict`/`from_dict`, `workspace_to_json`/`from_json`). So a workspace
serializes and unit-tests entirely on its own — a graph-free workspace JSON is a valid
document. Lose the whole workspace and you lose only *visualizations*, never hunt data.
On disk it is one top-level `workspace` entry beside `graphs` (the `app` layer stitches
them), but because the codecs are independent it *could* be two files.

The on-disk shape:

```jsonc
"workspace": {
  "views": { "<view_id>": { "graph": "<graph_id>", "title": "<name>",
                            "positions": { "<node_id>": {"x": 0, "y": 0} } } },
  "tabs":  [ { "id": "<tab_id>", "view": "<view_id>",
               "viewport": {"x": 0, "y": 0, "zoom": 1} } ],
  "active_tab": "<tab_id>"
}
```

## Tests

In `tests/visualization/`:
- **`test_layout.py`** — the pure layout function (linear / branch+merge / disconnected /
  empty).
- **`test_workspace.py`** — workspace round-trips (dict + JSON), and a hand-written
  **graph-free** JSON document, proving the standalone "could be two files" shape.

## Rules (don't violate without discussing)

- **Reads `core`, never the reverse.** Layout may take a `Graph`; the data layers must
  stay ignorant of this package.
- **No hunt data in the workspace channel.** Nodes are referenced by opaque id only; if
  you find yourself importing `Artifact`/`Graph` into `workspace.py`, the seam is wrong.
- **The model lives here, not in the frontend's image.** The React app (`frontend/`) has
  its own TypeScript types; this is the Python persistence representation, kept in sync
  through the `app` layer's JSON contract — not by sharing code.
