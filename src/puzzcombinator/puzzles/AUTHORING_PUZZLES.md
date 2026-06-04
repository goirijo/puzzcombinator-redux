# Authoring a new puzzle type

This guide walks you, the game master, through writing a brand-new puzzle class
and making it fully usable across the library — authored in code, rendered for
both players and yourself, saved to disk, and reloaded. We build one example all
the way through: a **riddle** whose text is split into ordered parts, each printed
on its own sheet, so the answer can't be guessed until the parts are reassembled.
It is small but exercises every part of the contract, including the optional
multi-sheet output.

> **Scope.** A puzzle is a *self-contained authoring template*. It knows its own
> data, how to draw itself, and how to serialize itself — **and nothing else**.
> It has no idea which hunt it belongs to, what edge or node carries it, or what
> comes before or after it. That isolation is deliberate: the graph layer stays
> puzzle-agnostic, so adding a puzzle never forces an edit to `core/`,
> `serialization/`, or `rendering/`. Composing puzzles into a hunt graph is a
> separate concern, covered in its own guide.
>
> A puzzle also **never grades anything**. There is no `is_solved`, no answer
> checking, no "correct/incorrect". In a physical hunt, correctness is implicit:
> the player solves the puzzle and uses its output as the input to the next step.
> The most you ever expose is a *solution view* for your own answer key (step 4).

---

## The contract at a glance

Every puzzle is a subclass of `Puzzle` (`base.py`). To be complete it must
provide:

| Requirement | What it is | Riddle example |
|---|---|---|
| `type_name` | a stable string key for the registry | `"riddle"` |
| `@register_puzzle` | decorator that registers the class for deserialization | on `RiddlePuzzle` |
| `__init__(self, id=None, ...)` | stores the puzzle's data; **must** call `super().__init__(id)` | stores `parts`, `answer` |
| `to_payload()` | returns the puzzle's JSON-safe, type-specific fields | `{"parts": [...], "answer": "..."}` |
| `from_payload(cls, id, payload)` | rebuilds an instance from `to_payload()` output | reconstructs from the dict |
| `render(audience)` | returns a `RenderFragment` for `PLAYER` or `GAME_MASTER` | riddle text vs. the answer |

Two things are optional:

- a **convenience constructor** that lets you author from friendlier input than
  the raw canonical fields;
- an override of **`player_artifacts()`**, needed when the puzzle prints as
  several separate sheets — which the riddle does (one sheet per part, step 5).

The base class already gives you `__eq__` / `__hash__` (value equality by
`id` + `to_payload()`) and a default single-sheet `player_artifacts()`.

---

## Step 0 — Decide what data the puzzle *is*

Before writing code, pin down the **minimal canonical state** that fully
describes the puzzle, such that everything else (the player view, your answer
key, the printables) can be *derived* from it. Keep it JSON-safe (strings,
numbers, bools, lists, dicts) because it will be serialized verbatim.

For the riddle, that's two fields:

- `parts: list[str]` — the riddle text, split into the ordered pieces the player
  collects;
- `answer: str` — the solution.

A useful question here is *"can I derive the answer from the rest?"* When you can,
don't store it — keep only what's needed and compute the answer on demand, so the
two can't drift apart. A riddle's answer **cannot** be computed from its text, so
here the answer is genuinely part of the canonical state and we store it. Store
what you must, derive what you can.

---

## Step 1 — Create the file and the class skeleton

New puzzles live in `src/puzzcombinator/puzzles/`. Create one file per puzzle
type. Subclass `Puzzle`, set `type_name`, and apply `@register_puzzle`. Here is
the **generic skeleton to copy** — replace `MyPuzzle`, the `type_name`, and *all*
of the fields with your own:

```python
from __future__ import annotations

from typing import Any

from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.registry import register_puzzle
from puzzcombinator.rendering.fragment import Audience, RenderFragment


@register_puzzle
class MyPuzzle(Puzzle):
    """One-line description of the puzzle."""

    type_name = "my_puzzle"          # unique, stable registry key

    def __init__(self, id: str | None = None, *, field_a: ..., field_b: ...) -> None:
        super().__init__(id)         # <-- stores self.id (auto-generated if None)
        self.field_a = field_a       # your canonical state from step 0
        self.field_b = field_b
```

