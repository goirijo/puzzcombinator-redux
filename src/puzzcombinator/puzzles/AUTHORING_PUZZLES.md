# Authoring a new puzzle type

This guide walks you, the game master, through writing a brand-new puzzle class
and making it fully usable across the library — authored in code, rendered for
both players and yourself, saved to disk, and reloaded. We use the Caesar cipher
(`cipher.py`) as the running example because it is the smallest puzzle that
exercises every part of the contract.

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
> the player decodes the message and uses it as the next clue. The most you ever
> expose is a *solution view* for your own answer key (see step 4).

---

## The contract at a glance

Every puzzle is a subclass of `Puzzle` (`base.py`). To be complete it must
provide:

| Requirement | What it is | Caesar example |
|---|---|---|
| `type_name` | a stable string key for the registry | `"caesar_cipher"` |
| `@register_puzzle` | decorator that registers the class for deserialization | on `CaesarCipherPuzzle` |
| `__init__(self, id, ...)` | stores the puzzle's data; **must** call `super().__init__(id)` | stores `shift`, `ciphertext` |
| `to_payload()` | returns the puzzle's JSON-safe, type-specific fields | `{"shift": ..., "ciphertext": ...}` |
| `from_payload(cls, id, payload)` | rebuilds an instance from `to_payload()` output | reconstructs from the dict |
| `render(audience)` | returns a `RenderFragment` for `PLAYER` or `GAME_MASTER` | ciphertext vs. decoded answer |

Two things are optional:

- a **convenience constructor** (e.g. `from_plaintext`) that lets you author the
  puzzle from human-friendly input rather than from already-encoded state;
- an override of **`player_artifacts()`**, only needed when the puzzle prints as
  several separate sheets (see step 5).

The base class already gives you `__eq__` / `__hash__` (value equality by
`id` + `to_payload()`) and a default single-sheet `player_artifacts()`.

---

## Step 0 — Decide what data the puzzle *is*

Before writing code, pin down the **minimal canonical state** that fully
describes the puzzle, such that everything else (the player view, your answer,
the printable) can be *derived* from it. Keep it JSON-safe (strings, numbers,
bools, lists, dicts) because it will be serialized verbatim.

For Caesar, the canonical state is just the `shift` and the `ciphertext`. Notice
what is **not** stored: the plaintext solution. It is derivable by decoding, so
storing it would be redundant and could drift. Prefer deriving over storing.

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

    def __init__(self, id: str, *, field_a: ..., field_b: ...) -> None:
        super().__init__(id)         # <-- stores self.id; do not skip
        self.field_a = field_a       # your canonical state (step 0), not Caesar's
        self.field_b = field_b
```

> **Adapting from a real puzzle?** It's tempting to copy `cipher.py` wholesale,
> but then swap the *signature* without swapping the *body* — leaving a stray
> `self.shift = shift % 26` that references a parameter you renamed. Replace every
> field in one pass: the params, the `self.` assignments, the payload, and the
> render all refer to the **same** set of fields you chose in step 0.

Filled in, that skeleton is exactly the Caesar cipher:

```python
@register_puzzle
class CaesarCipherPuzzle(Puzzle):
    """A Caesar-shifted message for players to decode."""

    type_name = "caesar_cipher"

    def __init__(self, id: str, *, shift: int, ciphertext: str) -> None:
        super().__init__(id)
        self.shift = shift % 26
        self.ciphertext = ciphertext
```

Notes:

- **`type_name` must be unique and stable.** It is the key written to disk and
  looked up on load. Renaming it later breaks every saved hunt that used it.
- **`id`** is the puzzle's identifier within a hunt (e.g. `"c1"`). The base
  `__init__` stores it; always call `super().__init__(id)` first.
- Take the rest of your data as **keyword-only** arguments (`*,`) so call sites
  read clearly and you can reorder fields freely.
- The `__init__` should accept the *canonical* state. If you want to normalize
  or validate, do it here (Caesar normalizes `shift % 26`). For a puzzle with
  structural rules, raise `PuzzleError` from a `_validate()` helper called at the
  end of `__init__` — see `r4.py` for a thorough example. `PuzzleError` is a
  design-time aid ("you built this puzzle wrong"), never player grading.

---

## Step 2 — (Optional) Add an authoring constructor

`__init__` takes canonical state, but you usually want to author from something
friendlier. Add a classmethod that does the encoding for you. Caesar lets you
start from plaintext:

```python
    @classmethod
    def from_plaintext(cls, id: str, plaintext: str, shift: int) -> CaesarCipherPuzzle:
        """Author a puzzle from plaintext by encoding the prompt the player sees."""
        return cls(id, shift=shift % 26, ciphertext=_caesar(plaintext, shift))
