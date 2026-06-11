# Rendering

The **rendering** layer is the bottom of the library (stdlib only, no upward
dependencies, so every other layer can import it without a cycle). It owns three
things: the format-neutral render primitive (`RenderFragment`), the `Artifact` ABC that
produces it, and the ready-made factories + file writers built on top.

> Companion to `artifacts/ARTIFACTS.md` (which covers the concrete artifact *types*).
> This guide covers *how* an artifact turns into markup and a file. The whole-hunt
> output layer — `binder.py` — is **stale / not yet migrated**: its
> player-vs-answer-key routing hasn't been rebuilt and its tests are skipped. Ignore
> it as a reference until its phase lands.

## `RenderFragment` — the format-neutral primitive

A `RenderFragment` is a self-contained snippet of markup plus the CSS it needs:

```python
RenderFragment(markup: str, kind: Literal["html", "svg"] = "html", styles: str = "")
RenderFragment.html(markup, *, styles="")   # a body fragment (a <section>, <p>, …)
RenderFragment.svg(markup, *, styles="")     # an inline <svg>…</svg>
```

`styles` is optional CSS keyed by the fragment's own class names; a consumer aggregates
the `styles` of every fragment it embeds into one place, so an artifact carries its own
styling and the consumer never needs artifact-specific CSS.

### The `kind` distinction (`html` vs `svg`) — what it actually means

`kind` is **metadata, not behavior**. `RenderFragment.html` and `.svg` are identical
except for the value they stamp; nothing in `fragment.py` branches on it. The tag
records one fact a consumer can't safely assume: **is this markup a standalone document
or a body snippet?**

- **HTML markup is a fragment** — it only renders embedded inside `<html><body>…`. It
  can never stand alone as a file.
- **SVG markup is a complete, self-describing document** (`<svg xmlns=…>…</svg>`) — valid
  *both* embedded inline in HTML *and* as a standalone `.svg` file.

So the tag matters in exactly one place:

- **Embedding** (a composite, a gallery, a binder page): *no difference.* Inline `<svg>`
  drops straight into an HTML `<body>` alongside `<section>`s. Consumers concatenate
  `.markup` regardless of kind.
- **Writing a standalone file:** *divergence.* An `svg` fragment is best written **raw**
  to a native `.svg` (a real vector asset — print-sharp, openable in vector tools); an
  `html` fragment must be wrapped in `<html><body>`.

Why an SVG flavor exists at all: artifacts needing **precise geometry** (a grid, a
grille, a generated diagram) render as inline SVG — vector, coordinate-exact, crisp at
any scale. Flowed prose (clues, captions, answers) stays HTML. It's an authoring choice
about the right drawing medium, recorded as `kind`.

## `Artifact` — the renderable ABC

`Artifact` (also in `fragment.py`) is the universal *thing that renders* carried on a
graph edge: a registry-backed, serializable renderable that turns its own payload into a
`RenderFragment` via a pure `render()` — see `ARTIFACTS.md` for the full
type/registry/serialization story.

## `presets.py` — fragment factories (the easy path)

Hand a raw value, get back a styled fragment that already carries its CSS:

- `presets.text(value, *, title=None, id=None, monospace=False)` — a string as a card.
- `presets.image(data_uri, *, alt="", caption=None, title=None, id=None)` — an `<img>`.
- `presets.card(body, *, title=None, id=None)` — your own inner markup, default styling.

All preset fragments share one CSS constant, so a whole document's worth aggregates to a
single copy. Drop to `RenderFragment.html(...)` / `.svg(...)` with your own `styles=`
only when a preset isn't enough. The typed presets escape untrusted text for you;
`card` and raw fragments do not.

## Writing one artifact to a file

All the single-artifact file writers live in **`rendering/export.py`** and need only the
`Artifact` ABC (the type-specific knowledge lives in each artifact's `render()` /
`native()`, so they name no concrete type):

- `html_document(title, body, styles="") -> str` — wrap body markup + CSS in a minimal
  standalone HTML document (pure, no I/O).
- `write_html(artifact, out_dir) -> Path` — render *any* artifact and write `{id}.html`.
  Works for everything because it goes through `render()` (an inline `<svg>` lands in the
  body and renders fine). Answers *"how does this look?"*
- `write_artifact(artifact, out_dir) -> Path` — the *native* exporter. Asks the artifact
  for its native form via `native()` and writes that (a `.txt`, decoded image bytes with
  the extension from the mime, a raw `.svg`), falling back to `write_html` when there is
  none (a composite). Answers *"give me the thing itself."* No per-type dispatch — a new
  artifact type is handled by declaring its own `native()`.
- `write_artifacts(artifacts, out_dir) -> list[Path]` — `write_artifact` over a whole
  `{name: Artifact}` bag, each file named by its **id**. The inspection helper a puzzle
  demo uses to eyeball all of `puzzle.artifacts()` at once.

Every writer takes an artifact and an **output directory**, derives `{id}.{ext}`, and
returns the written `Path`. A composite has no single native form, so it only has the
HTML view. `examples/artifacts/showcase.py` exercises all of this and assembles a
`gallery.html` (via `html_document`).

### Why they all live here (a layering note worth keeping)

The native exporter once needed concrete-type knowledge (`.markup`, `.data_uri`, `.text`)
and so lived up in the *artifact* layer. Moving that knowledge onto the artifacts
themselves — each declares its own native `(extension, bytes)` via `native()` — made the
exporter agnostic, so it now sits beside `write_html` in `rendering/`, needing only the
ABC. The whole family points *downward* at the `Artifact` interface; none reaches up at a
concrete type.
