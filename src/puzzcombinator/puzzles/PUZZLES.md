# Authoring a new puzzle type

This guide walks you, the game master, through adding a brand-new puzzle and making
it fully usable across the library — authored in code, rendered, saved to disk, and
reloaded. We build one example all the way through: a **riddle** whose text is split
into ordered lines, each printed on its own sheet, so the lines can be scattered
across the hunt and the answer can't be guessed until they're reassembled.

A "puzzle type" is really **two small things**:

- an **`Artifact`** — the serializable *thing that renders* (here, one riddle line).
  Artifacts are what live on graph edges and what get saved, reloaded, and printed.
- a **`Puzzle`** — an authoring-time *generator* that owns the puzzle's data and
  emits **all** its artifacts as one flat `{name: Artifact}` map: the pieces players
  receive *and* the answer key, each a fully-baked instance.

> **Scope.** An artifact knows its own data and how to draw itself — **and nothing
> else**. A puzzle knows how to author and split that data into artifacts. Neither
> has any idea which hunt it belongs to, what edge carries it, or *who* receives it.
> That isolation is deliberate: the graph layer stays **artifact-agnostic**, so
> adding a type never forces an edit to `core/`, `serialization/`, or `rendering/`.
> Composing artifacts into a hunt graph is a separate concern, covered in its own
> guide.
>
> A puzzle also **never grades anything**. There is no `is_solved`, no answer
> checking, no "correct/incorrect". In a physical hunt, correctness is implicit: the
> player solves the puzzle and uses its output as the input to the next step. The
> most you ever produce is an *answer-key artifact* for your own reference — just
> another piece in the map, with no special status.

---

## The contract at a glance

An **artifact** subclasses `Artifact` (`rendering/fragment.py`). To be complete it
must provide:

| Requirement | What it is | Riddle-line example |
|---|---|---|
| `type_name` | a stable string key for the registry | `"riddle_line"` |
| `@register_artifact` | decorator that registers the class for deserialization | on `RiddleLineArtifact` |
| `__init__(self, ..., *, name, id=None)` | stores the data; **must** call `super().__init__(...)` | stores `text`, `index`, `total` |
| `to_payload()` | returns the artifact's JSON-safe, type-specific fields | `{"text": ..., "index": ..., "total": ...}` |
| `from_payload(cls, *, name, id, payload)` | rebuilds an instance from its envelope + `to_payload()` | reconstructs from the dict |
| `render()` | returns a `RenderFragment` — a **pure function of the payload** | the line, as a card |

A **puzzle generator** subclasses `Puzzle` (`base.py`) and provides one method:

| Requirement | What it is | Riddle example |
|---|---|---|
| `type_name` | a readable id prefix for the artifacts it emits | `"riddle"` |
| `_artifacts(self)` | builds the full list of artifacts the puzzle is made of | a line per part, plus the answer |

The base `Puzzle` gives you `artifacts(name=None)` (the map/by-name dispatch) and
`artifact_id(name)` (`{puzzle.id}-{name}`). The base `Artifact` gives you value-based
`__eq__` / `__hash__` (type + id + name + `to_payload()`), which is what makes the
serialization round-trip `==` invariant hold.

A standalone artifact that carries no puzzle is an *orphan* — it lives in the
`artifacts/` package, not here, and you construct it directly with no generator. See
the shipped `TextArtifact` (`artifacts/text.py`) and `ImageArtifact`
(`artifacts/image.py`, with `from_bytes` / `from_file` classmethods).

> **Pieces are just named, never routed.** A puzzle emits every piece it is made of
> as a named entry in one map. Whether a given piece is handed to a player or kept
> only for the answer key is a **placement** decision a higher layer makes — not a
> property baked into the artifact.

---

## Step 0 — Decide what data the artifact *is*

Pin down the **minimal canonical state** that fully describes a piece, such that its
rendering can be *derived* from it. Keep it JSON-safe (strings, numbers, bools,
lists, dicts) because it is serialized verbatim.

A riddle line is three fields: `text` (the line), and `index` / `total` (so the
sheet can show "Line 2/3"). The puzzle generator holds the higher-level state —
`parts: list[str]` and `answer: str` — and slices it into per-line artifacts.

A useful question: *"is this the prompt or the answer?"* The two are **separate
artifact instances** — the generator bakes the right data into each (the blank/prompt
piece, and the revealed answer piece), so `render()` never has to branch on anything
external. Store what differs between the prompt and the answer as different instances,
not as a flag the renderer inspects.

