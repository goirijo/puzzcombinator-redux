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
- **Persist UI state, not just the graph.** The saved file should carry two parts: the
  graph, and the UI/canvas state (node placements, later collapsed/view overrides). This
  is the `app/canvas.py` sidecar — defined but not yet persisted. (Confirmed previously
  planned.)
- **Browser file-picker** to replace the `PUZZ_GRAPH` env var.
- **Generate a binder from the editor.** Unblocked now that the binder layer is real;
  wire the editor to the existing `Binder.of_artifacts` / `Binder.of_nodes`.

## Canvas & nodes

- **Edge directionality.** Today handles attach only left (target) / right (source).
  Consider allowing top/bottom attachment.
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

## Later layers (defer unless asked)

- **More puzzle types.**
- **GUI authoring layer** (beyond the editor shell).
- **Tracking / monitoring layer** (layer 4) — the *only* place answer-checking would ever
  live.
- **Per-puzzle parameter metadata** in the serialized format (still open).
