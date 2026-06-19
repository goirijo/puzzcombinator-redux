# Editor frontend

The UI for the hunt editor: a **React + React Flow** app (built with **Vite**, in
**TypeScript**) that draws the hunt graph and — soon — lets you edit it. It is a pure
consumer/producer of the backend's JSON seam; it owns no hunt data of its own.

The Python backend that serves that seam (the FastAPI app, the graph layout, the
canvas-state channel) is documented in
[`../src/puzzcombinator/app/APP.md`](../src/puzzcombinator/app/APP.md) — read that for the
server and the `/api/graph` shape. **This doc is the frontend code: what's here, how it's
organized, and how to add a feature.**

## What's actually in here (and what isn't)

A frontend directory looks alarming the first time, but **git tracks ~18 small text
files.** The hundreds of megabytes you see on disk are not in the repo:

```
frontend/
├── node_modules/   ~160 MB, ~120 packages   ← NOT in git. downloaded library code.
│                                               recreate anytime with `npm install`.
├── dist/           build output              ← NOT in git. made by `npm run build`.
└── ~18 tracked files                         ← the actual repo. tiny.
```

`node_modules/` is where npm downloads the libraries you depend on. You ask for a few
(React, React Flow, Vite); each of *those* depends on others, which depend on others — so a
handful of requests fan out to ~120 packages. **This is normal for every JS project**, and
it's exactly why it's gitignored: you never commit it, you regenerate it with `npm install`.
`package.json` + `package-lock.json` are the recipe that makes that reproducible.

## The files

Stack: React + React Flow (v12, `@xyflow/react`) + Vite + TypeScript. No router, no global
state library — it's one screen.

**The app — the files you'll actually edit (`src/`):**

| File | What it is |
| --- | --- |
| `api.ts` | The **seam** in TS: the DTO interfaces mirroring `GET /api/graph` + `fetchGraph()`. The one place the wire shape is written down; the compiler flags drift. |
| `adapt.ts` | The **pure adapter**: `toFlow()` maps seam DTOs → React Flow `{nodes, edges}`. No React/fetch/state. Defines the view-model types (`Hunt*`) and derives node role from topology. |
| `HuntNode.tsx` | The **node component**: renders one node's box from its `data`. No style values (class names + `data-role`); carries the two React Flow `Handle`s edges attach to. |
| `App.tsx` | The **one stateful / I/O file**: fetches on mount, runs `toFlow`, holds state via `useNodesState`/`useEdgesState`, renders `<ReactFlow>`. |
| `main.tsx` | Entry point — mounts `<App>` into the page. Set once. |
| `theme.css` | Every color/size as a `:root` CSS variable — the **swappable theme**. |
| `index.css` | Structural reset (full-viewport canvas). |

**Config — set once, rarely opened:** `index.html` (the page React loads into),
`package.json` (deps + the `dev`/`build` scripts), `package-lock.json` (npm's exact-version
lock — auto-managed, never hand-edited), `vite.config.ts` (Vite settings; holds the `/api`
proxy), `tsconfig*.json` ×3 (TypeScript compiler settings, split by Vite convention),
`eslint.config.js` (lint rules), `.gitignore` (ignores `node_modules`/`dist`),
`public/favicon.svg` (the browser-tab icon).

## The architecture, in one rule

**Pure modules vs. one stateful file** — the same discipline as the Python core.
`api.ts` / `adapt.ts` / `HuntNode.tsx` are pure (data + view, no I/O); `App.tsx` is the
*single* home of state and network calls. That's what keeps the logic testable and the view
swappable (it's how we replaced the old vanilla-SVG frontend without touching any Python).

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

- **A new field the backend already sends** (a node gains an attribute, say) → add it to the
  matching DTO in `api.ts`, then use it. If the backend doesn't send it yet, that's a backend
  change first (see [`APP.md`](../src/puzzcombinator/app/APP.md)).
- **A new graph→view transform** (e.g. color edges by artifact count) → edit `adapt.ts`. It's
  pure, so it's the easy place to reason about and the natural first thing to unit-test.
- **A new look, or a new kind of node** → edit `HuntNode.tsx` (structure) + `theme.css`
  (colors). For a genuinely new node type, write another component and register it in
  `App.tsx`'s `nodeTypes` map.
- **A new interaction, state, or network call** (selection, an inspector panel, Save) →
  `App.tsx` holds the state and the handler; put any new markup in its own *pure* component
  that `App.tsx` renders. Saving = `PUT` the graph block back to `/api/graph` (the backend
  already supports it — see [`APP.md`](../src/puzzcombinator/app/APP.md)).
- **Always finish with `npm run build`** — it's the type-check gate.

The throughline: new wire data → `api.ts`; a transform → `adapt.ts`; a visual → a component
+ `theme.css`; state/I/O → `App.tsx`.

## Tests

No automated frontend tests yet. `npm run build` type-checks everything and is the current
gate. `adapt.ts` is the natural first unit test (e.g. with Vitest) because it's pure —
seam JSON in, React Flow data out. React Flow behavior is verified by hand in the browser.
