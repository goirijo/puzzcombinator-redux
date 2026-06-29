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
- **Keyboard-driven command selection.** Beyond the existing global chords (`Ctrl/⌘+S`/`Z`/`Y`,
  in `shell/useKeyboardShortcuts.ts`), let single keys activate rail commands (e.g. `e` → edit) so
  the editor is drivable without the mouse — in keeping with the vim model. **Design (settled, not
  built):** the binding is *data on the command registry* — a `key` field on each `Command` in
  `shell/commands.ts` — not a hardcoded ladder in the hook, so adding a command keeps its one-entry
  plug-in property. Dispatch lives in `useKeyboardShortcuts` (the one keyboard home), reading
  `COMMANDS` → `onSelectCommand(id)`. **The sharp edge:** bare-key mnemonics *must* be
  focus-guarded (ignore when an `input`/`textarea`/`contenteditable` is focused) or typing `e` in a
  node's Label fires the command; chords deliberately are not guarded (`Ctrl+S` should save mid-edit).
  So the two interaction classes stay separate branches in the hook. A later, richer extension —
  vim-style key *sequences* (`g g`, leader keys, modes) — would also live here as a small state
  machine; defer until wanted.
- **Browser file-picker** to replace the `PUZZ_GRAPH` env var. *(Partial:* the SCRATCH command's
  Document section now does **New** (empty doc at a path) and **Open** (switch to an existing file)
  by typing a server-side path; the backend's active document is mutable at runtime and
  `PUZZ_GRAPH` is just its launch-time seed. Still to do: a real picker UI — browse/list files
  rather than type a path — and lifting it out of SCRATCH into the real Save/Load command.*)*
- **In-app document reseed (drop the reload).** New/Open currently switch the backend's active
  document and then do a **full page reload** (`window.location.reload()` in
  `panels/scratch/DocumentSection`), which lets the existing `usePersistence` mount-load reseed
  every store, undo history, and the dirty snapshot for free — minimal, but it flashes. The polish
  is to reseed **in-app**: re-fetch the envelope and call `loadGraph`/`loadWorkspace` +
  `temporal.clear()` directly. The blocker is the dirty snapshot — it lives as React state inside
  `usePersistence`, unreachable from a no-props panel — so this means lifting that snapshot into a
  store (or exposing a shared `loadDocument` action) so a switch can reset "clean" without a reload.
  Do it when New/Open graduate out of SCRATCH into the real Save/Load command.
- **Empty project by default.** *(Partial.)* A fresh load with no active document now starts
  **empty** — the built-in demo graph is gone (`app/demo.py` deleted); the backend serves an empty
  `Graph` and a synthesized default tab/view so the canvas still has somewhere to draw. Remaining:
  once in-UI graph creation is richer, consider dropping even the auto-created tab/view so a new
  project is truly blank and the designer builds it up from nothing.
- **Generate a binder from the editor.** Unblocked now that the binder layer is real;
  wire the editor to the existing `Binder.of_artifacts` / `Binder.of_nodes`.

## Canvas & nodes

- **Edge attachment & drawing connections.** *(Built.)* Edges attach to whichever node sides
  face each other, recomputed from live geometry (`edges/FloatingEdge`), and re-aim as nodes
  move — the graph isn't pinned to a shape (see the [[graph-no-imposed-shape]] principle).
  Connecting works: nodes carry four `source` handles + `ConnectionMode.Loose`, and dragging
  from a handle onto another node fires `onConnect` → `connectNodes` → a fresh floating edge
  (undoable; self-loops ignored; parallel edges allowed). **Deferred refinement:** the four
  side dots stay for now. An earlier "Easy Connect" idea (one invisible handle covering the
  whole node, drag from anywhere) was reconsidered — a full-node handle **conflicts with node
  dragging** (every mousedown would start a connection instead of a move), so it isn't the free
  win it looked like. The likely path is **interaction modes** (next bullet) rather than a
  always-on full-node handle.
- **Canvas interaction modes.** Different rail commands will likely put the canvas in different
  *modes* that change what a drag/click does (e.g. a connect mode where dragging from a node
  body draws an edge, vs. a move/arrange mode where dragging repositions). This resolves the
  drag-vs-connect conflict above and lets each command expose just the interactions it needs.
  Still **exploring approaches** — deferred while we focus on functionality; noted here so the
  handle/connection UX is revisited as part of this, not piecemeal.
- **Node creation.** *(Built.)* Create new nodes (and loose artifacts — see below) from the
  UI; currently bare buttons in the SCRATCH command, to be formalized into a real
  command (EDIT) once settled. Undoable via the `createNode`/`createLooseArtifact` store
  actions; ids are opaque uuids minted client-side.
