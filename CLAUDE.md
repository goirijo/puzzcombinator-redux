# CLAUDE.md — puzzcombinator

Orientation for a fresh session. Read this, skim `README.md` and
`examples/hunts/mock_hunt/hunt.py`, and you're caught up — you do **not** need any prior
chat transcript. Deeper rationale lives in the auto-loaded memory files
(`design-principles`, `roadmap`), the on-demand package docs (linked below), and `git log`
(commit messages are detailed).

## What this is

A modular Python library for **authoring treasure-hunt games**. It is a
**design-time tool for the hunt's designer**: create puzzles, compose them into a
hunt graph, and generate printable materials. It does **not** play or grade a
hunt — there is no answer-checking anywhere (in a physical hunt, correctness is
implicit when one puzzle's output is the next one's input). Live
progress-tracking is a future, separate layer.

The library layers — **artifacts → puzzles → serialization → core → rendering** — are
complete and green. A puzzle emits all its pieces (prompt pieces + answer key) as one flat
`{name: Artifact}` map; there's no player-vs-answer-key tag. The active frontier is the
**GUI editor** (`frontend/`). For how the bottom-up rebuild got here, see `git log`.

## Architecture — the model and the layer map

The model (artifact-on-edge graph), the layered stack + its strict downward dependency
direction, and the **generated → stored → displayed** data lifecycle all live in
**[`ARCHITECTURE.md`](ARCHITECTURE.md)** — read it once to orient. Per-layer detail is in
the package docs it links to (`artifacts/ARTIFACTS.md`, `puzzles/PUZZLES.md`,
`core/GRAPHS.md`, `rendering/RENDERING.md`, `app/APP.md`). That is the canonical
architecture reference; this file is the agent quickstart.

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

A **binder** is just *a collection of renderings the designer assembles* — there's no
player-vs-answer-key routing and no opinion about what a hunt "should" output. Three nesting
levels mirror `CompositeArtifact`: **`Section`** (one rendering) → **`Chapter`** (titled
group) → **`Binder`** (a collection of chapters → one standalone HTML doc; layout via the
`title`/`chapter_divider`/`section_divider` fields). Pure (renders to a string) and
artifact-agnostic — every fragment's CSS aggregates and de-duplicates into one `<head>` (via
`dedupe_css` in `rendering/fragment.py`), so a new artifact needs **zero binder edits**. Full
API + the headline uses (answer key, page-per-node walkthrough) are in `rendering/RENDERING.md`
and `examples/hunts/mock_hunt/hunt.py`.

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
- **GUI = producer, binder = consumer, model+serialization = the seam.**

## Adding a type (the short version)

Full recipe in `artifacts/ARTIFACTS.md` ("Writing a custom artifact") and `puzzles/PUZZLES.md`.
The shape:

1. **The artifact** (the serializable renderable): `type_name`, `@register_artifact`,
   `to_payload`/`from_payload`, a pure `render()`. A pure clue can reuse `TextArtifact`;
   several things together is a `CompositeArtifact`.
2. **The puzzle generator** — *only* if one authoring object emits several artifacts or
   distinct prompt-vs-answer pieces. Subclass `Puzzle`, set `type_name`, implement
   `_artifacts()` building **all** instances (ids via `self.artifact_id(name)`). Emit every
   piece as distinctly-named instances (cipher's `cipher`/`solution`), never one with a flag.
   **Skip this for an orphan artifact** (text, image, lat/long) — the designer constructs it
   directly.

Where it lives: an **orphan** artifact → `artifacts/`; a **puzzle-bound** artifact →
`puzzles/` (same file as its generator). Export from the package `__init__.py`s. **No edits
to `core/`, `serialization/`, or `rendering/`.** Add a test mirroring the others.

## Commands / the "done" bar

```bash
pip install -e ".[dev]"
pytest                                     # all green, 0 skipped
ruff check . && ruff format --check .
mypy src/puzzcombinator
python examples/hunts/mock_hunt/hunt.py    # regenerates its out/ (binder.html, solutions.html, …)
```

Conventions: `src/` layout, hatchling, `requires-python >=3.12` (PEP 695 generics used),
free-form `action` strings, commit messages end with the Co-Authored-By trailer. Generated
`examples/*_out/` and `*.html`/`*.svg` are gitignored. **`examples/hunts/jgg_hunt/hunt.py` is
the user's WIP hunt — excluded from the bar; don't touch it without asking.**

## Status & next steps

The library is complete; the **GUI editor** (`frontend/`) is the active frontier. It draws the
hunt graph and edits content — create/delete nodes/edges/loose artifacts, move artifacts
pool↔edge, a per-view show-unplaced toggle — all undoable. Storage: the `HuntDocument.unplaced`
pool + workspace `View` flags. Frontend: three Zustand stores (`graphStore` undoable,
`workspaceStore`, `selectionStore`); panels subscribe to stores (no props). See
`frontend/FRONTEND.md` (frontend) and `app/APP.md` (the wire seam) for current detail.

**The backlog lives in [`ROADMAP.md`](ROADMAP.md)** — a *tracking* doc, not a work queue:
nothing there enters development until a prompt makes it the explicit subject (the
`build-only-whats-asked` rule). Park new ideas there; don't code them speculatively.

The user is **new to frontend** — pace GUI work incrementally. Later layers (more puzzle types,
GUI authoring, the tracking/monitoring layer where answer-checking would live) stay deferred
unless asked.
