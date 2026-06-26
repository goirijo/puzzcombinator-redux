# ROADMAP — puzzcombinator

The long-term plan, in the repo so it's visible. This is a **tracking** doc, not a
work queue: items here are ideas and intended directions, **not** commitments to build
now. Nothing here enters development until it's the explicit subject of a prompt — see
the `build-only-whats-asked` rule. New "nice to have" ideas get parked here rather than
coded speculatively.

For *where we are today*, see `CLAUDE.md` ("Current status"). For the architecture these
ideas must respect, see `ARCHITECTURE.md`. The library layers (artifacts → puzzles →
core → rendering) are complete and green; almost everything below is the **GUI editor**,
which is the active frontier.

## Near-term (active frontier — the GUI editor)

- **Canvas interaction.** Node dragging with positions persisted, pan/zoom, and drawing
  connections. The natural point to fully lean on React Flow.
- **Persist UI state, not just the graph.** *(Done.)* The saved file carries two channels —
  the graph, and the workspace (views, tabs, node positions, per-tab viewport). `visualization/`
  owns the workspace model + codec; `app` composes the two into one file. (Vim model: views =
  buffers, tabs = windows.)
- **Per-view / independent move-undo (the deferred undo split).** Node positions ride the
  graph store *during editing*, so (a) moving a node and editing a node share **one** undo
  stack, and (b) that stack's snapshots carry per-view positions while positions are the one
  per-view thing — so undoing after a view switch would clobber the current view with another
  view's snapshot. **Interim fix (shipped):** the undo history is cleared on every view switch
  (`workspaceStore.resetHistory`), scoping undo to "since you arrived at this view" — no
  cross-view corruption, at the cost of undo not surviving a switch (the data itself is never
  lost). **The real fix:** lift positions out of the undoable graph store into the
  `workspaceStore` (per view, with their own history), making React Flow nodes a projection of
  shared hunt-data + active-view positions, and route the undo keybinding by focus (vim-style).
  The persisted format already separates the two channels, so this is additive and **in-memory
  only — no data migration**, not a rewrite. (See the data-flow section of `frontend/FRONTEND.md`.)
- **Browser file-picker** to replace the `PUZZ_GRAPH` env var.
- **Empty project by default.** Today a fresh load synthesizes a demo graph plus a default
  tab/view/auto-layout so there's always something to draw. Once the browser file-picker and
  in-UI graph creation land, drop that: a new project should start **empty** — no demo graph,
  no auto-created tab/view — and the designer builds it up from nothing.
- **Generate a binder from the editor.** Unblocked now that the binder layer is real;
  wire the editor to the existing `Binder.of_artifacts` / `Binder.of_nodes`.

## Canvas & nodes

- **Edge attachment & drawing connections.** *(Floating edges shipped.)* Edges attach to
  whichever node sides face each other, recomputed from live geometry (`edges/FloatingEdge`),
  and re-aim as nodes move — the graph isn't pinned to a shape (see the
  [[graph-no-imposed-shape]] principle). **Interim state:** nodes show four discrete `source`
  handles + `ConnectionMode.Loose` (Viewport). These are only the minimum React Flow needs to
  *render* an edge — a finished edge ignores them and floats — but manual wiring isn't built, so
  the four dots don't connect anything yet. They're left visible as-is (no point polishing an
  interim look). **Decided design for when drawing connections lands:** drop the four dots for a
  *single invisible handle covering the whole node* (React Flow's "Easy Connect" pattern) +
  `ConnectionMode.Loose`, so a designer starts a drag from anywhere on a node and the resulting
  edge floats like every other edge. Part of the near-term **Canvas interaction** milestone.
- **Node creation.** A way to create new nodes (and artifacts — see below) from the UI.
- **Custom node coloring.** Author-chosen colors per node. (Note: an earlier *automatic*
  start/middle/end role-coloring was rejected — coloring should be explicit author intent,
  not a derived, backend-absent property.)
- **Lock nodes by default.** Commands generally lock nodes in place; rearranging happens
  only inside a dedicated command, which also offers layout/distribution options and the
  ability to create new views.
- **Mass select & manipulate.** Once nodes/artifacts can carry extra tagged data, support
  selecting many and editing them together.

## Artifacts on the canvas

- **A canvas representation for artifacts** that can be dragged onto edges. Open design
  question: how to handle an artifact that appears on more than one edge.
- **Artifact creation, two paths.** One rail command → a puzzle/artifact *generator*;
  a separate rail command → make an *individual* artifact.
- **Artifact preview.** Clicking an artifact renders its HTML preview.
- **Grouping artifacts** on the canvas (the model already has `CompositeArtifact`).

## Views & the binder

- **Binder interface.** A good UI for assembling/previewing binders.
- **Canvas as a host for non-graph views.** The canvas already renders different *views*
  of the graph; generalize so it can render other view *types* too — e.g. a binder view —
  not just the graph. (V1 visual hunt-map view and `action`-filtered subgraph views fit
  here.)

## Validation / status

- **Status window** surfacing warnings about a bad authoring state (cycles in the graph,
  disjoint/orphaned nodes, etc.). Authoring-only — still no answer-checking.

## Polish & small enhancements

> **Agent note:** low-stakes cosmetic backlog — skip ahead to the next section unless the
> prompt is specifically about one of these items. Don't spend tokens reading it otherwise.

Non-functional UX niceties — nothing here changes what the editor *can do*, only how
pleasant it is. Low-stakes, pick up opportunistically.

- **Full tab name on hover.** When a tab's title is truncated (many tabs shrink the width,
  or a long view name), reveal the full name on hover. Leaning toward a native `title`
  attribute set only when the label actually overflows (`scrollWidth > clientWidth`,
  measured on the hover the `TabBar` already handles) — full name when truncated, nothing
  when it already fits, no custom-tooltip machinery. A themed tooltip is the heavier
  alternative if the OS one ever feels off.

## Later layers (defer unless asked)

- **More puzzle types.**
- **GUI authoring layer** (beyond the editor shell).
- **Tracking / monitoring layer** (layer 4) — the *only* place answer-checking would ever
  live.
- **Per-puzzle parameter metadata** in the serialized format (still open).
