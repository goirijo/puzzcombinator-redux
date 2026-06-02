# puzzcombinator

A modular library of tools for **authoring treasure-hunt games**.

A treasure hunt is modeled as a **graph of actions**. Each **edge** carries the
information flowing between actions — a clue/word/object, and/or a **puzzle**
artifact the player works on. Each **node** is a pure *action* (solve, find,
move, …) that consumes its incoming edges and produces its outgoing ones. Nodes
may have multiple inputs (e.g. two paths converge) and multiple outputs; start
and end are simply the nodes with no incoming / no outgoing edges.

This is a **design-time tool for the hunt's designer** — it helps you create
puzzles, compose them into a hunt, and produce printable artifacts. It does not
*play* or *grade* a hunt: in a physically-played hunt, correctness is verified
implicitly when a player uses one puzzle's output as the next puzzle's input (or
the key fits the lock). Live progress tracking is a separate, future layer.

## Layers

- **`core/`** — the puzzle-agnostic graph engine: `Node` (a pure action with a
  free-form `action` label), `Edge` carrying `Content` (`text` / `data` /
  optional `puzzle`), `Graph`, a fluent `GraphBuilder`, and a topological
  `chronological_order` with branch/merge gating. Stdlib only.
- **`puzzles/`** — the `Puzzle` base + a type registry + concrete puzzles
  (`CaesarCipherPuzzle`, `CrosswordPuzzle`, `R4DecoderPuzzle`). A puzzle is an
  authoring-time template: it owns its data and knows how to render its printable
  artifact (for players) and its solution (for the game-master answer key). It has
  no notion of being "solved" and does no answer-checking. The crossword derives
  its numbering and across/down slots from a solution grid, and optional
  `highlight` cells spell an **emergent word**. The R4 decoder is a turning-grille
  cipher (inline SVG) with `reveal_grid` / `reveal_decoder` flags so the player
  view can be the full puzzle to overlay-and-rotate, or blank templates assembled
  from clues revealed by other puzzles.
- **`serialization/`** — round-trip a hunt to/from JSON (stdlib) or YAML
  (optional `[yaml]` extra). The Python builder API is primary; serialization
  lets a future GUI/web/monitoring layer read and write hunts.
- **`rendering/`** — format-neutral `RenderFragment`s (HTML or inline SVG, each
  carrying its own CSS) that a puzzle emits on demand, plus the output layer:
  `game_master_binder` (a page per action + a production checklist),
  `player_pages` (one printable per edge puzzle), and `hunt_bundle` /
  `write_bundle` to produce a `binder.html` + `players/` folder. Puzzle-agnostic:
  a new puzzle type needs no binder changes.

The model is **stateless**: it describes a hunt but never tracks live player
state and does no answer-checking. Those are playthrough concerns owned by a
future tracking layer, so it can be added without reworking the model.

## Quick start

```python
from puzzcombinator import GraphBuilder, CaesarCipherPuzzle
from puzzcombinator import chronological_order, produced_outputs
from puzzcombinator import hunt_bundle, write_bundle
from puzzcombinator.serialization import to_json, from_json

cipher = CaesarCipherPuzzle.from_plaintext("c1", plaintext="FOUNTAIN", shift=3)

# The cipher rides the edge into the "solve" action; solving yields the next clue.
graph = (
    GraphBuilder()
    .node("start", label="Welcome")
    .node("solve", action="solve", label="Caesar gate", notes="hide under the doormat")
    .node("end", label="Treasure")
    .connect("start", "solve", puzzle=cipher)
    .connect("solve", "end", text="Go to the fountain.")
    .build()
)

for node in chronological_order(graph):
    print(node.id, node.action)

# The clue this action produces flows on its outgoing edge.
assert [c.text for c in produced_outputs(graph, "solve")] == ["Go to the fountain."]

restored = from_json(to_json(graph))
assert restored == graph

# Generate the materials: a game-master binder.html + a players/ folder.
write_bundle(hunt_bundle(graph), "hunt_out")
```

See `examples/mock_hunt/hunt.py` for a full non-linear hunt (all five puzzle
types, a converging branch, and a physical step).

## Development

```bash
pip install -e ".[dev]"
pytest --cov=puzzcombinator
ruff check . && ruff format --check . && mypy src/puzzcombinator
```
