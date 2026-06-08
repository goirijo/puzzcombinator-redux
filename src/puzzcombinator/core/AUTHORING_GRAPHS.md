# Authoring a hunt graph

The companion guide, [`AUTHORING_PUZZLES.md`](../puzzles/AUTHORING_PUZZLES.md),
showed how to build a single self-contained puzzle. This one is the next layer
up: **composing puzzles — and the steps between them — into a whole hunt.** You
will lay out the path players take, hang puzzles on it, branch it so several
threads run at once, merge those threads back together, and finally turn the
result into printable materials. The running example is the shipped reference
hunt, [`examples/hunts/mock_hunt/hunt.py`](../../../examples/hunts/mock_hunt/hunt.py); read
this with that file open.

> **Scope.** A hunt is a **directed graph of actions**. Everything here is the
> *graph layer* — it is deliberately **artifact-agnostic**: it never names a
> concrete artifact type, only the `Artifact` interface. That is why adding an
> artifact type never forces a graph-layer edit, and why authoring a graph never
> cares which artifacts are on an edge.
>
> Like the puzzle layer, the graph layer is **authoring-only and stateless**.
> There is no player state, no "current position", no answer-checking, and no
> notion of *who* is solving — ever. The model describes the hunt's structure;
> tracking a live playthrough is a separate future layer.

---

## The mental model

Three types carry the whole model (`core/graph.py`):

| Type | What it is | In the hunt |
|---|---|---|
| **`Node`** | a **pure action** with a free-form `action` string (`"solve"`, `"find"`, `"move"`, …) | a step the players *do* |
| **`Edge`** | a directed connection from one node to another, carrying a tuple of `Artifact`s | the information that flows between steps |
| **`Artifact`** | a serializable **thing that renders** (a clue, a cipher, a grid) | one piece of what a step hands to the next |

A **`Puzzle`** is an authoring-time *generator* of artifacts (see
[`AUTHORING_PUZZLES.md`](../puzzles/AUTHORING_PUZZLES.md)); it is not part of the
graph — you place the artifacts it emits.

The shape of the whole thing follows from a few rules:

- **Artifacts live on edges, not nodes.** An edge carries a flat list of artifacts —
  the information flowing into an action. There is **no "clue vs puzzle"
  distinction**: a clue is a `TextArtifact`, a cipher is a `CipherArtifact`, and the
  binder renders whichever are present. The idiom to internalise: **a puzzle's
  artifacts ride the edge _into_ the action that consumes them.**
- **Nodes are pure actions — no payload, no "kind".** A node consumes its incoming
  edges and produces its outgoing ones. The `action` string is free-form and
  open-ended; there is no fixed enum to pick from.
- **Start and end are _derived from topology_, never declared.** A start node is
  simply one with no incoming edges; an end node has no outgoing edges. You never
  flag a node as start/end — you just don't wire anything into (or out of) it.
- **Identity is by string `id`.** Edges reference nodes by id; per-node wiring is
  *recomputed* on build/load, never stored. This keeps the object graph acyclic
  and gives clean value-equality for serialization round-trips.

Here is the reference hunt's whole shape — a branch into three parallel threads
that merge, then a physical step to the prize:

```
start
  -[gate cipher]-> solve_gate         (decodes to: LIBRARY, ATTIC, GARDEN)
       -"Search the LIBRARY."-> find_library -[crossword]-> solve_cw     -"ROAD"-------.
       -"Search the ATTIC."--> find_attic   -[R4 grille]-> solve_grille -"FIFTH STEP"-+
       -"Search the GARDEN."-> find_garden  -[riddle]----> solve_riddle -"SUNDIAL"----+
                                                                                      |
                                       combine  <-(all three converge here)----------'
                                          -[patio photo]-> examine
                                             -"Lift the loose flagstone…"-> vault (physical)
                                                -"Open the cabinet!"-> end
```

Read the bracketed `[...]` as a puzzle's artifacts riding *that edge into* the next
action, and the `"..."` as a `TextArtifact` clue the designer placed on the edge.

---

## Step 1 — Place the actions (`node`)

Build a graph with `GraphBuilder` (`core/builder.py`). Each `node(...)` returns a
**handle** that you capture in a variable and wire edges with — you never invent
or type a node id:

```python
from puzzcombinator import GraphBuilder

builder = GraphBuilder()
start = builder.node(label="Kickoff")
solve_gate = builder.node(action="solve", label="Opening cipher")
find_library = builder.node(
    action="find",
    label="The library",
    notes="Tape the crossword inside the red book in the 800s.",
)
# …then wire each edge right after you make its target (step 2), and builder.build().
```

The signature is `node(id=None, *, action=None, label=None, notes=None) -> str`,
and it **returns the new node's id** — the handle you pass to `connect`:

- **the handle (`id`)** — `node()` hands back a unique id; keep it in a variable
  (`start`, `solve_gate`, …). The id is internal bookkeeping: **omit it and the
  builder generates a unique one for you**, so you never have to invent or track
  one. Nothing user-facing depends on it — the binder shows a node's `label`, not
  its id. Pass an explicit `id="…"` only when you want a stable, readable handle
  (e.g. to assert on it in a test). A duplicate explicit id raises `GraphError`.
- **`action`** — the free-form verb for what players do here (`"solve"`, `"find"`,
  `"combine"`, `"examine"`, `"unlock"`, …). Invent whatever reads well; nothing
  validates it against a fixed set. A start/end node often has *no* action — it's
  just a labelled entry or exit.
- **`label`** — a human-readable heading shown in the game-master binder.
- **`notes`** — free-form designer text, also printed in the binder. This is where
  staging instructions live ("hide the grille pieces in the steamer trunk") — the
  physical-world half of the hunt the graph can't otherwise capture.

> **Capture the handle; don't guess an id.** Because ids are auto-generated, the
> only reliable way to refer to a node is the value `node()` returned. Passing a
> made-up string (a label, say) to `connect` leaves the edge dangling and `build()`
> raises `GraphError`.

> **Don't encode start/end as a node property** — there is no such property. Just
> leave the first node with nothing wired in and the last with nothing wired out;
> `start_nodes()` / `end_nodes()` derive them from the wiring (step 5).

---

## Step 2 — Connect them, carrying content (`connect`)

`connect(source, target, *artifacts, id=None)` takes the **handles** from step 1
and the artifacts that flow along the edge. Because `node()` hands back its handle
the moment you call it, the clearest way to author is to **interleave**: create a
node, then immediately wire the edge that feeds it. Each step reads as a unit — the
action next to the artifacts that flow into it — instead of one giant chain you have
to cross-reference against the node list:

```python
from puzzcombinator import TextArtifact

builder = GraphBuilder()

start        = builder.node(label="Kickoff")
solve_gate   = builder.node(action="solve", label="Opening cipher")
# a puzzle's artifacts ride the edge *into* the action that solves it — the whole
# set: the ciphertext to decode and the revealed answer for the answer key.
builder.connect(start, solve_gate, *gate.artifacts().values())

find_library = builder.node(action="find", label="The library")
builder.connect(solve_gate, find_library, TextArtifact("Search the LIBRARY."))  # the clue to reach it

solve_cw     = builder.node(action="solve", label="Crossword")
builder.connect(find_library, solve_cw, *crossword.artifacts().values())

combine      = builder.node(action="combine")
builder.connect(solve_cw, combine, TextArtifact("ROAD"))  # the solution you place on the outgoing edge (step 3)

hunt = builder.build()
```

You can only wire **backward** — `connect` needs handles that already exist, so
create a node before the edge that points at it. `connect` does return the builder,
so a short linear run *can* be chained
(`builder.connect(a, b, …).connect(b, c, …).build()`); but one `connect` per line
stays readable once the graph branches and merges (step 4), so prefer it.

The signature is `connect(source, target, *artifacts, id=None)`, where
`source`/`target` are node handles:

- **`*artifacts`** are the artifact instances flowing along the edge, in order. Pass
  a `TextArtifact` for a clue, a single artifact you got from `puzzle.artifacts(name)`,
  or spread a whole set with `*puzzle.artifacts().values()` to place every piece a
  puzzle emits (its prompt pieces and its answer key alike).
- An edge may carry **nothing** (pass no artifacts) — a pure structural link.
- **`id`** is optional. By default the edge id is `"{source}->{target}"`, with
  `#2`, `#3`, … appended if you connect the same pair more than once. Pass `id=`
  only when you want a stable, meaningful handle. A duplicate edge id raises
  `GraphError`.

---

## Step 3 — The input/output idiom (and why it's loosely coupled)

This is the single most important convention in the whole layer, so it gets its
own step.

**A puzzle's artifacts hang on the edge that flows _into_ the node where it gets
solved.** The node is the `solve` action; the edge before it carries the puzzle's
pieces the players work on; the edge *after* it carries the puzzle's answer as a
plain `TextArtifact`, which becomes the next step's input. In the reference hunt:

```python
    .connect(find_library, solve_cw, *crossword.artifacts().values())  # in:  the crossword
    .connect(solve_cw, combine, TextArtifact("ROAD"))                  # out: its solution
```

Crucially, **the library does _not_ auto-link a puzzle's solution to its outgoing
clue.** You write `TextArtifact("ROAD")` by hand. This loose coupling is deliberate:

- An artifact is self-contained and has no idea which edge carries it or what comes
  next (see the puzzle guide's scope note). Forcing the graph to reach into a puzzle
  for "the answer" would break that isolation and require every puzzle to expose a
  machine-readable solution — which several puzzle types can't cleanly do.
- The clue a player reads next is usually *not* verbatim the puzzle's answer — it's
  a sentence you phrase ("By the SUNDIAL, pace the ROAD…"). Authoring that by hand
  is a feature, not a gap.

The trade-off is that the two can drift (you change the crossword's emergent word
but forget to update the outgoing `text`). That is an accepted design cost; the
deliberate fix, *if drift ever causes real bugs*, is to add a puzzle `outputs()`
accessor — **not before**. For now, when you change a puzzle's answer, update its
outgoing edge by hand.

You can inspect what each step consumes and produces with the structural queries
in `core/ordering.py`:

```python
from puzzcombinator import required_inputs, produced_outputs

required_inputs(hunt, solve_cw)    # [CrosswordArtifact(...)]  — the artifacts it consumes
produced_outputs(hunt, solve_cw)   # [TextArtifact("ROAD")]    — the artifact it yields
```

(The queries take a node id; pass the same handle `node()` returned. Both return a
flat `list[Artifact]` across the node's edges.)

---

## Step 4 — Branch and merge

Non-linear hunts fall out of plain topology — no special construct:

- **A branch is just a node with several outgoing edges.** The reference hunt's
  `solve_gate` sends players to three places at once:

  ```python
      .connect(solve_gate, find_library, TextArtifact("Search the LIBRARY."))
      .connect(solve_gate, find_attic, TextArtifact("Search the ATTIC."))
      .connect(solve_gate, find_garden, TextArtifact("Search the GARDEN."))
  ```

- **A merge is just a node with several incoming edges.** The three threads
  converge on `combine`:

  ```python
      .connect(solve_cw, combine, TextArtifact("ROAD"))
      .connect(solve_grille, combine, TextArtifact("FIFTH STEP"))
      .connect(solve_riddle, combine, TextArtifact("SUNDIAL"))
  ```

  Scattering one puzzle's pieces is the same shape: place each artifact from a
  single generator on a *different* edge that feeds the solve. The reference hunt
  scatters the riddle's three lines this way —
  `connect(find_shed, solve_riddle, riddle.artifacts("line0"))`, and so on — so the
  gated merge means "you need all three lines to read the riddle."

The ordering query understands the difference: a merge node is **gated** — it is
not reached until **every** thread feeding it has been emitted (step 5). So
`combine` appears in the solve order only *after* all three of its inputs, which is
exactly what "you need all three clues to proceed" means.

> **Multiple teams / competing players — an open, deferred question.** Several
> teams racing, diverging onto different paths and re-converging, is expressed
> with these *same* primitives: divergence is a branch, convergence is a gated
> merge. It is **never** a puzzle concern — a puzzle never knows *who* is solving it,
> and *which team is where*
> is live playthrough state that belongs to the future tracking layer, not this
> stateless model. What is **not yet decided** is the ergonomic authoring form for
> per-team divergent content: one shared graph with a per-edge/path team tag, vs.
> parallel subgraphs sharing convergence nodes. These are two interconvertible
> encodings of the same information, so the real question is which is the
> *canonical authored shape* and which is a *derived view* — an additive seam
> extension to settle when the need is concrete, not a model rewrite. Author
> single-thread hunts today; don't hand-roll a team-tagging scheme yet.

---

## Step 5 — Build, wire, and validate (`build`)

`.build()` materialises the immutable `Graph`. It is the single place that wires
and checks everything (via `Graph.assemble`):

```python
hunt = builder.build()
```

On build the graph:

1. **recomputes every node's wiring** (`incoming_edge_ids` / `outgoing_edge_ids`)
   from the edge list — these are never authored or stored, which is what keeps
   built and loaded graphs identical (and round-trip equality clean);
2. **validates structure**, raising `GraphError` on:
   - a **dangling edge** — `source` or `target` names a node that doesn't exist
     (usually a handle you didn't capture, or a `connect` before the matching
     `node`);
   - a **duplicate artifact id** — two artifacts sharing an id would collide on
     their output filenames; ids auto-generate uniquely (and a puzzle prefixes its
     pieces with its own id), so this only fires if you pass two explicit ones that
     clash;
   - a **cycle** — a hunt must flow forward; a loop back to an earlier action is
     rejected with the offending node ids.

There is no separate "set the start" call: after `build`, `start_nodes()` and
`end_nodes()` read the entry and exit points straight off the topology.

> **A node must exist before an edge names it.** Every `connect` endpoint must be a
> handle from a `node()` you already called. The common slip is referencing a node
> by a string you assumed instead of the handle `node()` returned — that surfaces
> as a dangling-edge `GraphError` at build time.

---

## Step 6 — Inspect the structure

With a built graph you have a small set of pure, side-effect-free queries (all
exported from the top-level package):

```python
from puzzcombinator import chronological_order

hunt.start_nodes()                 # [Node(...)]   — derived entry points
hunt.end_nodes()                   # [Node(...)]   — derived exits
hunt.incoming(combine)             # the three edges feeding the merge
hunt.outgoing(solve_gate)          # the three branch edges

for node in chronological_order(hunt):
    print(node.label)              # a valid solve order, merges gated correctly
```

`chronological_order(graph, start=None)` is a Kahn-style topological sort: a node
is emitted only once **all** its incoming sources have been emitted (the merge
gating from step 4), and ties break by node id so the order is **deterministic**
regardless of how you inserted edges. Pass `start=` to prefer a particular seed
first. It raises `GraphError` if the graph somehow contains a cycle.

This ordering is exactly what the binder walks to lay out the game-master pages,
so eyeballing it is a quick sanity check that your hunt flows the way you intended.

---

## Step 7 — Generate the materials

Turning the graph into printable output is the binder's job (covered fully in
`rendering/binder.py`); from the graph author's side it's one call:

```python
from puzzcombinator import hunt_bundle, write_bundle

write_bundle(hunt_bundle(hunt), "hunt_out")
```

> **The binder is mid-migration.** It has not yet been rebuilt, and exactly how it
> routes a piece to a player printable vs. the answer key is the open question of
> that phase (see CLAUDE.md). The shape below describes the *target*; treat it as
> where this is heading, not what runs today.

- **`hunt_bundle(graph)`** is pure: it returns a `dict` of `{path: contents}` — a
  game-master `binder.html` (one page per action in solve order, rendering each
  step's incoming and outgoing artifacts, including the answer-key pieces, plus a
  production checklist) and a `players/` printable per player-facing artifact.
- **`write_bundle(bundle, dir)`** is the only filesystem I/O — it writes that dict
  to disk and returns the paths written.
- If you want the pieces separately, `game_master_binder(graph) -> str` and
  `player_pages(graph) -> dict` are exported too.

The binder holds **no artifact-specific styling** — each artifact's `RenderFragment`
carries its own CSS — so a hunt using a brand-new artifact type needs zero binder
changes. See the reference hunt's tail for the canonical invocation.

---

## Step 8 — Save and load

The graph round-trips losslessly through `serialization/` — the interchange seam
for any future GUI or tracking layer:

```python
from puzzcombinator.serialization import to_json, from_json

text = to_json(hunt)               # JSON string (stdlib; indent=2 by default)
restored = from_json(text)         # an equal Graph
assert restored == hunt            # the keystone invariant
```

`from_json(to_json(g)) == g` is the invariant the whole serialization layer is
built to preserve — which is why wiring is recomputed on load and ids (not object
references) tie everything together. Each edge's artifacts round-trip through their
registry as `{type, id, name, payload}`, so a loaded hunt rebuilds every
artifact by `type_name`. (Puzzle generators are authoring-time only and are not
serialized — the artifacts they produced are.) `to_yaml` / `from_yaml` are available
too (lazy, optional dependency). Malformed input raises `SerializationError`.

---

## The whole recipe, condensed

1. `builder = GraphBuilder()`.
2. `handle = builder.node(action=…, label=…, notes=…)` for each step — capture the
   returned handle; ids auto-generate (no inventing). Start/end are just the
   un-wired ends, not a property.
3. `builder.connect(src, tgt, *puzzle.artifacts().values())` (using the handles) to
   hang **all** of a puzzle's pieces — prompt and answer key alike — on the edge
   **into** its solve action; `connect(src, tgt, TextArtifact(…))` for the clue it
   yields.
4. Write each puzzle's outgoing clue **by hand** — solutions are not auto-linked.
5. Branch = a node with several outgoing edges; merge = a node with several
   incoming edges (gated in solve order). Scatter one puzzle's pieces by placing
   each `puzzle.artifacts(name)` on a different edge into the merge.
6. `.build()` — wires and validates (dangling edges, cycles → `GraphError`).
7. `chronological_order` / `start_nodes` / `end_nodes` / `incoming` / `outgoing`
   / `required_inputs` / `produced_outputs` to inspect.
8. `write_bundle(hunt_bundle(graph), dir)` for materials; `to_json` / `from_json`
   to persist.

**You never edit `puzzles/` or `rendering/` to author a hunt, and the graph layer
never names a concrete artifact type.** If you reach for either, stop — the layers
are decoupled on purpose.

---

*See [`examples/hunts/mock_hunt/hunt.py`](../../../examples/hunts/mock_hunt/hunt.py) for all of
the above assembled into one working hunt — four puzzle types, the image artifact, a
three-way branch and merge, and a physical step — and [`AUTHORING_PUZZLES.md`](../puzzles/AUTHORING_PUZZLES.md)
for building the puzzles that ride the edges.*