```

This is purely ergonomic — the library never calls it. It is where the puzzle's
"forward" logic (here, `_caesar`) lives. Keep such helpers as module-level
functions (Caesar's `_caesar`) so they are easy to unit-test in isolation.

---

## Step 3 — Implement serialization (`to_payload` / `from_payload`)

These two methods are the round-trip seam. The codec wraps your payload as
`{"type": type_name, "id": id, "payload": to_payload()}` on save, and on load
calls `build_puzzle(type, id, payload)` → your `from_payload`. You only have to
handle the *type-specific fields* — `type` and `id` are handled for you.

```python
    def to_payload(self) -> dict[str, Any]:
        return {"shift": self.shift, "ciphertext": self.ciphertext}

    @classmethod
    def from_payload(cls, id: str, payload: dict[str, Any]) -> CaesarCipherPuzzle:
        return cls(id, shift=payload["shift"], ciphertext=payload["ciphertext"])
```

Rules:

- **`to_payload` output must be JSON-safe** and contain exactly enough to rebuild
  the puzzle. Don't include derived fields (no `solution`).
- **`from_payload(to_payload())` must reconstruct a value-equal puzzle.** This is
  the keystone invariant the whole serialization layer relies on; the base
  `__eq__` compares `id` + `to_payload()`, so as long as you store and restore
  the same fields, equality holds for free.
- For fields added later, read them defensively so old saved files still load —
  e.g. `payload.get("reveal_grid", True)` as `r4.py` does.

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
constant, so it aggregates to a single copy in the binder). A complete `render`
can be two lines:

```python
from puzzcombinator.rendering import presets

def render(self, audience: Audience) -> RenderFragment:
    if audience is Audience.PLAYER:
        return presets.text(self.ciphertext, title="Cipher", id=self.id, monospace=True)
    return presets.text(self.solution, title="Answer", id=self.id)
```

The three helpers, in increasing order of control:

- **`presets.text(value, *, title=None, id=None, monospace=False)`** — a plain
  string, escaped. `monospace=True` renders a `<pre>` (codes, coordinates, grids).
- **`presets.image(data_uri, *, alt="", caption=None, title=None, id=None)`** — an
  inline image with an optional caption. Pass a data URI to keep the hunt
  self-contained.
- **`presets.card(body, *, title=None, id=None)`** — your own inner HTML with the
  default styling. `body` is inserted verbatim, so escape untrusted text yourself.
  Use it to combine pieces — e.g. an image *and* a GM answer line (see `image.py`,
  which builds its `GAME_MASTER` body then wraps it with `presets.card`).

For many puzzles you are **done at this point** — skip to step 5. Read on only if
your puzzle wants custom CSS or precise SVG geometry.

### Full control: building a `RenderFragment` by hand

When the presets aren't enough, build the fragment yourself with
`RenderFragment.html(...)` / `RenderFragment.svg(...)` and your own `styles=` — as
the Caesar cipher does (it styles its ciphertext) and R4 does (inline SVG grids).

> **The `solution` property below is not part of the contract.** It is just a
> convenience Caesar defines *for itself* to compute its answer once and render
> it. There is no required "solution" method, and nothing constrains its type or
> name — R4 calls its answer `message: str`, crossword exposes both
> `emergent_word: str` *and* structured `slots()`. Return whatever type fits your
> answer key (string, list of cells, dict…), or skip the accessor and compute it
> inline in the `GAME_MASTER` branch. The **only** value that must be a string is
> the `RenderFragment` markup your `render` ultimately returns.

```python
    @property
    def solution(self) -> str:           # Caesar's own helper — optional, type is its choice
        """The decoded message — shown in the game-master answer key."""
        return _caesar(self.ciphertext, -self.shift)

    def render(self, audience: Audience) -> RenderFragment:
        if audience is Audience.PLAYER:
            return RenderFragment.html(
                f'<section class="puzzle cipher" data-id="{html.escape(self.id)}">'
                f"<h3>Cipher</h3>"
                f"<p>Decode this message:</p>"
                f'<pre class="ciphertext">{html.escape(self.ciphertext)}</pre>'
                f"</section>",
                styles=_CSS,
            )
        return RenderFragment.html(
            f'<section class="answer cipher" data-id="{html.escape(self.id)}">'
            f"<p>Caesar shift {self.shift} &rarr; "
            f"<strong>{html.escape(self.solution)}</strong></p>"
            f"</section>",
            styles=_CSS,
        )
