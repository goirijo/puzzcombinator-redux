# Editor frontend

The UI for the hunt editor: a **React + React Flow** app (built with **Vite**, in
**TypeScript**) that draws the hunt graph and — soon — lets you edit it. It is a pure
consumer/producer of the backend's JSON seam; it owns no hunt data of its own.

The Python backend that serves that seam (the FastAPI app, the graph layout, the
canvas-state channel) is documented in
[`../src/puzzcombinator/app/APP.md`](../src/puzzcombinator/app/APP.md) — read that for the
server and the `/api/graph` shape. **This doc is the frontend code: what's here, how it's
organized, and how to add a feature.**

For how the UI should *look and behave* — the interface design worked out before the code —
see [`design/DESIGN.md`](design/DESIGN.md) and the per-feature specs alongside it. (This doc
describes the code that exists; `design/` describes what we intend to build and why.)

## What's actually in here (and what isn't)

A frontend directory looks alarming the first time, but **git tracks ~30 small text
files.** The hundreds of megabytes you see on disk are not in the repo:

```
frontend/
├── node_modules/   ~160 MB, ~120 packages   ← NOT in git. downloaded library code.
│                                               recreate anytime with `npm install`.
├── dist/           build output              ← NOT in git. made by `npm run build`.
└── ~30 tracked files                         ← the actual repo. tiny.
```

`node_modules/` is where npm downloads the libraries you depend on. You ask for a few
(React, React Flow, Vite); each of *those* depends on others, which depend on others — so a
handful of requests fan out to ~120 packages. **This is normal for every JS project**, and
it's exactly why it's gitignored: you never commit it, you regenerate it with `npm install`.
`package.json` + `package-lock.json` are the recipe that makes that reproducible.

## The files

Stack: React + React Flow (v12, `@xyflow/react`) + Vite + TypeScript, plus
**`react-resizable-panels`** (v4 — `Group`/`Panel`/`Separator`) for the draggable panel
divider, and **Zustand + zundo** for the graph store and its Undo/Redo history. No router —
it's one screen built as a *shell* (stable regions) with *features* (panels) plugging into
it.

`src/` is grouped by role: entry + global CSS at the root, then `model/` (the backend seam),
`nodes/` (canvas node components), `shell/` (the chrome), `panels/` (features). Tests live
next to their source (`*.test.ts`).

**Entry + globals (`src/`):**

| File | What it is |
| --- | --- |
| `main.tsx` | Entry point — mounts `<App>` into the page. Set once. |
| `App.tsx` | Now trivial: it just renders `<Shell />`. (State + I/O moved into the shell.) |
| `theme.css` | Every color/size as a `:root` CSS variable — the **swappable theme** (node colors *and* the shell-chrome tokens). |
| `index.css` | Structural reset (full-viewport). |

**The seam + pure adapters (`src/model/`):**

| File | What it is |
| --- | --- |
| `api.ts` | The **seam** in TS: the DTO interfaces mirroring `GET /api/graph` + `fetchGraph()` (load) and `saveGraph()` (`PUT`, the inverse). The one place the wire shape is written down; the compiler flags drift. |
| `adapt.ts` | The **pure adapter**: `toFlow()` maps seam DTOs → React Flow `{nodes, edges}`; `fromFlow()` is its inverse (→ the `{nodes, edges}` block `PUT` expects). No React/fetch/state. Defines the view-model types (`Hunt*`, `NodeFields`, `View`) and derives node role from topology. |
| `adapt.test.ts` | Vitest units for `toFlow`/`fromFlow` (role derivation, null↔'' coalescing, round-trip). |

**Canvas node components (`src/nodes/`):**

| File | What it is |
| --- | --- |
| `HuntNode.tsx` | The **node component**: renders one node's box from its `data`. No style values (class names + `data-role`); carries the two React Flow `Handle`s edges attach to. A new node *type* is another component here, registered in `shell/Canvas.tsx`'s `nodeTypes`. |

**The shell — the stable region skeleton (`src/shell/`):**