---

## Step 1 — Create the file and the artifact skeleton

Puzzle-bound types live in `src/puzzcombinator/puzzles/`, one file per type (an
orphan artifact with no generator goes in `src/puzzcombinator/artifacts/` instead).
Subclass `Artifact`, set `type_name`, apply `@register_artifact`. The **generic
skeleton to copy**:

```python
from __future__ import annotations

from typing import Any

from puzzcombinator.artifacts.registry import register_artifact
from puzzcombinator.rendering.fragment import Artifact, RenderFragment


@register_artifact
class MyArtifact(Artifact):
    """One-line description of the renderable piece."""

    type_name = "my_artifact"          # unique, stable registry key

    def __init__(
        self,
        field_a: ...,                  # your canonical state from step 0
        *,
        name: str = "my_artifact",
        id: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id)
        self.field_a = field_a
```

`name` / `id` are the **envelope** every artifact carries; take them as keyword-only
with sensible defaults and pass them straight to `super().__init__`. The base
auto-generates `id` as `{type_name}-{uuid}` when it's `None`.

Filled in for the riddle line:

```python
@register_artifact
class RiddleLineArtifact(Artifact):
    """One line of a riddle, labelled with its position so players can order them."""

    type_name = "riddle_line"

    def __init__(
        self, text: str, *, index: int, total: int,
        name: str | None = None, id: str | None = None,
    ) -> None:
        super().__init__(name=name or f"line{index}", id=id)
        self.text = text
        self.index = index
        self.total = total
```

Notes:

- **`type_name` must be unique and stable.** It is the key written to disk and looked
  up on load. Renaming it later breaks every saved hunt that used it.
