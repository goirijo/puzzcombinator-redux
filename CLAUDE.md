# CLAUDE.md — puzzcombinator

Orientation for a fresh session. Read this, skim `README.md` and
`examples/mock_hunt/hunt.py`, and you're caught up — you do **not** need any prior
chat transcript. Deeper rationale lives in the auto-loaded memory files
(`design-principles`, `roadmap`) and in `git log` (commit messages are detailed).

## What this is

A modular Python library for **authoring treasure-hunt games**. It is a
**design-time tool for the hunt's designer**: create puzzles, compose them into a
hunt graph, and generate printable materials. It does **not** play or grade a
hunt — there is no answer-checking anywhere (in a physical hunt, correctness is
implicit when one puzzle's output is the next one's input). Live
progress-tracking is a future, separate layer.

## The core model (current — rearchitected 2026-05-31)

A hunt is a **directed graph of actions**:
- **`Edge`** carries **`Content`** = `text` (clue/word/object) + `data` (JSON-safe
  dict) + optional **`puzzle`** (the artifact the player works on). A puzzle is
  just *optional richness* on content — there is **no "clue vs artifact"
  distinction**.
- **`Node`** is a **pure action** with a free-form **`action`** string
  (`"solve"`/`"find"`/`"move"`/…). **No `payload`, no `kind` enum.** Start/end are
  derived from topology (no incoming / no outgoing edges).
- A single puzzle may span several nodes (find → solve). The model is
  **stateless** — no player state, ever.
- **Ids are internal, not author-supplied.** `GraphBuilder.node(...)` returns a
  **handle** (the node id) you pass to `connect` — no fluent `.node().node()`
  chaining (connect still returns self). Omitted node ids auto-generate (`n1`, `n2`,
  …); omitted puzzle ids auto-generate `{type_name}-{uuid}`. A puzzle id is *not* a
  cross-reference key (nothing looks a puzzle up by it) — it only names output
  files, so it's optional; pass an explicit one only for readable `players/`
  filenames. `Graph.assemble` rejects duplicate puzzle ids.

Example: `start → [cipher] → solve → "go to the kitchen" → find → [crossword] → solve → "ROAD" → …`
(the bracketed puzzles ride the edges *into* the action that solves them).

## Package map (`src/puzzcombinator/`)

- **`core/`** — `graph.py` (Content, Node, Edge, Graph), `builder.py`
  (`GraphBuilder`), `ordering.py` (`chronological_order` topo sort w/ branch+merge
  gating, `required_inputs`, `produced_outputs`). Stdlib only; puzzle-agnostic.
- **`puzzles/`** — `base.py` (`Puzzle` ABC), `registry.py` (`@register_puzzle` /
  `build_puzzle`), and the puzzle types: `cipher.py` (Caesar), `crossword.py`,
  `r4.py` (turning-grille decoder). Depends on `rendering.fragment` + `errors`.
- **`serialization/`** — `codec.py` (Graph ↔ dict; the only place that knows the
  on-disk shape; puzzles round-trip via the registry as `{type,id,payload}` inside
  edge content), `__init__.py` (`to_json`/`from_json` stdlib, `to_yaml`/`from_yaml`
  lazy optional), `schema.py` (`SCHEMA_VERSION`). The interchange seam for a future
  GUI/monitoring layer. Keystone invariant: `from_json(to_json(g)) == g`.
- **`rendering/`** — `fragment.py` (`RenderFragment` {markup, kind html|svg,
  styles}, `Audience`, `Artifact`), `binder.py` (the output layer). Puzzle-agnostic.

## Output / the binder

`rendering/binder.py` turns a graph into a **bundle**:
- `game_master_binder(graph) -> str` — one HTML doc: a page per node (topological
  order) showing the content on its **incoming and outgoing** edges (puzzles
  rendered `GAME_MASTER` = answers shown) + a production checklist.
- `player_pages(graph) -> dict[path,str]` — one printable per edge-puzzle, keyed
  `players/<puzzle.id>-<slug>.{html,svg}`.
- `hunt_bundle(graph) -> dict[path,str]` (pure) and `write_bundle(bundle, dir)`
  (the only filesystem I/O).
The binder holds **no puzzle-specific CSS** — each `RenderFragment` carries its own
`styles`, which the binder aggregates. So a new puzzle needs zero binder edits.

## Key design rules (don't violate without discussing)

- **Authoring-only** — no `Validator`/`check`/`is_solved`/answer-gating anywhere.
- **Loose I/O coupling** — a puzzle's solution is NOT auto-linked to the outgoing
  edge clue; the designer hand-writes it. (Revisit only when drift causes real
  bugs; then add a puzzle `outputs()` accessor — not before.)
- **Puzzle-agnostic core + serialization + binder** — they never name a concrete
  puzzle type; everything goes through the `Puzzle` ABC and the registry.
- **Pure-stdlib core, no pydantic** — dataclasses; format knowledge only in
  `serialization/`; heavy deps (if ever) only inside the puzzle that needs them.
- **String ids, no object cycles** — edges reference nodes by id; node wiring is
  recomputed on load (gives clean value-equality for round-trip tests). Ids are
  auto-generated, not author-invented (see the core-model note above). Puzzle
  `__eq__`/`__hash__` is still id-based; switching it to value-based (`type` +
  `payload`, drop id) is a noted, deferred follow-up.
- **GUI = producer, binder = consumer, model+serialization = the seam.** A visual
  hunt map is deferred (GUI-adjacent).

## Adding a puzzle type (the whole recipe)

New file in `puzzles/`, subclass `Puzzle`, decorate `@register_puzzle`, set
`type_name`, implement `to_payload` / `from_payload(id, payload)` /
`render(audience) -> RenderFragment`. `__init__` takes `id: str | None = None`
first and passes it to `super().__init__(id)` (the base auto-generates when None);
convenience constructors put `id` last as an optional keyword. Override
`player_artifacts()` only if the puzzle prints as several separate sheets (see
`r4.py`). Export it in `puzzles/__init__.py` and the package `__init__.py`. **No
edits to `core/`, `serialization/`, or `rendering/`.** Add a test file mirroring
the others.

## Commands / the "done" bar

```bash
pip install -e ".[dev]"
pytest --cov=puzzcombinator            # 100% coverage on core/ is required
ruff check . && ruff format --check . && mypy src/puzzcombinator   # must be clean
python examples/mock_hunt/hunt.py      # regenerates examples/mock_hunt/out/
```
Conventions: `src/` layout, hatchling, `requires-python >=3.12` (PEP 695 generics
used), free-form `action` strings, commit messages end with the Co-Authored-By
trailer. Generated `examples/*_out/` and `*.html`/`*.svg` are gitignored.

## Current status & likely next steps

Working, fully tested. Five puzzle types (cipher, crossword, R4, riddle, image).
Full bundle output (binder + players/). `examples/mock_hunt/hunt.py` is the end-to-end
reference (all five puzzle types, a three-way converging branch, a physical step).

Not yet built (defer unless asked): more puzzle types; the visual hunt-map view
(V1) / `action`-filtered subgraph binder views; GUI authoring layer; the
tracking/monitoring layer (layer 4 — the only place answer-checking would ever
live). Deferred GUI-readiness: optional node x/y positions + per-puzzle parameter
metadata in the serialized format.
