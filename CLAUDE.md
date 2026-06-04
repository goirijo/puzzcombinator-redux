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

## The core model (current — artifact-on-edge, rearchitected 2026-06-04)

A hunt is a **directed graph of actions**, and the graph is the **flow of
artifacts**:
- **`Edge`** carries `content: tuple[Artifact, ...]` — the artifacts flowing from
  one action to the next. There is no `Content` wrapper and no `text`/`data`/`puzzle`
  fields anymore.
- **`Artifact`** (in `rendering/fragment.py`) is the universal **thing that
  renders**: a registry-backed, serializable, **single-audience** renderable with
  `render() -> RenderFragment` (no audience arg). Envelope fields beside its
  type-specific `payload`: `name` (its key within the puzzle that made it),
  `audience` (`PLAYER` prints its own sheet / `GAME_MASTER` shows only in the answer
  key), `id` (unique within a hunt; names a player artifact's output file).
- **`Puzzle`** (in `puzzles/base.py`) is an authoring-time **generator**, *not*
  stored on edges and *not* serialized. `puzzle.artifacts(name=None, *, audience=
  Audience.PLAYER)` returns a `{name: Artifact}` map (or one artifact by name). It
  emits a player set and a game-master set; the designer places those artifacts on
  edges. A multi-piece puzzle (riddle lines, R4 grid+grille) is just a generator
  that emits several artifacts — placeable together or **scattered** across edges
  and assembled at a merge.
- **`Node`** is a **pure action** with a free-form **`action`** string
  (`"solve"`/`"find"`/`"move"`/…). **No `payload`, no `kind` enum.** Start/end are
  derived from topology (no incoming / no outgoing edges). The model is
  **stateless** — no player state, ever.
- **Ids are internal, not author-supplied.** `GraphBuilder.node(...)` returns a
  **handle** (the node id) you pass to `connect` — no fluent `.node().node()`
  chaining (connect still returns self). Omitted node ids auto-generate (`n1`, `n2`,
  …). Artifact ids default to `{type_name}-{uuid}`; a puzzle prefixes its emitted
  artifacts as `{puzzle.id}-{name}` so pass an explicit puzzle/artifact id only for
  readable `players/` filenames. `Graph.assemble` rejects duplicate **player**
  artifact ids (those name output files; GM artifacts are exempt).

Authoring: `connect(source, target, *artifacts)`. Example —
`connect(start, solve, *cipher.artifacts().values(), *cipher.artifacts(audience=GM).values())`,
then `connect(solve, find, TextArtifact("go to the kitchen"))`. The artifacts ride
the edges *into* the action that consumes them; a puzzle's answer is a separate
artifact you place on the outgoing edge.

## Package map (`src/puzzcombinator/`)

- **`core/`** — `graph.py` (Node, Edge, Graph), `builder.py` (`GraphBuilder`),
  `ordering.py` (`chronological_order` topo sort w/ branch+merge gating,
  `required_inputs`, `produced_outputs` — both return `list[Artifact]`). Stdlib
  only; artifact-agnostic (references only the `Artifact` ABC, for typing).
- **`artifacts/`** — the **orphan** artifacts (no puzzle behind them) and the
  registry: `registry.py` (`@register_artifact` / `build_artifact`), `text.py`
  (`TextArtifact`, the standalone clue), `image.py` (`ImageArtifact`, an inline-data-URI
  picture with `from_bytes`/`from_file` classmethods). Depends only on `rendering` +
  `errors`, so `puzzles/` builds on top of it without a cycle.
- **`puzzles/`** — `base.py` (`Puzzle` generator ABC) and the puzzle types, each
  pairing a `Puzzle` generator with its `Artifact` subclass(es): `cipher.py`,
  `crossword.py`, `r4.py`, `riddle.py`. Depends on `artifacts` + `rendering` +
  `errors`. (An artifact with no puzzle logic — text, image, a future lat/long — is
  an *orphan* and lives in `artifacts/`, not here.)
- **`serialization/`** — `codec.py` (Graph ↔ dict; the only place that knows the
  on-disk shape; each edge's content is a list of artifacts round-tripped via the
  registry as `{type,id,name,audience,payload}`), `__init__.py` (`to_json`/`from_json`
  stdlib, `to_yaml`/`from_yaml` lazy optional), `schema.py` (`SCHEMA_VERSION = "2"`).
  The interchange seam for a future GUI/monitoring layer. Keystone invariant:
  `from_json(to_json(g)) == g`.
- **`rendering/`** — `fragment.py` (`RenderFragment` {markup, kind html|svg,
  styles}, `Audience`, and the `Artifact` ABC), `presets.py` (fragment factories),
  `binder.py` (the output layer). Artifact-agnostic.

## Output / the binder

`rendering/binder.py` turns a graph into a **bundle**:
- `game_master_binder(graph) -> str` — one HTML doc: a page per node (topological
  order) rendering **all** artifacts on its **incoming and outgoing** edges (both
  `PLAYER` and `GAME_MASTER` ones, so the answer key shows the player pieces *and*
  the revealed answers) + a production checklist.
- `player_pages(graph) -> dict[path,str]` — one printable per **`PLAYER`** artifact,
  keyed `players/<artifact.id>.{html,svg}`. `GAME_MASTER` artifacts render only in
  the binder and produce no file.
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
  `__eq__`/`__hash__` is **value-based** (type + id + name + audience + payload),
  which is what makes the round-trip `==` invariant hold. Puzzle generators are not
  serialized and are not compared.
- **GUI = producer, binder = consumer, model+serialization = the seam.** A visual
  hunt map is deferred (GUI-adjacent).

## Adding a type (the whole recipe)

1. **The artifact** (the serializable renderable). Subclass `Artifact`, decorate
   `@register_artifact`, set `type_name`, implement `to_payload` /
   `from_payload(*, name, audience, id, payload)` / `render() -> RenderFragment`
   (a pure function of the payload — no audience branching). `__init__` takes the
   type-specific data plus `*, name=..., audience=Audience.PLAYER, id=None` and
   passes the last three to `super().__init__(...)`. A pure clue type can reuse
   `TextArtifact`.
2. **The puzzle generator** (*only* if a single authoring object emits several
   artifacts or needs answer-vs-blank logic). Subclass `Puzzle`, set `type_name`
   (the id prefix), implement `_artifacts(audience) -> list[Artifact]` building the
   per-audience instances (ids via `self.artifact_id(name)`); the base
   `artifacts(name=None, *, audience=...)` does the map/name dispatch. Put the
   audience decision (what's blank vs revealed) *here*, baked into each instance's
   payload. **Skip this step for an orphan artifact** — one with nothing to generate
   (text, image, a lat/long). It has no puzzle; the designer constructs it directly,
   building each single-audience instance by hand (see `ImageArtifact`'s player vs
   game-master use in the mock hunt). Convenience constructors (`from_file`, …) go on
   the artifact as classmethods.

Where it lives: an **orphan** artifact goes in `artifacts/` (beside `text.py` /
`image.py`); a **puzzle-bound** artifact goes in `puzzles/` in the same file as its
generator. Export the new classes from that package's `__init__.py` and the package
`__init__.py`. **No edits to `core/`, `serialization/`, or `rendering/`.** Add a test
file mirroring the others (payload round-trip + render; for a generator, the
`artifacts()` map + audience behavior).

## Commands / the "done" bar

```bash
pip install -e ".[dev]"
pytest --cov=puzzcombinator            # 100% coverage on core/ is required
ruff check . && ruff format --check . && mypy src/puzzcombinator   # must be clean
python examples/hunts/mock_hunt/hunt.py      # regenerates examples/hunts/mock_hunt/out/
```
Conventions: `src/` layout, hatchling, `requires-python >=3.12` (PEP 695 generics
used), free-form `action` strings, commit messages end with the Co-Authored-By
trailer. Generated `examples/*_out/` and `*.html`/`*.svg` are gitignored.

## Current status & likely next steps

Working, fully tested. Four puzzle types (cipher, crossword, R4, riddle) plus two
orphan artifacts (text, image). Full bundle output (binder + players/).
`examples/hunts/mock_hunt/hunt.py` is the end-to-end reference (every puzzle type,
the image artifact, a three-way converging branch, a physical step).

Not yet built (defer unless asked): more puzzle types; the visual hunt-map view
(V1) / `action`-filtered subgraph binder views; GUI authoring layer; the
tracking/monitoring layer (layer 4 — the only place answer-checking would ever
live). Deferred GUI-readiness: optional node x/y positions + per-puzzle parameter
metadata in the serialized format.