| File | What it is |
| --- | --- |
| `Shell.tsx` | The **stateful / I/O file**. Fetches on mount, subscribes to the graph store, holds the *non-undoable* UI state (`selection`, active command, `views`, save status + dirty), wires the regions with `react-resizable-panels`, and drives global Save/Undo/Redo + keyboard shortcuts. |
| `store.ts` | The **graph store** — a Zustand store wrapped in zundo's `temporal` middleware. Holds the *undoable* state (nodes + edges) and its mutators (`updateNode`, the React Flow change handlers). Tuned so one user action = one undo step (`equality` ignores selection/drag flags; a leading-edge `handleSet` debounce coalesces typing/drag bursts). |
| `MenuBar.tsx` | The full-width top **menu bar**: global Undo / Redo + a single Save with a dirty indicator. Pure presentational; fed by `Shell.tsx`. |
| `CommandRail.tsx` | The left **command rail**: one button per registry entry; collapses to a sliver. A dumb container — reads `COMMANDS`, reports clicks up. |
| `TabBar.tsx` | The top **tab bar**: one tab per *view*. One default view today; the seam for many later. |
| `PanelRegion.tsx` | The **swappable panel**: looks the active command up in the registry and renders its `Panel`, forwarding `PanelProps`. Knows no specific panel. |
| `Canvas.tsx` | The **canvas region**: wraps `<ReactFlow>`, reports selection up, and re-`fitView`s on container resize (the one React Flow resize gotcha). |
| `commands.ts` | The **command registry**: the `COMMANDS` list pairing each command id with the panel it opens. The single plug-in point — add a command here, nowhere else. |
| `types.ts` | The shell↔feature contracts: `Selection`, `SaveState`, and `PanelProps` (what every panel receives). |
| `history.ts` | Pure undo-granularity helpers used by `store.ts`: `graphSignature` (what counts as a meaningful change) and `leadingDebounce` (how a burst collapses to one step). Kept separate so they're unit-testable. |
| `history.test.ts` | Vitest units for `graphSignature` + `leadingDebounce`. |
| `shell.css` | Region + panel styling. Structural/visual CSS using `theme.css` tokens (no hardcoded values). |

**The features — panels that plug into a region (`src/panels/`):**

| File | What it is |
| --- | --- |
| `GraphInspector.tsx` | The **GRAPH** command's panel: edit the selected node's label/action/notes, see its incoming/outgoing edges + artifacts, Save. A pure view over `PanelProps`. |
| `PlaceholderPanel.tsx` | The stand-in every not-yet-built command opens, so the rail shows the full intended command set. |

**Config — set once, rarely opened:** `index.html` (the page React loads into),
`package.json` (deps + the `dev`/`build` scripts), `package-lock.json` (npm's exact-version
lock — auto-managed, never hand-edited), `vite.config.ts` (Vite settings; holds the `/api`
proxy), `tsconfig*.json` ×3 (TypeScript compiler settings, split by Vite convention),
`eslint.config.js` (lint rules), `.gitignore` (ignores `node_modules`/`dist`),
`public/favicon.svg` (the browser-tab icon).

## The architecture: a shell, not a screen

The editor is a **shell** (a stable skeleton of *regions* — command rail, tab bar,
swappable panel, canvas) plus **features** (self-contained components that live inside a
region). The payoff is that adding a feature never restructures the app — you fill a slot
that already exists. The design rationale lives in [`design/DESIGN.md`](design/DESIGN.md);
the seams that hold it together are:

- **The command registry (`shell/commands.ts`).** Each command is a `{ id, label, icon,
  Panel }` descriptor. The rail renders a button per entry; the panel region renders the
  active entry's `Panel`. Neither names a specific command — so a new one is *one entry*.
- **`PanelProps` (`shell/types.ts`).** The uniform contract every panel receives (the
  graph, the `selection`, `updateNode`). A panel is a pure view over this; it owns no graph
  state. (Saving is global — it lives in the menu bar, not a panel.)
- **The view model (`View` in `model/adapt.ts`).** A *view* is a particular drawing of a
  graph; a tab is a view. The canvas consumes one today (a single default view), so multiple
  views drop in without rewiring it.

**Pure modules vs. stateful files** — the same discipline as the Python core.
`model/` and `nodes/HuntNode.tsx` and every panel are pure (data + view, no I/O). State
has two homes: the **graph** (the undoable thing) lives in the zundo-backed Zustand store
(`shell/store.ts`) so Undo/Redo come almost for free; all other **UI state** (selection,
active command, save status, views) lives in `shell/Shell.tsx` as plain hooks. The store is
deliberately scoped to the graph — `DESIGN.md`'s "lift to the shell first" still governs
everything that isn't the graph; don't pour unrelated UI state into the store.