- **Delete nodes / artifacts / edges.** *(Built.)* Delete via React Flow's native
  Delete/Backspace (a node cascades its edges). Deleting an edge — or a node that owned it —
  **detaches that edge's artifacts back into the pool** at the edge midpoint rather than
  destroying them (`detachEdges`). Undoable. (Today this leans on React Flow's built-in key
  handling; explicit keybindings for everything are a later pass.)
- **Smarter spawn placement for new nodes/artifacts.** Today a created node spawns at a
  fixed point with a small cascade offset (deliberately clunky). Give creation a real notion
  of *where* things land — e.g. the current viewport center, near the cursor, or offset from
  the selection — so new nodes/artifacts appear in view rather than at a fixed corner. Applies
  to the loose-artifact pool too.
- **Stagger coincident nodes on auto-arrange.** After an auto-arrange, any canvas nodes that
  land on the *same* coordinate should be nudged apart by a small offset so it's visible that
  several occupy one spot, rather than rendering as a single node. The sharp case today: the
  arrange request is built from `toGraphBlock`, which drops loose-artifact nodes — so the
  layout returns no position for them and they all fall back to `(0,0)` and stack. Two angles
  to consider: give the unplaced pool its own arranged placement (a column/grid beside the
  graph), and/or a general post-arrange pass that de-overlaps any coincident positions.
- **Custom node coloring.** Author-chosen colors per node. (Note: an earlier *automatic*
  start/middle/end role-coloring was rejected — coloring should be explicit author intent,
  not a derived, backend-absent property.)
- **Lock nodes by default.** Commands generally lock nodes in place; rearranging happens
  only inside a dedicated command, which also offers layout/distribution options and the
  ability to create new views.
- **Mass select & manipulate.** Select multiple nodes and act on them as a group — move,
  collapse, delete, and (once nodes/artifacts can carry extra tagged data) edit them
  together. React Flow has built-in multi-selection (drag-box / shift-click) to build on;
  the work is the group operations and how they interact with the per-view position model.

## Artifacts on the canvas

- **A canvas representation for artifacts.** *(Built.)* Loose (unplaced) artifacts live in a
  per-graph pool on `HuntDocument` (keyed by graph id), **propagate to every view** of that
  graph, and render as non-connectable canvas nodes; their *positions* are per-view (in `View`,
  with auto-layout fallback), like nodes. Placing an artifact moves it from the pool into an
  `edge.content`; detaching (one artifact, or all when an edge is deleted) returns it to the
  pool at the edge's midpoint. The React Flow element id is kept distinct from the domain
  artifact id (`loose:{id}`) so one artifact could later render in several places — which is
  also what keeps the normalization below cheap.
- **Drag an artifact onto an edge to place it.** The placement/detach actions are wired and
  driven by buttons in the GRAPH inspector (select an edge → place from pool / detach). The
  remaining piece is the gesture: drag a loose-artifact node and drop it on an edge to place
  it, drag it off to detach. React Flow has no native drop-on-edge, so this needs geometric
  hit-testing of the drop point against edge paths. The store actions (`placeArtifactOnEdge`/
  `detachArtifact`) are UI-agnostic, so the drag layer just calls the same machinery.