```

Key points when building a fragment by hand:

- **The fragment carries its own CSS.** Pass `styles=` with CSS scoped to your
  own class names (Caesar's `_CSS = ".cipher .ciphertext { ... }"`). The binder
  aggregates every fragment's `styles` into one `<head>`, so **you never edit the
  binder to add styling** — this is exactly why the binder stays puzzle-agnostic.
- **HTML or SVG.** Use `RenderFragment.html(...)` for markup, or
  `RenderFragment.svg(...)` for an inline `<svg>...</svg>` when you need precise
  geometry (grids, boards). SVG embeds directly in the HTML binder and prints
  sharply — see `r4.py`.
- **Escape everything user-supplied** with `html.escape(...)` to avoid breaking
  the markup.
- Put a `data-id` on your root element and use stable class names; it makes the
  output easy to style and debug.
- Derive the solution (don't store it). Caesar exposes a `solution` property and
  only renders it in the `GAME_MASTER` branch.

---

## Step 5 — (Optional) Override `player_artifacts()` for multi-sheet puzzles

`player_artifacts()` returns the printable player-facing piece(s). The default
is fine for most puzzles — it wraps a single `render(PLAYER)` into one artifact:

```python
    # default, provided by the base class — no need to write this:
    def player_artifacts(self) -> list[Artifact]:
        return [Artifact("puzzle", self.render(Audience.PLAYER))]
```

Override it **only** when the physical puzzle is several separate sheets that
print on their own pages. The R4 decoder is the canonical example — its grid and
its cut-out grille are two physical pieces:

```python
    def player_artifacts(self) -> list[Artifact]:
        """Grid and decoder as separate printable sheets (the decoder is cut out)."""
        assets = self.svg_assets(Audience.PLAYER)
        return [
            Artifact("grid", RenderFragment.svg(assets["grid"])),
            Artifact("decoder", RenderFragment.svg(assets["decoder"])),
        ]
```

Each `Artifact` has a short filename-safe `slug` (`"grid"`, `"decoder"`) and a
`fragment`. The binder writes one player file per artifact, keyed
`players/<puzzle.id>-<slug>.{html,svg}`.

---

## Step 6 — Export the class

Make the class importable and ensure it self-registers. Add it in **two** places:

1. `src/puzzcombinator/puzzles/__init__.py`:

   ```python
   from puzzcombinator.puzzles.cipher import CaesarCipherPuzzle
   # ...
   __all__ = ["CaesarCipherPuzzle", ...]
   ```

2. the package `src/puzzcombinator/__init__.py` (so users can do
   `from puzzcombinator import CaesarCipherPuzzle`):

   ```python
   from puzzcombinator.puzzles.cipher import CaesarCipherPuzzle
   # ...
   __all__ = ["CaesarCipherPuzzle", ...]
   ```

> **Why this matters for loading.** `@register_puzzle` only runs when the module
> is imported. The package `__init__` imports every built-in puzzle on import,
> which is what populates the registry so `from_json` can rebuild puzzles by
> `type_name`. If you skip the export, your puzzle authors fine but **fails to
> deserialize** with a `RegistryError: unknown puzzle type`.

---

## Step 7 — Add a test file

Mirror the existing tests in `tests/puzzles/` (one file per puzzle, e.g.
`tests/puzzles/test_cipher.py`). At minimum cover:

- **forward logic** (encode/decode round-trips of your module helpers);
- **authoring constructor** produces the expected canonical state;
- **solution is derivable** (the GM view matches the original input);
- **payload round-trip**: `from_payload(to_payload()) == original`;
- **equality / hash** behaves (value equality, hashable in a set).

```python
def test_payload_roundtrip() -> None:
    puzzle = CaesarCipherPuzzle.from_plaintext("c1", plaintext="CODE", shift=4)
    rebuilt = CaesarCipherPuzzle.from_payload("c1", puzzle.to_payload())
    assert rebuilt == puzzle
