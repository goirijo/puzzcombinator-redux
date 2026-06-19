# Editor UI — design notes

This directory is the **space for interface-design specs**: how the editor UI should
*look and behave*, worked out before (or alongside) the code that implements it. It is
deliberately separate from [`../FRONTEND.md`](../FRONTEND.md), which documents the code that
*exists*. Specs here describe what we intend to build and why; FRONTEND.md describes what's
already there and how to extend it.

Add per-feature specs as their own files alongside this one (e.g. `inspector.md`,
`binder-builder.md`) as each gets designed. **This file is the foundational one**: the
overall shape of the editor and the principles that keep it incremental.

---

## The target shape: Inkscape-style, docked

The editor is a single screen built like Inkscape (the editor the user is most used to):

- A **canvas** dominates the middle — this is the React Flow node-graph.
- A thin **command rail** down the left edge — one button per command/tool. The rail can
  **collapse** to a sliver to recover canvas space.
- Clicking a command opens a **docked panel** next to the rail. Panels are **docked**
  (pinned to an edge), not floating windows — a deliberate choice (see below). A panel can
  be closed to recover space, and **resized by dragging its edge**.
- The panel region is **swappable**: it shows whichever command is active (the inspector
  now, the binder builder later, …), or nothing when none is.

Decisions already settled:

- **Docked, not floating.** Free-floating draggable windows mean reimplementing window
  management (positions, z-order, drag) — medium-to-hard and not worth it. Docked
  collapsible panels give ~95% of the "open an inspector, close it to recover space" feel
  for a fraction of the effort, and match what VS Code / Figma actually use. Floating could
  be added much later as a self-contained feature; it is **not** planned.
- **Resizable panels are wanted** (drag the divider to widen a panel).

---

## The one idea that makes this incremental: build a *shell*, not a *screen*

Every editor-style app (Inkscape, VS Code, Figma, Blender) is two separate things:

1. **The chrome (the shell)** — a stable skeleton of *regions*: command rail, swappable
   panel, canvas, (later) a status bar. This frame rarely changes.
2. **The features** — self-contained components that *live inside* a region (the inspector,
   the binder builder, a toolbar button). Each owns its little area and knows nothing about
   the others.

The payoff: **you define the empty regions once, then every new feature is "build a small
component, drop it in a region."** You never restructure the app to add a feature — you fill
a slot that already exists. It's the same discipline as the Python layering: stable seams
(the regions) plus small things that plug in (the components).

So the first thing to build is the **shell with mostly-empty regions**, not a finished
screen.

### The habits that keep it clean

1. **Regions are dumb containers.** The shell says "rail here, panel here, canvas here" and
   holds no feature logic.
2. **Each feature is one small component, single responsibility** — like the puzzle classes.
   Split anything doing two jobs.
3. **Build *vertical slices*, not *horizontal layers*.** Don't build the whole rail first;
   pick one feature and build it through every region it touches, end to end. The rail grows
   one button at a time as features that need a button arrive. A "Save" button is worthless
   until the save *action* exists — build the action first.
4. **State is the part to be deliberate about.** When two regions touch the same data (click
   a node on the canvas → the inspector shows *that* node), they share state. Walk this
   progression in order, don't skip ahead:
   - **Local state** in one component (where `App.tsx` is now).
   - **Lift to the shell** when two siblings need it — the shell owns `selectedNodeId` + the
     graph and passes them down. This carries you a long way.
   - **A small store** (Zustand — *not* Redux) only when prop-passing gets painful. You'll
     feel when that happens; don't pre-build it.

---

## React Flow is *not* the app — it's one widget inside it

The crux, and the thing to internalize: **React Flow only draws the node-graph canvas.**
That's its whole job. The command rail, the collapsible/resizable panels, the inspector, the
binder builder, the previews — *none of that is React Flow's concern.* All of it is plain
React + CSS, with React Flow sitting in the middle as the content of the canvas region.

So the right question is almost never "can React Flow do X?" — it's "can React do X?", and
for everything below the answer is yes. React is *for* showing and hiding pieces of UI based
on state.

---

## Feasibility / difficulty of the pieces we discussed

| Piece | Difficulty | How |
| --- | --- | --- |
| Collapse the command rail | **easy** | one boolean of state; render full rail or a sliver |
| Click a command → a panel appears | **easy** | one `activePanel` value (`"inspector"` \| `"binder"` \| `null`); the panel region renders whichever matches. Adding a command later = a button + one `case`. |
| Drag-to-resize a panel | **easy with a library** | use **`react-resizable-panels`** (`PanelGroup` / `Panel` / `PanelResizeHandle`) — gives the draggable divider, min/max, and size persistence for free. Writing it by hand is "medium" (mouse-event math); don't. |
| HTML preview of an artifact render | **easy — we're set up for it** | artifacts already render to self-contained HTML+CSS (the binder consumes it). Drop that string into an `<iframe>` (iframe so the artifact's CSS can't leak into the editor). The hard part is done in Python; the frontend just displays a fetched string. |
| Binder builder (drag artifacts in, reorder, group into chapters) | **medium — the one meaty piece** | two halves below |

