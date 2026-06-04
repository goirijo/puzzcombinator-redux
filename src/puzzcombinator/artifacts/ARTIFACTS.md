# Artifacts

An **artifact** is the lowest layer of the library: a single, self-contained thing
that can be **serialized** and **rendered**. It is what a player is handed, or what
represents a solution — a clue, a picture, a cipher grid, a pair of coordinates.

An artifact knows two things and nothing else:

- **its own data** — the type-specific payload (a string, an image's bytes, …), and
- **how to draw itself** — `render()` turns that payload into a `RenderFragment`
  (a snippet of HTML or inline SVG, plus the CSS it needs).

An artifact does **not** know about puzzles, graphs, edges, files, or who will see
it. Whether a piece goes to the player or only into an answer key is a *placement*
decision made by a higher layer — never a property of the artifact itself.

Every artifact carries two envelope fields beside its payload:

- `name` — a generic label/key (a composite addresses its children by it; a puzzle
  generator names the pieces it emits). Defaults to a per-type value (`"text"`,
  `"image"`, `"composite"`).
- `id` — unique within a hunt; it names the artifact's output file. Auto-generated
  as `{type_name}-{uuid}` when you don't supply one. Pass an explicit `id` when you
  want a readable filename.

Artifacts compare by **value** (`type` + `id` + `name` + `payload`), which is what
makes the serialization round-trip `artifact_from_dict(artifact_to_dict(a)) == a`
hold.

---

## The primitives

A primitive is a **single thing**. Two exist today (a QR code, coordinates, and
others will follow):

### `TextArtifact` — a string

```python
from puzzcombinator.artifacts import TextArtifact

clue = TextArtifact("Search the LIBRARY")
code = TextArtifact("48.8584, 2.2945", title="Coordinates", monospace=True)
```

`title` adds a heading; `monospace=True` renders the text in a `<pre>` block
(preserving spacing — good for codes, coordinates, or ASCII art). These are
*render hints* for the one string, not separate content.

### `ImageArtifact` — a single picture

The bytes ride **inside** the artifact as a `data:` URI, so a serialized hunt stays
self-contained (copy the JSON and you have copied the image too). Author one from a
file or raw bytes:

```python
from puzzcombinator.artifacts import ImageArtifact

photo = ImageArtifact.from_file("patio.jpg", alt="the back patio")
dot   = ImageArtifact.from_bytes(png_bytes, mime="image/png", alt="a red dot")

# Or pass a data: URI directly (a non-data URI is rejected):
inline = ImageArtifact("data:image/png;base64,AAAA", alt="map")
```

`alt` is the accessibility/fallback text describing the picture — the only thing an
image carries besides the image. A caption, prompt, or answer note is *separate
content*: make it a `TextArtifact` and combine the two with a composite.

---

## Composites: aggregating artifacts

A `CompositeArtifact` holds an **ordered collection** of child artifacts and is
itself an artifact — so composites nest, serialize, and render like any other piece.
Use one whenever a clue is really several things together (a picture with a caption,
a grid beside its instructions, a riddle's lines):

```python
from puzzcombinator.artifacts import CompositeArtifact, TextArtifact, ImageArtifact

clue = CompositeArtifact(
    [
        ImageArtifact.from_file("door.jpg", alt="a green door"),
        TextArtifact("Where does this door lead?"),
    ],
    id="green-door",
)
```

`render()` draws every child in order into one HTML fragment and unions the
children's CSS (deduplicated), so a composite of mixed kinds (an SVG grid next to an
HTML caption) Just Works — inline SVG embeds directly in HTML.

Any registered artifact type can be a child; the composite round-trips its children
through the registry without knowing their concrete types.

---

## Writing a custom artifact

Reach for a custom type only when a primitive (or a composite of primitives) can't
express the thing — i.e. it has its own data shape *and* its own way of drawing
itself (a crossword grid, a cipher). The recipe is four small pieces:

```python
from typing import Any

from puzzcombinator.artifacts.registry import register_artifact
from puzzcombinator.rendering import presets
from puzzcombinator.rendering.fragment import Artifact, RenderFragment


@register_artifact                       # 2. register for deserialization
class CoordinateArtifact(Artifact):
    type_name = "coordinate"             # 1. stable registry key

    def __init__(self, lat: float, lon: float, *, name: str = "coordinate",
                 id: str | None = None) -> None:
        super().__init__(name=name, id=id)   # always call super with name/id
        self.lat = lat
        self.lon = lon

    def to_payload(self) -> dict[str, Any]:          # 3a. data -> JSON-safe dict
        return {"lat": self.lat, "lon": self.lon}

    @classmethod
    def from_payload(cls, *, name: str, id: str,     # 3b. dict -> artifact
                     payload: dict[str, Any]) -> "CoordinateArtifact":
        return cls(payload["lat"], payload["lon"], name=name, id=id)

    def render(self) -> RenderFragment:              # 4. a pure function of payload
        return presets.text(f"{self.lat}, {self.lon}", title="Go here",
                            id=self.id, monospace=True)
```

Rules to follow:

- `render()` is a **pure function of the payload** — no branching on who's asking,
  no side effects. Two equal artifacts always render the same.
- `to_payload()` must be JSON-safe (strings, numbers, lists, dicts). Whatever it
  emits, `from_payload()` must rebuild an equal artifact — that's the round-trip
  contract.
- Build markup with the **presets** (`presets.text`, `presets.image`, `presets.card`)
  so your fragment inherits the shared CSS for free. Drop to `RenderFragment.html(...)`
  / `RenderFragment.svg(...)` with your own `styles=` only when a preset isn't
  enough. Escape any untrusted text yourself (`html.escape`) — the typed presets do
  this for you, `card`/raw fragments do not.

Where it lives: an **orphan** artifact (no generator behind it — text, image, a
coordinate) goes in this package next to `text.py` / `image.py`, and is exported from
`artifacts/__init__.py`. An artifact that a `Puzzle` *generates* lives beside its
generator in the `puzzles/` layer instead (see the puzzle-authoring guide).

---

## Serializing an artifact

Each artifact serializes to a self-describing envelope `{type, id, name, payload}`
via the registry helpers — this is what a composite uses for its children and what
the graph codec composes for whole edges:

```python
from puzzcombinator.artifacts import artifact_to_dict, artifact_from_dict

data = artifact_to_dict(clue)          # -> a plain dict, ready for json.dumps
again = artifact_from_dict(data)       # rebuilt via the registry
assert again == clue                   # value-equality round-trips
```

---

## Rendering to a file to inspect in a browser

An artifact renders to a `RenderFragment` — a `markup` string (HTML, or inline SVG)
plus the `styles` (CSS) it needs. To eyeball one, wrap those in a minimal HTML
document and write it to disk:

```python
from pathlib import Path
from puzzcombinator.rendering.fragment import RenderFragment


def write_html(artifact, path: str) -> None:
    frag: RenderFragment = artifact.render()
    doc = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<style>{frag.styles}</style></head>"
        f"<body>{frag.markup}</body></html>"
    )
    Path(path).write_text(doc, encoding="utf-8")


write_html(clue, "clue.html")          # then open clue.html in a browser
```

This works for **any** artifact — a primitive, a composite, or a custom type —
because they all render the same way. An SVG-kind fragment is valid inside the
`<body>`, so it renders inline with no extra handling.

> The library's real output layer (`rendering/binder.py`) does this for a whole hunt
> — a game-master binder plus a `players/` folder, one file per artifact, with all
> the CSS aggregated into one `<head>`. The one-off helper above is just for
> inspecting a single artifact while you build it.