```

It is also worth a test that `render(PLAYER)` does **not** leak the answer and
`render(GAME_MASTER)` **does** show it.

---

## Step 8 — Verify against the "done" bar

From the repo root:

```bash
pip install -e ".[dev]"
pytest --cov=puzzcombinator
ruff check . && ruff format --check . && mypy src/puzzcombinator
```

All must be clean. (100% coverage is required on `core/`; your puzzle should be
well covered too.) If your puzzle touches the end-to-end flow, regenerate the
reference output and eyeball it:

```bash
python examples/mock_hunt.py    # writes examples/mock_hunt_out/
```

---

## Handling media (images and other binary assets)

Sooner or later a puzzle *is* a picture — a photo clue, a rebus, a scrambled
image. This seems to collide with "the payload must be JSON-safe", but it
doesn't: the rule that actually matters is that a serialized hunt is
**self-contained** (copy the JSON and you have copied the whole hunt). The way to
honour both is the same trick the R4 puzzle already uses for its SVG — **embed
the media inline**. For raster bytes that means a **data URI**:
`data:image/png;base64,<...>`. It is just a (longer) string, so:

- `to_payload()` stays JSON-safe and `from_json(to_json(g)) == g` holds
  **byte-exact** — the bytes are *part of* the compared value, so equality can
  never silently drift from what renders;
- `render()` stays pure — it emits `<img src="data:...">`, no file reads, no
  network;
- the output bundle stays `dict[str, str]` and `write_bundle` is unchanged — the
  player page and the binder embed the image with zero asset-copying machinery;
- the hunt stays portable — hand the JSON (or the printed page) to anyone and the
  image travels with it.

`ImagePuzzle` (`image.py`) is the worked example. Its canonical state is the data
URI plus a player `prompt` and an optional game-master `answer`:

```python
@classmethod
def from_bytes(cls, id, data: bytes, *, mime: str, ...) -> ImagePuzzle:
    return cls(id, data_uri=_data_uri(data, mime), ...)   # _data_uri = base64-encode

def render(self, audience):
    parts = [f'<img src="{html.escape(self.data_uri)}" alt="{html.escape(self.alt)}"/>', ...]
    if audience is Audience.GAME_MASTER and self.answer is not None:
        parts.append(f'<p class="answer">Answer: {html.escape(self.answer)}</p>')
    return RenderFragment.html("".join(parts), styles=_CSS)
```

Guidance when your puzzle carries media:

- **Author from bytes, store the data URI.** Provide a `from_bytes(id, data, *,
  mime=...)` constructor (and optionally a `from_file` convenience). Keep
  filesystem reads confined to such authoring constructors — `render`,
  `to_payload`, and `from_payload` must never touch disk.
- **Vector art is free.** If the media is line art / a grid / a board, emit inline
  SVG via `RenderFragment.svg(...)` (text, tiny, prints sharply) — no base64
  needed. Reach for a data URI only for genuine raster images.
- **Bloat is acceptable at hunt scale.** A handful of images base64-inlined is
  fine. There is intentionally no size limit.

**The escape hatch (don't build it until you need it).** If a future puzzle needs
*large* or *shared* media where inlining hurts, the deliberate upgrade is an
**asset store**: the payload holds a stable reference (e.g. a content hash), the
bytes travel beside the JSON in an `assets/` directory, and the bundle is widened
to carry `bytes`. That is strictly more machinery and gives up nothing the data
URI already gives you for small media — so treat it as a documented, discussed
change, not a default.

---

## The whole recipe, condensed

1. New file in `puzzles/`; `class MyPuzzle(Puzzle)`, `@register_puzzle`.
2. Set a unique, stable `type_name`.
3. `__init__(self, id, *, ...)` storing canonical state; `super().__init__(id)`.
4. (Optional) a `from_...` authoring constructor for friendly input.
5. `to_payload()` / `from_payload()` — JSON-safe, round-trip exact.
6. `render(audience)` — player view vs. GM answer key; carry your own `styles`.
7. (Optional) `player_artifacts()` only if it prints as multiple sheets.
8. Export in `puzzles/__init__.py` **and** the package `__init__.py`.
9. Add `tests/puzzles/test_mypuzzle.py`.
10. `pytest`, `ruff`, `mypy` clean.

**You never edit `core/`, `serialization/`, or `rendering/`.** If you find
yourself needing to, stop — the design intends the puzzle to be fully
self-describing through the `Puzzle` ABC and the registry. Reach for a discussion
before breaking that boundary.

---

*Next: composing puzzles into a hunt — building the graph, and what nodes and
edges mean.*
