# CLAUDE.md — puzzcombinator

Orientation for a fresh session. Read this, skim `README.md` and
`examples/hunts/mock_hunt/hunt.py`, and you're caught up — you do **not** need any prior
chat transcript. Deeper rationale lives in the auto-loaded memory files
(`design-principles`, `roadmap`) and in `git log` (commit messages are detailed).

## What this is

A modular Python library for **authoring treasure-hunt games**. It is a
**design-time tool for the hunt's designer**: create puzzles, compose them into a
hunt graph, and generate printable materials. It does **not** play or grade a
hunt — there is no answer-checking anywhere (in a physical hunt, correctness is
implicit when one puzzle's output is the next one's input). Live
progress-tracking is a future, separate layer.

## Refactor complete (bottom-up rebuild, 2026-06-04 → 2026-06-14)

We rebuilt the library **one layer at a time, lowest first**. All phases are done and
green:

- **Phase 1 — Artifact layer.** Minimal single-thing primitives (`text`/`image`/`svg`),
  a `CompositeArtifact`, the registry envelope helpers, and the single-artifact file
  writers. See `src/puzzcombinator/artifacts/ARTIFACTS.md`.
- **Phase 2 — Puzzles + serialization + core hooks.** The puzzle generators,
  `serialization/codec.py`, and `core/graph.py`'s duplicate-id check; the old
  player/game-master split (and the `Audience` enum) is **gone from the codebase**. A
  puzzle emits *all* its pieces — prompt pieces and answer key — as one flat
  `{name: Artifact}` map; which piece goes where is a placement decision.
- **Phase 3 — The binder.** `rendering/binder.py` was rebuilt as composable
  `Section`/`Chapter`/`Binder` primitives (see "Output / the binder" below). The old
  `game_master_binder`/`player_pages`/`hunt_bundle` and the player-vs-answer-key routing
  question are **gone** — a binder is now just whatever collection of renderings the
  designer assembles.

`pytest` is **171 passed / 0 skipped**, `ruff` + `mypy` clean. (Pre-existing lint/format
drift in `examples/hunts/jgg_hunt/hunt.py` — the user's WIP hunt — is out of scope.)

## Architecture — the model and the layer map

The model (artifact-on-edge graph), the layered stack + its strict downward dependency
direction, and the **generated → stored → displayed** data lifecycle all live in
**[`ARCHITECTURE.md`](ARCHITECTURE.md)** — read it once to orient. Per-layer detail is in
the package docs it links to (`artifacts/ARTIFACTS.md`, `puzzles/PUZZLES.md`,
`core/GRAPHS.md`, `rendering/RENDERING.md`, `app/APP.md`). That is the canonical
architecture reference; this file is the agent quickstart + current status.

A few practical facts for *writing code here* that the architecture doc doesn't dwell on:

- **Authoring call:** `connect(source, target, *artifacts)`. Example —
  `connect(start, solve, *cipher.artifacts().values())`, then
  `connect(solve, find, TextArtifact("go to the kitchen"))`. Artifacts ride the edges
  *into* the action that consumes them; a puzzle's answer is a separate artifact you place
  on the outgoing edge.
- **Ids are internal, auto-generated.** `GraphBuilder.node(...)` returns a *handle* (the
  node id) you pass to `connect` (no fluent chaining; `connect` returns self). Omitted node
  ids auto-generate (`n1`, `n2`, …); artifact ids default to `{type_name}-{uuid}`, and a
  puzzle prefixes its pieces `{puzzle.id}-{name}` — pass an explicit id only for readable
  filenames. The same artifact may be reused on several edges; only a repeated id *within a
  single edge* is rejected.

## Output / the binder

A **binder** is **not a fixed thing** — it is just *a collection of renderings that
logically belong together*, chosen by the designer. There is **no player-vs-answer-key
routing** and no opinion about what a hunt's output "should" be (that question dissolved
with the `Audience` enum); you decide what goes in and `rendering/binder.py` gives you
composition + layout. Pure (renders to a string — write with `Path.write_text`) and
artifact-agnostic. Three nesting levels, each aggregating the one below, mirroring
`CompositeArtifact`:

- **`Section`** — one rendered item. `Section.from_artifact(artifact)`, or
  `Section.from_node(graph, node_id, *, incoming=True, outgoing=True)` (a node's
  header + the artifacts on its incoming/outgoing edges, via `required_inputs`/
  `produced_outputs`). Node-facing binder methods take **ids** (the same handle
  `node()`/`topological_order` give back) and materialize via `graph.node` internally.
- **`Chapter`** — a group of closely-related sections under an optional title.
  `Chapter.of_artifacts(...)` / `Chapter.of_nodes(graph, node_ids, ...)`.
- **`Binder`** — a collection of chapters rendering to **one standalone HTML document**.
  Layout knobs are fields: `title`, `chapter_divider` (page break, default) and
  `section_divider` (thin rule, default), all overridable. `Binder.of_artifacts(...)` /
  `Binder.of_nodes(graph, node_ids, ...)` wrap a single chapter for the ungrouped case.