> **Adapting by copy-paste?** If you start from another puzzle's file, swap the
> *signature* and the *body* together in one pass — the params, the `self.`
> assignments, the payload, and the render must all refer to the **same** set of
> fields you chose in step 0. The classic mistake is renaming a parameter but
> leaving an assignment that still references the old name (`self.x = old_name`),
> which blows up only when something runs that line.

Filled in for the riddle:

```python
@register_puzzle
class RiddlePuzzle(Puzzle):
    """A riddle with a unique answer, split into parts so it can't be guessed
    until they're all assembled."""

    type_name = "riddle"

    def __init__(self, id: str | None = None, *, riddle: list[str], answer: str) -> None:
        super().__init__(id)
        self.parts = riddle
        self.answer = answer
```

Notes:

- **`type_name` must be unique and stable.** It is the key written to disk and
  looked up on load. Renaming it later breaks every saved hunt that used it.
- **`id`** is **optional and auto-generated.** It only needs to be unique within a
  hunt because it names the puzzle's output files; nothing ever looks a puzzle up
  by it. Take it as the first parameter defaulting to `None` and pass it straight
  to `super().__init__(id)` — the base class fills in a unique `{type_name}-{uuid}`
  when it's `None`. Accept an explicit id only as a convenience for readable
  printable filenames; never require the author to invent one.
- Take the rest of your data as **keyword-only** arguments (`*,`) so call sites
  read clearly and you can reorder fields freely.
- A keyword and the attribute it feeds need not share a name — here the `riddle=`
  argument is stored as `self.parts`. Pick whichever reads best on each side.
- The `__init__` should accept the *canonical* state. If the fields have
  structural rules (e.g. "must be non-empty"), validate them here and raise
  `PuzzleError` from a `_validate()` helper called at the end of `__init__`.
  `PuzzleError` is a design-time aid ("you built this puzzle wrong"), never
  player grading.

---

## Step 2 — (Optional) Add an authoring constructor

`__init__` takes the canonical state, but you often want to author from something
friendlier. Add a classmethod that builds the canonical fields for you. The riddle
stores a *list* of parts, but sometimes you just have one unsplit string:

```python
    @classmethod
    def from_text(cls, text: str, *, answer: str, id: str | None = None) -> RiddlePuzzle:
        """Author from a single unsplit string (one part)."""
        return cls(id, riddle=[text], answer=answer)
```

These constructors are purely ergonomic — the library never calls them, it only
ever uses `__init__` (directly and via `from_payload`). If a constructor needs
real transformation logic, keep that logic in a module-level function so it's easy
to unit-test on its own.

> **Where to put `id` in a convenience constructor.** Lead with the puzzle's real
> input (here `text`) and make `id` an optional trailing keyword, mirroring the
> built-ins (`from_plaintext(plaintext, shift, *, id=None)`). The author calls
> `RiddlePuzzle.from_text("…", answer="…")` and never thinks about ids; they add
> `id="r1"` only if they want a readable filename. (`from_payload` is the
> exception — the codec always passes the saved id, so it keeps `id` required and
> first.)

---

## Step 3 — Implement serialization (`to_payload` / `from_payload`)

These two methods are the round-trip seam. The codec wraps your payload as
`{"type": type_name, "id": id, "payload": to_payload()}` on save, and on load
calls `build_puzzle(type, id, payload)` → your `from_payload`. You only handle the
*type-specific fields* — `type` and `id` are taken care of.

```python
    def to_payload(self) -> dict[str, Any]:
        return {"parts": self.parts, "answer": self.answer}

    @classmethod
    def from_payload(cls, id: str, payload: dict[str, Any]) -> RiddlePuzzle:
        return cls(id, riddle=payload["parts"], answer=payload["answer"])
```

Rules:

- **`to_payload` output must be JSON-safe** and hold exactly enough to rebuild the
  puzzle — no more. If a field is derivable (step 0), don't store it.