### The binder builder, broken down

- *The drag-and-drop* (pick up an artifact, drop into a chapter, reorder) needs a small DnD
  library — **`dnd-kit`**, **not** React Flow. This is the only genuinely new skill in the
  list; bounded and very well documented (reorderable lists are a solved problem).
- *The grouping data* (which artifacts, in what order, in which chapter) is just a list in
  state — and it maps almost one-to-one onto the Python `Section` / `Chapter` / `Binder`
  primitives. The UI builds that structure; on Save it hands it to the backend, which builds
  the real binder. The serialization seam absorbs it, same as everything else.

### One known gotcha (not a trap, just expect it)

React Flow must be told when its container changes size, or the canvas can look stale after
you drag a divider. It has a built-in resize observer / `fitView`-on-resize for exactly this
— a one-line concern, flagged here so it doesn't read as a bug later.

---

## Recommended build order

1. **The empty shell** — collapsible command rail + a resizable swappable panel region +
   the canvas, built on `react-resizable-panels` (so resize comes for free, not bolted on),
   with one placeholder button. No feature logic yet.
2. **First vertical slice: the inspector** — click a node → the panel shows its
   `label` / `action` / `notes` → edit → a Save button (`PUT`s back through the existing
   seam). Small, and it teaches the selection-state *lifting* from habit #4 on a real
   feature. The backend already supports the save (`PUT /api/graph`).
3. **The binder builder, later** — the meatiest panel, but it slots into the *same* frame:
   another command button, another panel component. Tackle once the rhythm is established.

Everything after the shell is "write a component, add a button, add a `case`" — no
restructuring. That is the whole point of doing the shell first.

---

## Feeding designs as Inkscape SVG

SVG is the ideal format to hand me a design, because I read it **two ways at once**: as a
rendered picture *and* as text (the `<text>` labels, the element `id`s/labels, the layer
names, and the x/y/width/height that encode your layout). A labeled SVG wireframe carries
more intent than paragraphs. Polish doesn't matter; **labels and structure do.** Commit the
`.svg` straight into this `design/` directory.

**The golden rule: keep text as text.** Do **not** run *Path → Object to Path* on your
labels before saving — that turns words into path outlines, and I'd see meaningless curve
data instead of the words. Likewise avoid embedding big raster images; keep it vector boxes
+ text so the whole file stays readable. Save as **Inkscape SVG** (the default) — its layer
and object *labels* are exactly the structure I rely on.

A strategy that makes an SVG far more useful than a bare drawing:

1. **Name the structure.** Give each region box a real name via *Object → Object Properties
   → Label* (and/or a meaningful `id`). "command-rail", "swappable-panel", "canvas" come
   through in the SVG as labels I can read — so I know which box is which without guessing.
2. **Put a text label *inside* each box** too (just type it on the canvas). Belt and
   suspenders: the visible label and the object label both reach me.
3. **Write behavior in words, with arrows.** Next to a thing, add a short text note for what
   it *does* — "collapses to a sliver", "drag edge to resize →", "click → opens Inspector
   here". I read those literally, so spell out the interaction rather than implying it.
4. **Use layers for interaction states.** Inkscape layers become named groups in the SVG, so
   you can put each *state* on its own toggleable layer in **one file** — e.g. a `default`
   layer, a `rail-collapsed` layer, an `inspector-open` layer, a `binder-open` layer. Name
   the layers by the state they show. Toggling layers lets you draw the before/after of an
   interaction without separate files, and the layer names tell me what each state is.
5. **Add a small legend.** A text block in a corner saying what your conventions mean
   (e.g. "dashed = collapsible", "blue fill = clickable", "orange = panel that swaps") removes
   all ambiguity from colors and line styles.

**File conventions for this directory:** one `.svg` per screen/feature, named for its
subject (`shell.svg`, `inspector.svg`, `binder-builder.svg`), sitting next to its matching
spec doc if there is one. Rough proportions in the drawing are enough — I infer relative
layout from the geometry; I don't need a pixel grid.

In short: **boxes + real text labels + named layers/objects + a legend.** That gives me the
picture, the names, the states, and the behavior all in one file I can both see and parse.
