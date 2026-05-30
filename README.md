# puzzcombinator

A modular library of tools for **authoring treasure-hunt games**.

A treasure hunt is modeled as a **graph of puzzles**: it flows from a start
node, through a branching/merging web of puzzle nodes, to an end node. Solving a
puzzle reveals its **output** (a clue), which feeds **downstream** puzzles as
their input. Nodes may have multiple inputs (e.g. two teams' paths converge
before a node) and multiple outputs.

This is a **design-time tool for the hunt's designer** — it helps you create
puzzles, compose them into a hunt, and produce printable artifacts. It does not
*play* or *grade* a hunt: in a physically-played hunt, correctness is verified
implicitly when a player uses one puzzle's output as the next puzzle's input (or
the key fits the lock). Live progress tracking is a separate, future layer.

## Layers

- **`core/`** — the puzzle-agnostic graph engine (`Node` / `Edge` / `Graph`),
  a fluent `GraphBuilder`, and a topological `chronological_order` with
  branch/merge gating. Stdlib only.
- **`puzzles/`** — the `Puzzle` base + a type registry + the first concrete
  puzzle (`CaesarCipherPuzzle`). A puzzle is an authoring-time template: it owns
  its data and knows how to render its printable artifact (for players) and its
  solution (for the game-master answer key). It has no notion of being "solved"
  and does no answer-checking.
- **`serialization/`** — round-trip a hunt to/from JSON (stdlib) or YAML
  (optional `[yaml]` extra). The Python builder API is primary; serialization
  lets a future GUI/web/monitoring layer read and write hunts.
- **`rendering/`** — format-neutral `RenderFragment`s (HTML or inline SVG) that
  a puzzle emits on demand, plus the master-binder seam (`render_binder`) that a
  later milestone fleshes out into the full printable document.

The model is **stateless**: it describes a hunt but never tracks live player
state and does no answer-checking. Those are playthrough concerns owned by a
future tracking layer, so it can be added without reworking the model.

## Quick start

```python
from puzzcombinator import GraphBuilder, Content, NodeKind, CaesarCipherPuzzle
from puzzcombinator import chronological_order, produced_outputs, render_binder, Audience
from puzzcombinator.serialization import to_json, from_json

cipher = CaesarCipherPuzzle.from_plaintext("c1", plaintext="FOUNTAIN", shift=3)

graph = (
    GraphBuilder()
    .node("start", kind=NodeKind.START, label="Welcome")
    .node("c1", payload=cipher, label="Caesar gate", notes="hide under the doormat")
    .node("end", kind=NodeKind.END, label="Treasure")
    .connect("start", "c1", content=Content(text="Your first clue is encoded."))
    .connect("c1", "end", content=Content(text="Go to the fountain."))
    .build()
)

for node in chronological_order(graph):
    print(node.id, node.label)

# The clue this puzzle reveals flows on its outgoing edge.
assert [c.text for c in produced_outputs(graph, "c1")] == ["Go to the fountain."]

restored = from_json(to_json(graph))
assert restored == graph

# Printable master document; GAME_MASTER audience includes the answer key + notes.
html = render_binder(graph, audience=Audience.GAME_MASTER)
```

## Development

```bash
pip install -e ".[dev]"
pytest --cov=puzzcombinator
ruff check . && ruff format --check . && mypy src/puzzcombinator
```
