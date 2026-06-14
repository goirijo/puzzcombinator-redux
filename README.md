# puzzcombinator

A modular library of tools for **authoring treasure-hunt games**.

A treasure hunt is modeled as a **graph of actions**. Each **edge** carries a list
of **artifacts** — the information flowing between actions (a clue, a cipher, a
grid, a pair of coordinates). Each **node** is a pure *action* (solve, find,
move, …) that consumes its incoming edges and produces its outgoing ones. Nodes
may have multiple inputs (e.g. two paths converge) and multiple outputs; start
and end are simply the nodes with no incoming / no outgoing edges.

An **artifact** is the universal "thing that renders": a serializable renderable. A
**puzzle** is an authoring-time *generator* of artifacts — it emits all of its pieces
(the ones players receive *and* the answer key) as one flat `{name: Artifact}` map.
The designer places those artifacts on edges, together or scattered across the graph;
which pieces reach players and which stay in the answer key is a placement decision.

This is a **design-time tool for the hunt's designer** — it helps you create
puzzles, compose the artifacts they emit into a hunt, and produce printable
materials. It does not *play* or *grade* a hunt: in a physically-played hunt,
correctness is verified implicitly when a player uses one artifact's output as the
next step's input (or the key fits the lock). Live progress tracking is a separate,
future layer.

## Layers

- **`core/`** — the artifact-agnostic graph engine: `Node` (a pure action with a
  free-form `action` label), `Edge` carrying a tuple of `Artifact`s, `Graph`, a
  `GraphBuilder`, and a topological `topological_order` with branch/merge gating.
  Stdlib only.
- **`artifacts/`** — the *orphan* artifacts that have no puzzle behind them
  (`TextArtifact`, and `ImageArtifact` — an inline-data-URI picture you build
  directly from bytes or a file), plus the artifact-type registry. The `puzzles`
  layer builds on top of it.
- **`puzzles/`** — the `Puzzle` generator base and the concrete puzzles
  (`CaesarCipherPuzzle`, `CrosswordPuzzle`, `R4DecoderPuzzle`, `RiddlePuzzle`) each
  paired with the artifact type(s) it emits. A puzzle owns its data and emits artifacts via
  `artifacts(name=None)`; it has no notion of being "solved" and
  does no answer-checking. The crossword derives its numbering and across/down slots
  from a solution grid, and optional `highlight` cells spell an **emergent word**.
  The R4 decoder is a turning-grille cipher (inline SVG) emitting grid + grille
  pieces, with `reveal_grid` / `reveal_decoder` flags. The riddle emits one line
  artifact per part, so its lines can be scattered across the graph and assembled.
- **`serialization/`** — round-trip a hunt to/from JSON (stdlib) or YAML
  (optional `[yaml]` extra). Each edge serializes its artifacts as
  `{type, id, name, payload}`. The Python builder API is primary;
  serialization lets a future GUI/web/monitoring layer read and write hunts.
- **`rendering/`** — format-neutral `RenderFragment`s (HTML or inline SVG, each
  carrying its own CSS) that an artifact emits on demand, plus the output layer:
  `game_master_binder` (a page per action + a production checklist), `player_pages`
  (one printable per artifact), and `hunt_bundle` / `write_bundle` to
  produce a `binder.html` + `players/` folder. Artifact-agnostic: a new artifact
  type needs no binder changes.

The model is **stateless**: it describes a hunt but never tracks live player
state and does no answer-checking. Those are playthrough concerns owned by a
future tracking layer, so it can be added without reworking the model.

## Quick start

```python
from puzzcombinator import GraphBuilder, CaesarCipherPuzzle, TextArtifact
from puzzcombinator import topological_order, produced_outputs
from puzzcombinator import hunt_bundle, write_bundle
from puzzcombinator.serialization import graph_to_dict, graph_from_dict

cipher = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")

# node() returns a handle; capture it and wire edges as you go. The cipher's
# artifacts ride the edge into the "solve" action — the ciphertext to decode and
# the revealed answer; solving yields the next clue.
b = GraphBuilder()
start = b.node(label="Welcome")
solve = b.node(action="solve", label="Caesar gate", notes="hide under the doormat")
end = b.node(label="Treasure")
b.connect(start, solve, *cipher.artifacts().values())
b.connect(solve, end, TextArtifact("Go to the fountain."))
graph = b.build()

for node_id in topological_order(graph):   # returns node ids, the universal handle
    print(node_id, graph.node(node_id).action)

# The artifacts this action produces flow on its outgoing edge (use the handle).
assert [a.text for a in produced_outputs(graph, solve)] == ["Go to the fountain."]

# A graph round-trips losslessly through its own JSON slice. (To save a whole hunt
# to a file, wrap it: to_json(HuntDocument.single(graph)) — see AUTHORING_GRAPHS.md.)
restored = graph_from_dict(graph_to_dict(graph))
assert restored == graph

# Generate the materials: a game-master binder.html + a players/ folder.
write_bundle(hunt_bundle(graph), "hunt_out")
```

See `examples/hunts/mock_hunt/hunt.py` for a full non-linear hunt (all four puzzle
types, the image artifact, a converging branch, and a physical step).

## Development

```bash
pip install -e ".[dev]"
pytest --cov=puzzcombinator
ruff check . && ruff format --check . && mypy src/puzzcombinator
```