- **`id`** is auto-generated and only needs to be unique within a hunt (it names an
  artifact's output file). The generator sets it to `{puzzle.id}-{name}` so
  filenames stay readable; nothing ever looks an artifact up by it.
- Validate structural rules in the `__init__` (raise `PuzzleError` from a
  `_validate()` helper). `PuzzleError` is a design-time aid ("you built this wrong"),
  never player grading.

---

## Step 2 — Implement serialization (`to_payload` / `from_payload`)

These are the round-trip seam. The codec wraps your payload as
`{"type": type_name, "id": ..., "name": ..., "payload": to_payload()}` on save; on
load it calls `build_artifact(type, name=, id=, payload=)` → your `from_payload`. You
only handle the *type-specific fields*.

```python
    def to_payload(self) -> dict[str, Any]:
        return {"text": self.text, "index": self.index, "total": self.total}

    @classmethod
    def from_payload(cls, *, name: str, id: str, payload: dict[str, Any]):
        return cls(payload["text"], index=payload["index"], total=payload["total"],
                   name=name, id=id)
```

Rules:

- **`to_payload` output must be JSON-safe** and hold exactly enough to rebuild the
  piece — no more.
- **`from_payload(... to_payload())` must reconstruct a value-equal artifact.** This
  is the keystone invariant the serialization layer relies on; the base `__eq__`
  compares the envelope + `to_payload()`, so storing and restoring the same fields
  makes equality hold for free.
- Read new fields defensively (`payload.get("hint")`) so older saved hunts still load.

---

## Step 3 — Implement `render()`

`render` returns a `RenderFragment` — a self-contained markup snippet plus the CSS it
needs — and is a **pure function of the artifact's payload**. It takes no arguments:
the prompt piece and the answer piece are *different instances* (step 4), so `render`
just draws whatever data it holds.

### The easy path: presets (reach for this first)

Most pieces render something simple — a word, a code, coordinates, an image. Don't
hand-write markup or a `_CSS` block: call a helper from
`puzzcombinator.rendering.presets`. You pass the raw value and get back a fragment
that already carries its styling (every preset shares one CSS constant, so it
aggregates to a single copy in the binder). The riddle line's whole render is one
line:

```python
from puzzcombinator.rendering import presets

    def render(self) -> RenderFragment:
        return presets.text(
            self.text, title=f"Line {self.index + 1}/{self.total}", id=self.id, monospace=True
        )
```

The three helpers, in increasing order of control:

- **`presets.text(value, *, title=None, id=None, monospace=False)`** — a plain
  string, escaped for you. `monospace=True` renders a `<pre>` preserving spacing.
- **`presets.image(data_uri, *, alt="", caption=None, title=None, id=None)`** — an
  inline image (see "Handling media" below).
- **`presets.card(body, *, title=None, id=None)`** — your own inner HTML wrapped in
  the default styling. `body` is inserted verbatim, so escape untrusted text yourself.

For many types you are **done at this point**. Read on only for custom CSS or SVG.

### Full control: building a `RenderFragment` by hand

When presets aren't enough, build the fragment with `RenderFragment.html(...)` /
`RenderFragment.svg(...)` and your own `styles=`:

- **The fragment carries its own CSS.** Pass `styles=` scoped to your own class
  names; the binder aggregates every fragment's `styles` into one `<head>`, so **you
  never edit the binder to add styling** (identical strings are de-duplicated).
- **HTML or SVG.** Use `RenderFragment.svg(...)` for an inline `<svg>...</svg>` when
  you need precise geometry (a grid, a board); it embeds in the HTML binder and
  prints sharply. See `r4.py`'s `R4PieceArtifact`.
- **Escape everything you interpolate** with `html.escape(...)`.
- Put a `data-id` on your root element; it makes output easy to style and debug.

Whichever artifact renders the answer simply *includes* the answer in its payload and
markup — there is no required "solution" method. The cipher's `solution` artifact
carries the decoded text; for the riddle, the answer is a separate `TextArtifact`
(step 4).

---

## Step 4 — Write the puzzle generator

The generator owns the puzzle's data and emits artifacts. Subclass `Puzzle`, set
`type_name` (the id prefix), and implement `_artifacts(self)` — the base supplies
the public `artifacts(name=None)` map/by-name dispatch.

```python
class RiddlePuzzle(Puzzle):
    """Generates a riddle's ordered line artifacts plus its answer."""

    type_name = "riddle"

    def __init__(self, id: str | None = None, *, riddle: list[str], answer: str) -> None:
        super().__init__(id)
        self.parts = riddle
        self.answer = answer

    def _artifacts(self) -> list[Artifact]:
        total = len(self.parts)
        out: list[Artifact] = [
            RiddleLineArtifact(part, index=ix, total=total, name=f"line{ix}",
                               id=self.artifact_id(f"line{ix}"))
            for ix, part in enumerate(self.parts)
        ]
        out.append(TextArtifact(self.answer, title="Answer", name="answer",
                                id=self.artifact_id("answer")))
        return out
```

The generator emits **every piece the puzzle is made of** — here the lines *and* the
answer (a reused `TextArtifact`) — as separate, distinctly-named instances. It makes
no player-vs-answer-key decision: that routing is a *placement* concern for a higher
layer. Where a piece's prompt and answer views genuinely differ, emit **two named
instances** rather than one with a flag — see `cipher.py` (`cipher` carries the
ciphertext, `solution` carries the decoded answer) and `crossword.py` (`crossword`
is the blank grid, `solution` the filled one). The author then places these —
together with `*puzzle.artifacts().values()`, or one at a time with
`puzzle.artifacts("line0")` to **scatter** the pieces across the graph.

> **`id` in a convenience constructor.** Lead with the puzzle's real input and make
> `id` an optional trailing keyword, mirroring `from_plaintext(plaintext, shift, *,
> id=None)`. The author rarely thinks about ids; they pass one only for readable
> filenames.

---

## Step 5 — Export the classes

Make them importable and ensure the artifact self-registers. Add them in **two**
places — the package `__init__.py` for the layer the type lives in
(`src/puzzcombinator/puzzles/__init__.py`, or `artifacts/__init__.py` for an orphan)
and the top-level `src/puzzcombinator/__init__.py`:

```python
from puzzcombinator.puzzles.riddle import RiddleLineArtifact, RiddlePuzzle
# ... and add both names to __all__
```

> **Why this matters for loading.** `@register_artifact` only runs when the module is
> imported. The package `__init__` imports every built-in type on import, which
> populates the registry so `from_json` can rebuild artifacts by `type_name`. Skip
> the export and your type authors fine but **fails to deserialize** with a
> `RegistryError: unknown artifact type`.

---

## Step 6 — Add a test file

Mirror `tests/puzzles/` (or `tests/artifacts/` for an orphan), one file per type. At
minimum cover:

- **artifact payload round-trip** — `from_payload(... to_payload()) == original`;
- **artifact equality / hash** — value equality, hashable in a set;
- **artifact render** — what it should show is in the markup;
- **generator `artifacts()`** — the right names are present, and the answer renders
  only on its own piece, never on a prompt piece.

```python
def test_line_artifacts_one_per_part_for_scattering() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer="coffin")
    artifacts = puzzle.artifacts()
    assert list(artifacts) == [f"line{i}" for i in range(len(parts))] + ["answer"]
    lines = [a for name, a in artifacts.items() if name.startswith("line")]
    assert all("coffin" not in a.render().markup for a in lines)


def test_artifacts_include_the_answer() -> None:
    artifacts = RiddlePuzzle("r1", riddle=parts, answer="coffin").artifacts()
    assert "coffin" in artifacts["answer"].render().markup
```

> **Test the output methods, not just the data.** Construction and payload can pass
> while `render` or `_artifacts` is broken — because nothing calls them. The
> render-and-artifacts tests are what catch a type that crashes when the binder
> builds a hunt that uses it.

---

## Step 7 — Verify against the "done" bar

From the repo root:

```bash
pip install -e ".[dev]"
pytest --cov=puzzcombinator
ruff check . && ruff format --check . && mypy src/puzzcombinator
python examples/hunts/mock_hunt/hunt.py    # writes examples/hunts/mock_hunt/out/
```

All must be clean, and your new type should be fully covered.

---

## Handling media (images and other binary assets)

Sooner or later an artifact *is* a picture — a photo clue, a rebus, a scrambled
image. This seems to collide with "the payload must be JSON-safe", but it doesn't:
the rule that actually matters is that a serialized hunt is **self-contained** (copy
the JSON and you have copied the whole hunt). Honour both by **embedding the media
inline** as a **data URI**: `data:image/png;base64,<...>`. It is just a (longer)
string, so:

- `to_payload()` stays JSON-safe and the round-trip stays **byte-exact**;
- `render()` stays pure — it emits `<img src="data:...">`, with no file reads;
- the output bundle stays text-only — the page embeds the image with zero
  asset-copying machinery;
- the hunt stays portable — hand someone the JSON and the image travels with it.

The pattern: take the bytes in an authoring classmethod on the artifact, store the
data URI as its canonical state, then render it (or hand the URI to `presets.image`).
An image has no puzzle behind it, so this lives on the artifact itself — see
`artifacts/image.py` for the worked version (`ImageArtifact.from_file` / `from_bytes`).

- **Author from bytes, store the data URI.** Keep filesystem reads confined to
  authoring constructors — `render`, `to_payload`, `from_payload` must never touch disk.
- **Vector art is free.** Line art / a grid / a board: emit inline SVG via
  `RenderFragment.svg(...)`. Reach for a data URI only for genuine raster images.
- **Bloat is acceptable at hunt scale.** A handful of inlined images is fine; there
  is intentionally no size limit.

**The escape hatch (don't build it until you need it).** If a future type needs
*large* or *shared* media where inlining hurts, the deliberate upgrade is an **asset
store**: the payload holds a stable reference (a content hash), the bytes travel
beside the JSON in an `assets/` directory, and the bundle is widened to carry binary.
That is strictly more machinery — treat it as a documented, discussed change.

---

## The whole recipe, condensed

1. New file in `puzzles/` (or `artifacts/` if it's an orphan with no generator);
   `class MyArtifact(Artifact)`, `@register_artifact`, unique `type_name`.
2. `__init__(self, ..., *, name, id=None)` storing canonical state; call
   `super().__init__(...)`.
3. `to_payload()` / `from_payload(*, name, id, payload)` — JSON-safe, round-trip exact.
4. `render()` — a pure function of the payload; presets first, hand-rolled only if needed.
5. `class MyPuzzle(Puzzle)` with `_artifacts(self)` that emits every piece — prompt
   and answer — as separate named instances (skip the generator entirely for a pure
   standalone artifact like a clue).
6. Export the artifact **and** the generator in `puzzles/__init__.py` **and** the
   package `__init__.py`.
7. Add `tests/puzzles/test_mytype.py` — payload round-trip, render, and the
   generator's `artifacts()` map.
8. `pytest`, `ruff`, `mypy` clean.

**You never edit `core/`, `serialization/`, or `rendering/`.** If you find yourself
needing to, stop — the design intends the artifact to be fully self-describing
through the `Artifact` ABC and the registry. Reach for a discussion before breaking
that boundary.

---

*Next: composing artifacts into a hunt — building the graph, and what nodes and edges
mean. See [`../core/GRAPHS.md`](../core/GRAPHS.md).*
