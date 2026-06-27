# AUDIT — code-health snapshot (2026-06-27)

A one-time code-quality audit of the whole tree (Python library, FastAPI app +
serialization seam, React/TS frontend), run as four parallel sweeps and
spot-checked against the real code. This file is the **durable record** so a
future session reads it instead of re-trawling the codebase.

**Headline:** the codebase is genuinely well-architected — strict downward
layering, value-based artifact equality, a graph-free workspace channel with
standalone codec round-trip tests, pure/deterministic `layered_layout`, no
`isinstance` type-switching in the export path, two-store frontend
channel-independence, no inline styles, strong tests (189 backend + frontend
Vitest). Findings were real but mostly small.

**Scope decision:** implement only genuine cleanups/simplifications (no new
functionality), backend first then frontend. Functionality-adding items
(request validation, error boundary, etc.) are **deferred** and also pointed to
from `ROADMAP.md`.

Status legend: ✅ fixed in this pass · ⏸ deferred (recorded only) · 🟢 kept on
purpose.

## Backend — Python library + app

| file:line | finding | priority | status |
|---|---|---|---|
| `core/graph.py:132-148` | `_check_acyclic()` rescans all edges per node → O(V·E). `_rewire()` runs *after* validation so can't use `self.outgoing()`; build a local adjacency map. | high (perf) | ✅ |
| `core/builder.py:85-90` | `connect()` uses `isinstance(item, Iterable)`; a stray `str` is silently exploded into per-char "artifacts". Make checks type-led, reject `str`. | high (footgun) | ✅ |
| `visualization/defaults.py:48-57` | `resolve_workspace()` mutates the caller's `stored` Workspace (reassigns `view.positions`). Return a fresh object. | medium | ✅ |
| `puzzles/base.py:66-76` | Duplicate-name guard is an unimplemented TODO — colliding names silently drop a piece. Implement it (raise `PuzzleError`). | medium | ✅ |
| `artifacts/composite.py:74` + `rendering/binder.py:63` | `_dedupe` duplicated verbatim. `artifacts → rendering` import is allowed; promote to one shared `dedupe_css` helper. | medium (DRY) | ✅ |
| `puzzles/crossword.py` | `render()` runs `_analyze()` twice (grid + clues); nested `section()` helper. Analyze once; lift helper to module level. | medium | ✅ |
| `puzzles/cipher.py:72-94` | Three render branches rebuild the same `<section>` wrapper. Compute `body`+`css_class`, emit once. | medium (DRY) | ✅ |
| `rendering/__init__.py` | `presets` is imported by puzzles but not in `__all__`. Add it. | low | ✅ |
| `app/server.py:104-153` | Endpoints take `body: dict[str, Any]` with no schema; validation deferred to deep try/except. Add Pydantic request models. | high | ⏸ (adds behavior; pair with file-picker) |
| `app/server.py:119-123, 148-152` | Catch-all `(GraphError, SerializationError, KeyError, TypeError)` → 422 masks structural errors. Narrow once Pydantic lands. | medium | ⏸ |
| `app/server.py:120, 149` | Repeated `{KEY_SCHEMA_VERSION: SCHEMA_VERSION, KEY_GRAPH: ...}` envelope. Extract `_wrap_graph_for_deserialization`. | low | ⏸ (fold into file-picker work) |
| `app/server.py:99` | Non-obvious extraction of `KEY_GRAPH` from the single-graph envelope; add a clarifying comment. | low | ⏸ |
| `visualization/defaults.py:44` | Hardcoded `"tab-1"`; extract `DEFAULT_TAB_ID`. | low | ⏸ |
| `core/graph.py:82-83` | `_rewire()` runs after `validate_structure()` by design (round-trip wiring); add a clarifying comment. | low | ⏸ |
| `visualization/workspace.py` (`workspace_to_json`/`from_json`) | Public, used only by tests today. **Kept** — it's the standalone serialization path backing the workspace channel-independence invariant. | n/a | 🟢 |

## Frontend — React / TS

| file:line | finding | priority | status |
|---|---|---|---|
| `frontend/src/shell/shell.css` | `background: transparent` / `border: none` repeated across `.ghost-btn`, `.tab-bar__*`, `.panel__close`. Group shared declarations. | low (standing pref) | ✅ |
| `frontend/src/shell/TabBar.tsx:15` | Unused `CSSProperties` import. | low | ✅ |
| `frontend/src/panels/GraphInspector.tsx` | Incoming/outgoing render the same heading + list + empty-state twice. Extract `RelatedEdgeList`. | low (DRY) | ✅ |
| `frontend/src/panels/ViewPanel.tsx:47-58` | `onArrange` stale-closure: rapid clicks can leave the button stuck / apply a stale layout. Guard with a `requestIdRef`. | medium (latent bug) | ✅ |
| `frontend/src/main.tsx`, `Shell.tsx` | No top-level error boundary / loading states. | medium | ⏸ (ship-time hardening, new behavior) |
| `frontend/src/shell/PanelRegion.tsx:20` | `.panel__title` class used but undefined in CSS (inherits). | low | ⏸ |
| `frontend/src/edges/floating.test.ts:12` | `as unknown as InternalNode` double-cast in a test mock. | low | ⏸ |
| `frontend/src/shell/graphStore.ts:68` | `350ms` debounce is an undocumented magic number; add a why-comment. | low | ⏸ |

## Dead code

Dedicated reference-traced sweep (backend + frontend, accounting for
registry/decorator dynamic dispatch): **no true dead code**. All public exports
are intentional, all module-level functions have callers, private helpers are
scoped, all React components/hooks reachable via the command registry/stores.
The one test-only export (`workspace_to_json`/`workspace_from_json`) is kept on
purpose (see table above).