- **`from_payload(to_payload())` must reconstruct a value-equal puzzle.** This is
  the keystone invariant the whole serialization layer relies on; the base
  `__eq__` compares `id` + `to_payload()`, so as long as you store and restore the
  same fields, equality holds for free.
- If you add a field in a later version, read it defensively so hunts saved by the
  older version still load — e.g. `payload.get("hint", None)` rather than
  `payload["hint"]`.

---

## Step 4 — Implement `render(audience)`

`render` returns a `RenderFragment` — a self-contained markup snippet plus the
CSS it needs. It is the **only** required output method. You produce **two views**
from the same data, selected by `audience`:

- `Audience.PLAYER` — what the player works on (the puzzle, *without* the answer).
- `Audience.GAME_MASTER` — your answer key (the solution shown).

### The easy path: presets (reach for this first)

Most puzzles render something simple — a word, a code, a pair of coordinates, an
image. For those, **don't hand-write markup or a `_CSS` block at all**: call a
helper from `puzzcombinator.rendering.presets`. You pass the raw value and get
back a fragment that already carries its styling (every preset shares one CSS
constant, so it aggregates to a single copy in the binder). The riddle's whole
`render` is two lines:

```python
from puzzcombinator.rendering import presets

def render(self, audience: Audience) -> RenderFragment:
    if audience is Audience.PLAYER:
        return presets.text("\n".join(self.parts), title="Riddle", id=self.id, monospace=True)
    return presets.text(self.answer, title="Answer", id=self.id)
```

The three helpers, in increasing order of control:

- **`presets.text(value, *, title=None, id=None, monospace=False)`** — a plain
  string, escaped for you. `monospace=True` renders a `<pre>` that preserves
  spacing (codes, coordinates, line-by-line text).
- **`presets.image(data_uri, *, alt="", caption=None, title=None, id=None)`** — an
  inline image with an optional caption. Pass a data URI to keep the hunt
  self-contained (see "Handling media" below).
- **`presets.card(body, *, title=None, id=None)`** — your own inner HTML wrapped
  in the default styling. `body` is inserted verbatim, so escape any untrusted
  text yourself. Use it when you need to combine several pieces into one fragment.

For many puzzles you are **done at this point** — skip to step 5. Read on only if
your puzzle wants custom CSS or precise SVG geometry.

### Full control: building a `RenderFragment` by hand

When the presets aren't enough, build the fragment yourself with
`RenderFragment.html(...)` / `RenderFragment.svg(...)` and your own `styles=`. Here
is the same riddle render done by hand, so you can see what the presets were doing
for you (note the extra `import html` for escaping):

```python
import html

_CSS = ".riddle pre { font-size: 1.2rem; letter-spacing: 0.03em; }"

    def render(self, audience: Audience) -> RenderFragment:
        if audience is Audience.PLAYER:
            lines = html.escape("\n".join(self.parts))
            return RenderFragment.html(
                f'<section class="puzzle riddle" data-id="{html.escape(self.id)}">'
                f"<h3>Riddle</h3><pre>{lines}</pre></section>",
                styles=_CSS,
            )
        return RenderFragment.html(
            f'<section class="puzzle riddle" data-id="{html.escape(self.id)}">'
            f"<h3>Answer</h3><p><strong>{html.escape(self.answer)}</strong></p>"
            f"</section>",
            styles=_CSS,
        )
```

> **There is no required "answer" or "solution" method**, and nothing constrains
> how you hold your answer key. Here it's a stored string; for another puzzle it
> might be a value you compute on the fly, or a structured object (a list of
> cells, a dict). The GM view simply has to render *something* for the answer. The
> **only** hard requirement is that `render` returns a `RenderFragment` whose
> `markup` is a string.

Key points when building a fragment by hand:

- **The fragment carries its own CSS.** Pass `styles=` with CSS scoped to your own
  class names. The binder aggregates every fragment's `styles` into one `<head>`,
  so **you never edit the binder to add styling** — this is exactly why the binder
  stays puzzle-agnostic. (Identical `styles` strings are de-duplicated, so a
  shared constant costs nothing.)
