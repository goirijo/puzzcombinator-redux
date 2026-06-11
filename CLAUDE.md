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

## ⚠️ Refactor in progress (bottom-up rebuild, started 2026-06-04)

We are rebuilding the library **one layer at a time, lowest first**, to keep each
change small.

- **Phase 1 — Artifact layer — done.** Minimal single-thing primitives
  (`text`/`image`/`svg`), a `CompositeArtifact`, the registry envelope helpers, and
  the single-artifact file writers. See `src/puzzcombinator/artifacts/ARTIFACTS.md`.
- **Phase 2 — Puzzles + serialization + core hooks — done (green).** The puzzle
  generators, `serialization/codec.py`, and `core/graph.py`'s duplicate-id check are
  migrated; the old player/game-master split (and the `Audience` enum) is **gone from
  the codebase**. A puzzle now emits *all* its pieces — the prompt pieces and the
  answer key — as one flat `{name: Artifact}` map; which piece reaches a player vs.
  the answer key is a placement decision. (Further puzzle work may still follow — this
  layer is migrated and green, not necessarily "finished.")

**Only `rendering/binder.py` remains stale** — the **last** layer to migrate (plus
its skipped tests in `tests/rendering/test_binder.py` + `tests/test_e2e.py`, and the
`examples/hunts/mock_hunt/` example). It must not constrain the layers below it —
break it freely. Everything else is green: `pytest` is **136 passed / 10 skipped**,
`ruff` + `mypy` clean.

## The core model (artifact-on-edge, rearchitected 2026-06-04)

A hunt is a **directed graph of actions**, and the graph is the **flow of
artifacts**:
- **`Edge`** carries `content: tuple[Artifact, ...]` — the artifacts flowing from
  one action to the next. There is no `Content` wrapper and no `text`/`data`/`puzzle`
  fields anymore.
- **`Artifact`** (in `rendering/fragment.py`) is the universal **thing that
  renders** carried on edges: a registry-backed, serializable renderable. **Its
  primitives, composite, custom-type recipe, and
  serialization are documented in full in `src/puzzcombinator/artifacts/ARTIFACTS.md`
  — read that for the artifact layer; the bullet here only covers how artifacts ride
  the graph.**