The two headline uses: `Binder.of_artifacts([p.artifacts("solution") for p in puzzles])`
(an answer key) and `Binder.of_nodes(graph, topological_order(graph))` (a page-per-node
walkthrough). Every fragment's `styles` aggregate and **de-duplicate** into one `<head>`
(a local copy of `CompositeArtifact._dedupe`, since `rendering` must not import
`artifacts`) — so a new artifact needs **zero binder edits**. See
`rendering/RENDERING.md` and `examples/hunts/mock_hunt/hunt.py` (builds several binders
from one graph).

## Key design rules (don't violate without discussing)

- **Authoring-only** — no `Validator`/`check`/`is_solved`/answer-gating anywhere.
- **Loose I/O coupling** — a puzzle's solution is NOT auto-linked to the outgoing
  edge; the designer hand-writes the answer artifact. (Revisit only when drift
  causes real bugs.)
- **Artifact-agnostic core + serialization + binder** — they never name a concrete
  artifact type; everything goes through the `Artifact` ABC and the registry.
- **Pure-stdlib core, no pydantic** — dataclasses; format knowledge only in
  `serialization/`; heavy deps (if ever) only inside the artifact that needs them.
- **String ids, no object cycles** — edges reference nodes by id; node wiring is
  recomputed on load (gives clean value-equality for round-trip tests). Ids are
  auto-generated, not author-invented (see the core-model note above). Artifact
  `__eq__`/`__hash__` is **value-based** (type + id + name + payload), which is what
  makes the round-trip `==` invariant hold. Puzzle generators are not serialized and
  are not compared.
- **GUI = producer, binder = consumer, model+serialization = the seam.** A visual
  hunt map is deferred (GUI-adjacent).

## Adding a type (the whole recipe)

1. **The artifact** (the serializable renderable). The full recipe — `type_name`,
   `@register_artifact`, `to_payload`/`from_payload`, a pure `render()`, and where it
   lives — is in `artifacts/ARTIFACTS.md` ("Writing a custom artifact"). A pure clue
   can reuse `TextArtifact`; several things together is a `CompositeArtifact`.
2. **The puzzle generator** (*only* if a single authoring object emits several
   artifacts, or distinct prompt-vs-answer pieces). Subclass `Puzzle`, set
   `type_name` (the id prefix), implement `_artifacts() -> list[Artifact]` building
   **all** the instances (ids via `self.artifact_id(name)`); the base
   `artifacts(name=None)` does the map/name dispatch. Emit every piece — where the
   prompt and answer views differ, that's *two distinctly-named instances* (e.g.
   cipher's `cipher`/`solution`, crossword's `crossword`/`solution`), not one with a
   flag. **Skip this step for an orphan artifact** — one with nothing to generate
   (text, image, a lat/long). It has no puzzle; the designer constructs it directly
   (see `ImageArtifact` in the mock hunt). Convenience constructors (`from_file`, …)
   go on the artifact as classmethods.

Where it lives: an **orphan** artifact goes in `artifacts/` (beside `text.py` /
`image.py`); a **puzzle-bound** artifact goes in `puzzles/` in the same file as its
generator. Export the new classes from that package's `__init__.py` and the package
`__init__.py`. **No edits to `core/`, `serialization/`, or `rendering/`.** Add a test
file mirroring the others (payload round-trip + render; for a generator, the
`artifacts()` map).

## Commands / the "done" bar

```bash
pip install -e ".[dev]"
pytest                 # 171 passed, 0 skipped
ruff check . && ruff format --check .
mypy src/puzzcombinator
python examples/hunts/mock_hunt/hunt.py   # regenerates its out/ (binder.html, solutions.html, …)
```
All green. (Pre-existing lint/format drift in `examples/hunts/jgg_hunt/hunt.py` — the
user's WIP hunt — is excluded from the bar; don't touch it without asking.) Still
worthwhile to restore as a habit: `pytest --cov=puzzcombinator` (100% on `core/`).
Conventions: `src/` layout, hatchling, `requires-python >=3.12` (PEP 695 generics
used), free-form `action` strings, commit messages end with the Co-Authored-By
trailer. Generated `examples/*_out/` and `*.html`/`*.svg` are gitignored.

## Current status & likely next steps

**Bottom-up refactor complete (see the banner).** All layers are migrated and green —
artifacts, puzzles + serialization + core, and now the binder. A puzzle emits all its
pieces in one `{name: Artifact}` map; a binder is whatever collection of renderings the
designer assembles (no player/answer-key tag — the `Audience` enum is gone). Documented
across `artifacts/ARTIFACTS.md`, `rendering/RENDERING.md`,
`puzzles/PUZZLES.md`, `core/GRAPHS.md`, and `app/APP.md`.

Likely next work (the GUI editor is the active frontier): the canvas-interaction
milestone (node dragging with positions persisted to the `app/canvas.py` sidecar,
pan/zoom, drawing connections — the natural point to adopt React Flow), and a browser
file-picker to replace the `PUZZ_GRAPH` env var. Wiring "generate a binder from the
editor" is now unblocked (the binder is real). The user is **new to frontend** — pace
GUI work incrementally.

Beyond that (defer unless asked): more puzzle types; the visual hunt-map
view (V1) / `action`-filtered subgraph binder views; GUI authoring layer; the
tracking/monitoring layer (layer 4 — the only place answer-checking would ever
live). Deferred GUI-readiness: the canvas/views channel (`app/canvas.py`) is defined
but positions aren't persisted yet (arrives with the drag/React-Flow milestone);
per-puzzle parameter metadata in the serialized format is still open.