- **HTML or SVG.** Use `RenderFragment.html(...)` for markup, or
  `RenderFragment.svg(...)` for an inline `<svg>...</svg>` when you need precise
  geometry (a grid, a board, a diagram). SVG embeds directly in the HTML binder
  and prints sharply.
- **Escape everything you interpolate** with `html.escape(...)` so player- or
  designer-supplied text can't break the markup.
- Put a `data-id` on your root element; it makes the output easy to style and
  debug.

---

## Step 5 — (Optional) Override `player_artifacts()` for multi-sheet puzzles

`player_artifacts()` returns the printable player-facing piece(s). The default,
from the base class, wraps a single `render(PLAYER)` into one artifact — fine for
most puzzles:

```python
    # default, provided by the base class — no need to write this:
    def player_artifacts(self) -> list[Artifact]:
        return [Artifact("puzzle", self.render(Audience.PLAYER))]
```

Override it when the physical puzzle is **several separate sheets**. The riddle is
exactly this: each part is hidden in a different place, so each gets its own
printable, and the answer only emerges once a player has collected and ordered
them all:

```python
    def player_artifacts(self) -> list[Artifact]:
        """Each part is found separately; the answer emerges when combined."""
        total = len(self.parts)
        return [
            Artifact(
                f"line{ix}",
                presets.text(part, title=f"Line {ix + 1}/{total}", id=self.id, monospace=True),
            )
            for ix, part in enumerate(self.parts)
        ]
```

(Add `Artifact` to your import from `puzzcombinator.rendering.fragment`.) Each
`Artifact` pairs a short **filename-safe `slug`** (`"line0"`, `"line1"`, …) with a
`fragment`. The slug is never shown to anyone — the binder uses it to name the
file, one per artifact, keyed `players/<puzzle.id>-<slug>.{html,svg}`. Don't
confuse the `slug` with a preset's `title`, which *is* the heading shown on the
sheet.

---

## Step 6 — Export the class

Make the class importable and ensure it self-registers. Add it in **two** places:

1. `src/puzzcombinator/puzzles/__init__.py`:

   ```python
   from puzzcombinator.puzzles.riddle import RiddlePuzzle
   # ...
   __all__ = ["RiddlePuzzle", ...]
   ```

2. the package `src/puzzcombinator/__init__.py` (so users can do
   `from puzzcombinator import RiddlePuzzle`):

   ```python
   from puzzcombinator.puzzles.riddle import RiddlePuzzle
   # ...
   __all__ = ["RiddlePuzzle", ...]
   ```

> **Why this matters for loading.** `@register_puzzle` only runs when the module
> is imported. The package `__init__` imports every built-in puzzle on import,
> which is what populates the registry so `from_json` can rebuild puzzles by
> `type_name`. If you skip the export, your puzzle authors fine but **fails to
> deserialize** with a `RegistryError: unknown puzzle type`.

---

## Step 7 — Add a test file

Mirror the existing tests in `tests/puzzles/` (one file per puzzle, e.g.
`tests/puzzles/test_riddle.py`). At minimum cover:

- **construction** — the canonical fields land where you expect;
- **payload round-trip** — `from_payload(to_payload()) == original`;
- **equality / hash** — value equality, hashable in a set;
- **both render audiences** — the answer is *absent* from `PLAYER` and *present*
  in `GAME_MASTER`;
- **`player_artifacts()`** if you overrode it — the right number of sheets,
  sensible slugs, and the answer never on a player sheet.

```python
def test_payload_roundtrip() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer="coffin")
    assert RiddlePuzzle.from_payload("r1", puzzle.to_payload()) == puzzle


def test_render_hides_answer_from_player_shows_to_gm() -> None:
    puzzle = RiddlePuzzle("r1", riddle=parts, answer="coffin")
    assert "coffin" not in puzzle.render(Audience.PLAYER).markup
    assert "coffin" in puzzle.render(Audience.GAME_MASTER).markup
```

> **Test the output methods, not just the data.** Construction, payload, and
> equality can all pass while `render` or `player_artifacts` is broken — because
> nothing in those tests calls them. A puzzle whose `player_artifacts` raises will
> pass its unit tests and then crash when the binder builds a hunt that uses it.
> The render-and-artifact tests above are what catch that.