- **`Puzzle`** (in `puzzles/base.py`) is an authoring-time **generator**, *not*
  stored on edges and *not* serialized. `puzzle.artifacts(name=None)` returns a
  `{name: Artifact}` map (or one artifact by name) — *all* the pieces the puzzle is
  made of, prompt and answer key alike. The designer places those artifacts on edges.
  A multi-piece puzzle (riddle lines + full text, R4's blanks/grille/grid/text,
  cipher's ciphertext/shift/solution) is just a generator that emits several
  artifacts — placeable together or **scattered** across edges and assembled at a
  merge.
- **`Node`** is a **pure action** with a free-form **`action`** string
  (`"solve"`/`"find"`/`"move"`/…). **No `payload`, no `kind` enum.** Start/end are
  derived from topology (no incoming / no outgoing edges). The model is
  **stateless** — no player state, ever.
- **Ids are internal, not author-supplied.** `GraphBuilder.node(...)` returns a
  **handle** (the node id) you pass to `connect` — no fluent `.node().node()`
  chaining (connect still returns self). Omitted node ids auto-generate (`n1`, `n2`,
  …). Artifact ids default to `{type_name}-{uuid}`; a puzzle prefixes its emitted
  artifacts as `{puzzle.id}-{name}` so pass an explicit puzzle/artifact id only for
  readable `players/` filenames. The same artifact may be **reused** on several
  edges (one piece used in multiple places); `Graph.assemble` only rejects a
  repeated id *within a single edge*.

Authoring: `connect(source, target, *artifacts)`. Example —
`connect(start, solve, *cipher.artifacts().values())`, then
`connect(solve, find, TextArtifact("go to the kitchen"))`. The artifacts ride the
edges *into* the action that consumes them; a puzzle's answer is a separate artifact
you place on the outgoing edge.

## Package map (`src/puzzcombinator/`)

- **`core/`** — `graph.py` (Node, Edge, Graph), `builder.py` (`GraphBuilder`),
  `ordering.py` (`chronological_order` topo sort w/ branch+merge gating,
  `required_inputs`, `produced_outputs` — both return `list[Artifact]`). Stdlib
  only; artifact-agnostic (references only the `Artifact` ABC, for typing).
- **`artifacts/`** — the **orphan** artifacts (`text.py`, `image.py`, `svg.py`), the
  composite (`composite.py`), and the registry (`registry.py`). Each artifact declares
  its own native file form via `native()` (the `Artifact` ABC default serves an svg-kind
  render as `.svg`; `text`/`image` override). Depends only on `rendering` + `errors`, so
  `puzzles/` builds on top of it without a cycle. **Fully documented in
  `artifacts/ARTIFACTS.md`** — go there for the types, the custom-type recipe, and
  serialization.
- **`puzzles/`** — `base.py` (`Puzzle` generator ABC) and the puzzle types, each
  pairing a `Puzzle` generator with its `Artifact` subclass(es): `cipher.py`,
  `crossword.py`, `r4.py`, `riddle.py`. Depends on `artifacts` + `rendering` +
  `errors`. (An artifact with no puzzle logic — text, image, a future lat/long — is
  an *orphan* and lives in `artifacts/`, not here.)
- **`serialization/`** — `codec.py` (Graph ↔ dict; the only place that knows the
  on-disk shape; each edge's content is a list of artifacts round-tripped via the
  registry as `{type,id,name,payload}` — it reuses the registry's
  `artifact_to_dict`/`artifact_from_dict`), `__init__.py` (`to_json`/`from_json`
  stdlib, `to_yaml`/`from_yaml` lazy optional), `schema.py` (`SCHEMA_VERSION = "2"`).
  The interchange seam for a future GUI/monitoring layer. Keystone invariant:
  `from_json(to_json(g)) == g`.
- **`rendering/`** — `fragment.py` (`RenderFragment` {markup, kind html|svg,
  styles} and the `Artifact` ABC, incl. `render()` + `native()`), `presets.py` (fragment
  factories), `export.py` (the agnostic single-artifact file writers: `html_document`,
  `write_html`, `write_artifact`, `write_artifacts` — all need only the ABC), `binder.py`
  (the whole-hunt output layer — **STALE, the last layer still to migrate**).
  Artifact-agnostic. **Documented in `rendering/RENDERING.md`.**

## Output / the binder

> **Stale — the last layer to migrate.** `binder.py` has not been rebuilt for the
> current model; **how it routes a piece to a player printable vs. the answer key**
> (now that nothing tags an artifact) is the open question of its phase, and its
> tests are skipped. The shape below is the *target*, not what runs.

`rendering/binder.py` turns a graph into a **bundle**:
- `game_master_binder(graph) -> str` — one HTML doc: a page per node (topological
  order) rendering **all** artifacts on its **incoming and outgoing** edges (so the
  answer key shows the prompt pieces *and* the revealed answers) + a production
  checklist.
- `player_pages(graph) -> dict[path,str]` — one printable per artifact, keyed
  `players/<artifact.id>.{html,svg}` (which pieces become player files is the routing
  question above).
- `hunt_bundle(graph) -> dict[path,str]` (pure) and `write_bundle(bundle, dir)`
  (the only filesystem I/O).
The binder holds **no artifact-specific CSS** — each `RenderFragment` carries its
own `styles`, which the binder aggregates. So a new artifact needs zero binder edits.

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
pytest                 # 136 passed, 10 skipped (binder + e2e, deferred)
ruff check . && ruff format --check .
mypy src/puzzcombinator
```
Everything except the binder is green; the 10 skips are `tests/rendering/test_binder.py`
and `tests/test_e2e.py`, both awaiting the binder phase. The remaining bar to restore
once the binder lands: `pytest --cov=puzzcombinator` (100% on `core/`) and
`python examples/hunts/mock_hunt/hunt.py` regenerating its `out/`.
Conventions: `src/` layout, hatchling, `requires-python >=3.12` (PEP 695 generics
used), free-form `action` strings, commit messages end with the Co-Authored-By
trailer. Generated `examples/*_out/` and `*.html`/`*.svg` are gitignored.

## Current status & likely next steps

**Mid bottom-up refactor (see the banner).** Phases 1–2 are done and green: the
artifact layer, and the puzzle generators + `serialization/codec.py` +
`core/graph.py`'s duplicate-id check, with the player/game-master split removed
entirely (the `Audience` enum is gone). A puzzle emits all its pieces in one
`{name: Artifact}` map; routing a piece to a player vs. the answer key is a placement
decision deferred to the binder. Documented across `artifacts/ARTIFACTS.md`,
`rendering/RENDERING.md`, `puzzles/AUTHORING_PUZZLES.md`, `core/AUTHORING_GRAPHS.md`.

**Next (and last) phase: the binder.** `rendering/binder.py` is the only stale
module. Its open design question is **how it routes a piece to a player printable vs.
the answer key** now that nothing tags an artifact — most likely derived from how/
where the designer placed it. Migrating it also unskips `tests/rendering/test_binder.py`
+ `tests/test_e2e.py` (rewrite their assertions to the new routing) and gets
`examples/hunts/mock_hunt/hunt.py` green end-to-end. The binder must not constrain the
layers below it — break it freely while finishing lower work.

Beyond the refactor (defer unless asked): more puzzle types; the visual hunt-map
view (V1) / `action`-filtered subgraph binder views; GUI authoring layer; the
tracking/monitoring layer (layer 4 — the only place answer-checking would ever
live). Deferred GUI-readiness: optional node x/y positions + per-puzzle parameter
metadata in the serialized format.