Two conventions that go with it:

- **Naming.** Seam/wire types end in `DTO` (`NodeDTO`, `EdgeDTO`, `GraphResponseDTO`);
  view-model types start with `Hunt` (`HuntNodeData`, `HuntFlowNode`). Two layers, two
  conventions — don't blur them, and don't paper over a name clash with an alias.
- **Styling.** Components hold **no** style values. Colors/sizes are `:root` variables in
  `theme.css`; structural layout (e.g. full-screen) is in `index.css`. A theme is just a
  swapped block of variables.

## Running it (development)

Two processes — the API and this UI:

```bash
# 1) backend (from the repo root) — see ../src/puzzcombinator/app/APP.md for options
python -m uvicorn puzzcombinator.app.server:app --reload   # API on http://127.0.0.1:8000

# 2) this UI (from frontend/)
npm install        # first time only — populates node_modules/
npm run dev        # UI on http://127.0.0.1:5173
```

Open **http://127.0.0.1:5173** — Vite proxies `/api` to the backend on `:8000`, so there's
one origin and no CORS. `npm run build` (`tsc -b && vite build`) type-checks every file and
is the cheap correctness gate; run it before committing.

## How to add a feature — the recipe

Find what you're adding; it tells you which file to touch:

- **A new command / panel** (Puzzle, Bind, …) → write a component in `panels/` that takes
  `PanelProps`, then swap it in for that command's `Panel` in `shell/commands.ts`. No shell
  edits — the rail and panel region pick it up. (A brand-new command is one more `COMMANDS`
  entry + its `CommandId`.) **Full step-by-step:**
  [`ADDING-A-COMMAND.md`](ADDING-A-COMMAND.md), which walks it end to end using the GRAPH
  command as the worked example.
- **A new field the backend already sends** (a node gains an attribute, say) → add it to the
  matching DTO in `model/api.ts`, then use it. If the backend doesn't send it yet, that's a
  backend change first (see [`APP.md`](../src/puzzcombinator/app/APP.md)).
- **A new graph→view transform** (e.g. color edges by artifact count) → edit `model/adapt.ts`.
  It's pure, so it's the easy place to reason about and to unit-test (`model/adapt.test.ts`).
- **A new look, or a new kind of node** → edit `nodes/HuntNode.tsx` (structure) + `theme.css`
  (colors). For a genuinely new node type, write another component in `nodes/` and register
  it in `shell/Canvas.tsx`'s `nodeTypes` map.
- **A new interaction, state, or network call** → a **graph mutation** goes in the store
  (`shell/store.ts`) so it's undoable; **other UI state** goes in `shell/Shell.tsx`. Either
  way, expose it to panels via `PanelProps`; keep new markup in a *pure* component. Saving is
  global (the menu bar): `saveGraph()` `PUT`s the `fromFlow` block to `/api/graph` (the
  backend already supports it — see [`APP.md`](../src/puzzcombinator/app/APP.md); note it
  returns **409 in demo mode** with no `PUZZ_GRAPH` file).
- **Always finish with `npm run build`** — it's the type-check gate.

The throughline: a new command → `commands.ts` + a `panels/` component; new wire data →
`model/api.ts`; a transform → `model/adapt.ts`; a visual → a component + `theme.css`; a graph
mutation → `shell/store.ts`; other state/I/O → `shell/Shell.tsx`.

## Tests

**Vitest** runs the unit tests (`npm test`, or `npm run test:watch`). Config lives in
`vite.config.ts` (`test` block, jsdom environment); test files are co-located as `*.test.ts`
next to their source and excluded from the production build (`tsconfig.app.json`).

We test the **small, pure, stable** parts — the pieces that get moved around as the UI
evolves — not components or end-to-end flows yet (the interface is still changing):

- `model/adapt.test.ts` — `toFlow`/`fromFlow`: role derivation, null↔'' coalescing, round-trip.
- `shell/history.test.ts` — `graphSignature` (selection/jitter ignored) and `leadingDebounce`
  (one history step per burst).

`npm run build` remains the type-check gate. Component behavior (click a node → inspector
fills) and full flows are verified **by hand in the browser** for now; when the interface
settles, the natural next steps are React Testing Library (components) and Playwright (E2E).