- **Normalize artifacts into a document-level store (future).** The chosen route above
  *embeds* artifacts in each `edge.content`, so the same artifact id on several edges is
  several equal copies: "appears on many edges" works (already supported today), but
  "edit once → all instances update" does not. The cleaner endgame is a normalized
  artifact table at the `HuntDocument` level (sibling of `graphs`) with edges/pool holding
  **id references** — giving true single-instance sharing and edit-propagation (the "one
  key, many locks" case). Deferred until edit-propagation is a felt need. Bounded refactor
  (touches `Edge.content`, the codec, and the binder's edge-reading code in
  `required_inputs`/`produced_outputs`/`Section.from_node`); no data migration since
  schemas are regenerated, not migrated.

  *Also resolves a builder-API asymmetry.* Today the builder is **id-first for nodes**
  (`node()` mints an id, `connect` wires node ids) but **value-first for artifacts** (built
  directly, passed by value into `connect`, embedded in the edge). That's justified now —
  a node is pure identity that *must* be referenced, an artifact *is* content and reads
  naturally as an embedded value (`connect(a, b, *cipher.artifacts().values())`) — and it
  underpins the value-equality round-trip and loose I/O coupling. But the **loose-artifact
  pool already lets artifacts exist off any edge**, nudging them toward first-class,
  id-referenced entities. The symmetry to reach for is *"everything is referenced by id,"*
  **not** *"everything goes through the builder"*: artifact creation/identity should move to
  a **separate, document-scoped artifact class** (a store/library that owns the instances and
  hands out ids) — deliberately *not* folded into `GraphBuilder`, which is graph-scoped and
  structural. The graph's edges and the pool then reference artifact ids. This respects that
  artifacts are document-scoped with their own lifecycle, distinct from graph wiring.
  Value-equality survives — id references are still values.
- **Artifact creation, two paths.** One rail command → a puzzle/artifact *generator*;
  a separate rail command → make an *individual* artifact. *(Partial:* the individual path has
  a clunky stub — `createLooseArtifact` drops a pre-baked text artifact into the pool from the
  SCRATCH command. Still to do: choosing the artifact type + editing its payload, and the
  generator path.*)*
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
- **Graceful save-validation errors that help the user fix the problem.** Today a save that
  fails validation (e.g. a cycle — the codec's `validate_structure` rejects it) comes back from
  the backend as a 422 whose raw `detail` string is dumped into a `<span>` in the menu bar
  (`MenuBar`'s `menu-bar__err`). It's accurate but ugly and unhelpful: it doesn't say *which*
  nodes/edges form the cycle or how to resolve it, and the user only finds out at save time.
  Wanted: (1) catch the failure and present it clearly (a dismissible message/panel, not a
  cramped menu-bar span), (2) **point at the offending elements** — parse/return the cycle's
  node ids and highlight them on the canvas — so the fix is obvious, and ideally (3) surface it
  *proactively* (pre-save, via the **Status window** above) rather than only on a failed save.
  Pairs with the deferred-audit "narrower exception handling (drop the catch-all 422)" item and
  with returning structured validation errors (offending ids, not just a message) from the
  codec/`app` seam.

## Polish & small enhancements

> **Agent note:** low-stakes cosmetic backlog — skip ahead to the next section unless the
> prompt is specifically about one of these items. Don't spend tokens reading it otherwise.

Non-functional UX niceties — nothing here changes what the editor *can do*, only how
pleasant it is. Low-stakes, pick up opportunistically.

- **Save As: assign the path, defer the write.** Today *Save As* (the Document section in
  SCRATCH) writes the file eagerly on click, mirroring *New*. A nicer feel: typing a path and
  hitting Save As would just *name* the untitled document (set the backend's active path)
  without touching disk, so the file only appears on the next real *Save* (Ctrl+S) — matching
  how most editors treat "untitled → named → saved". Small: split the backend's
  `/api/document/save-as` into a path-only "claim this path" step (still refuse-if-exists) and
  leave the write to the existing `PUT /api/graph`; the frontend would set the path and skip the
  reload (no write to reseed from yet). Defer until Save As leaves SCRATCH for the real
  Save/Load command, where the dirty-state UX gets designed properly anyway.
- **Full tab name on hover.** When a tab's title is truncated (many tabs shrink the width,
  or a long view name), reveal the full name on hover. Leaning toward a native `title`
  attribute set only when the label actually overflows (`scrollWidth > clientWidth`,
  measured on the hover the `TabBar` already handles) — full name when truncated, nothing
  when it already fits, no custom-tooltip machinery. A themed tooltip is the heavier
  alternative if the OS one ever feels off.
- **Center the graph after auto-arrange.** When the VIEW panel's Horizontal/Vertical
  arrange runs, recenter/fit the result in the viewport so the freshly laid-out graph isn't
  left scrolled off-screen (React Flow's `fitView`, applied after the new positions land in
  `ViewPanel.onArrange`).
- **Indicate tabs showing the same view.** Several tabs can reference one view (vim windows
  onto a buffer); give them a shared visual cue — a color/badge keyed off `tab.view` — so
  it's obvious which open tabs are different framings of the same drawing.

## Code health (deferred audit items)

From the 2026-06-27 code audit (full record in `AUDIT.md`). These were
deliberately *not* done in that cleanup pass because they add behavior or are
low-value polish — pick up when the adjacent work makes them natural:

- **FastAPI request validation.** Pydantic request models on the `/api/graph`
  endpoints + narrower exception handling (drop the catch-all 422). Pairs
  naturally with the browser file-picker milestone.
- **Frontend hardening.** A top-level React error boundary and explicit loading
  states (`main.tsx` / `Shell.tsx`).
- **Low-stakes nits:** `_wrap_graph_for_deserialization` helper for the repeated
  graph-envelope in `server.py`; `DEFAULT_TAB_ID` constant; `.panel__title` CSS;
  document the `350ms` history debounce; a few clarifying comments. See
  `AUDIT.md` for the exact lines.

## Later layers (defer unless asked)

- **More puzzle types.**
- **GUI authoring layer** (beyond the editor shell).
- **Tracking / monitoring layer** (layer 4) — the *only* place answer-checking would ever
  live.
- **Per-puzzle parameter metadata** in the serialized format (still open).