---

## Step 8 — Verify against the "done" bar

From the repo root:

```bash
pip install -e ".[dev]"
pytest --cov=puzzcombinator
ruff check . && ruff format --check . && mypy src/puzzcombinator
```

All must be clean, and your new puzzle should be fully covered. If your puzzle
touches the end-to-end flow, regenerate the reference output and eyeball it:

```bash
python examples/hunts/mock_hunt/hunt.py    # writes examples/hunts/mock_hunt/out/
```

---

## Handling media (images and other binary assets)

Sooner or later a puzzle *is* a picture — a photo clue, a rebus, a scrambled
image. This seems to collide with "the payload must be JSON-safe", but it doesn't:
the rule that actually matters is that a serialized hunt is **self-contained**
(copy the JSON and you have copied the whole hunt). Honour both by **embedding the
media inline** as a **data URI**: `data:image/png;base64,<...>`. It is just a
(longer) string, so:

- `to_payload()` stays JSON-safe and the round-trip stays **byte-exact** — the
  bytes are *part of* the compared value, so equality can never silently drift
  from what renders;
- `render()` stays pure — it emits `<img src="data:...">`, with no file reads and
  no network;
- the output bundle stays text-only and unchanged — the player page and the binder
  embed the image with zero asset-copying machinery;
- the hunt stays portable — hand the JSON (or the printed page) to anyone and the
  image travels with it.

The pattern: take the bytes in an authoring constructor, store the data URI as
canonical state, then render it (or hand the URI straight to `presets.image`):

```python
import base64

    @classmethod
    def from_bytes(cls, id: str, data: bytes, *, mime: str) -> MyImagePuzzle:
        b64 = base64.b64encode(data).decode("ascii")
        return cls(id, data_uri=f"data:{mime};base64,{b64}")
```

Guidance when your puzzle carries media:

- **Author from bytes, store the data URI.** Keep any filesystem reads confined to
  authoring constructors — `render`, `to_payload`, and `from_payload` must never
  touch disk.
- **Vector art is free.** If the media is line art / a grid / a board, emit inline
  SVG via `RenderFragment.svg(...)` (text, tiny, prints sharply) — no base64
  needed. Reach for a data URI only for genuine raster images.
- **Bloat is acceptable at hunt scale.** A handful of images base64-inlined is
  fine; there is intentionally no size limit.

**The escape hatch (don't build it until you need it).** If a future puzzle needs
*large* or *shared* media where inlining hurts, the deliberate upgrade is an
**asset store**: the payload holds a stable reference (e.g. a content hash), the
bytes travel beside the JSON in an `assets/` directory, and the bundle is widened
to carry binary. That is strictly more machinery and gives up nothing the data URI
offers for small media — so treat it as a documented, discussed change, not a
default.

---

## The whole recipe, condensed

1. New file in `puzzles/`; `class MyPuzzle(Puzzle)`, `@register_puzzle`.
2. Set a unique, stable `type_name`.
3. `__init__(self, id, *, ...)` storing canonical state; call `super().__init__(id)`.
4. (Optional) a convenience constructor for friendlier authoring input.
5. `to_payload()` / `from_payload()` — JSON-safe, round-trip exact.
6. `render(audience)` — player view vs. GM answer key; presets first, hand-rolled
   only if needed.
7. (Optional) `player_artifacts()` if it prints as multiple sheets.
8. Export in `puzzles/__init__.py` **and** the package `__init__.py`.
9. Add `tests/puzzles/test_mypuzzle.py` — including the render/artifact tests.
10. `pytest`, `ruff`, `mypy` clean.

**You never edit `core/`, `serialization/`, or `rendering/`.** If you find
yourself needing to, stop — the design intends the puzzle to be fully
self-describing through the `Puzzle` ABC and the registry. Reach for a discussion
before breaking that boundary.

---

*Next: composing puzzles into a hunt — building the graph, and what nodes and
edges mean. See [`../core/AUTHORING_GRAPHS.md`](../core/AUTHORING_GRAPHS.md).*
