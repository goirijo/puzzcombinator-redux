"""Artifact-layer showcase: every orphan artifact, rendered and round-tripped.

Run it:

    python examples/artifacts/showcase.py

This lives at the very bottom of the library — it touches no graph, no puzzle, and
no binder. It exercises only the orphan artifacts documented in
``src/puzzcombinator/artifacts/ARTIFACTS.md``:

    * TextArtifact   — a plain string (plus title / monospace render hints)
    * ImageArtifact  — a single picture carried inline as a data URI
    * SvgArtifact    — inline vector markup, generated in code
    * CompositeArtifact — several artifacts aggregated into one (and nested)

For each showcased artifact it:

    1. asserts the serialization round-trip  artifact_from_dict(artifact_to_dict(a)) == a,
    2. writes an HTML preview with ``write_html`` (works for *any* artifact), and
    3. for a primitive, also writes its **native** file (a .txt / image / .svg) with
       ``write_artifact`` — the "how it looks" vs. "the thing itself" duality.

All the file writers come from ``puzzcombinator.rendering.export``. It also assembles
one ``gallery.html`` embedding every fragment with its CSS aggregated into one
``<head>``, reusing that module's ``html_document`` wrapper.
"""

from __future__ import annotations

from pathlib import Path

from puzzcombinator.artifacts import (
    CompositeArtifact,
    ImageArtifact,
    SvgArtifact,
    TextArtifact,
    artifact_from_dict,
    artifact_to_dict,
)
from puzzcombinator.rendering.export import (
    html_document,
    write_artifact,
    write_html,
)
from puzzcombinator.rendering.fragment import Artifact

HERE = Path(__file__).parent
ASSET = HERE.parent / "assets" / "patio.jpg"
OUT = HERE / "out"


def _compass_svg(rings: int = 6) -> str:
    """Generate SVG markup in code: nested squares rotated into a rosette.

    Stands in for any computed graphic (a map, a grid, a diagram) — the point is the
    markup is *built*, not loaded, then handed straight to an SvgArtifact.
    """
    size, center = 200, 100
    squares = "".join(
        f'<rect x="30" y="30" width="140" height="140" fill="none" '
        f'stroke="#2b6cb0" stroke-width="1.5" '
        f'transform="rotate({i * 90 / rings} {center} {center})"/>'
        for i in range(rings)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}">{squares}'
        f'<circle cx="{center}" cy="{center}" r="3" fill="#c53030"/></svg>'
    )


def showcase() -> list[Artifact]:
    """Build one representative instance of every artifact capability."""
    patio = ImageArtifact.from_file(ASSET, alt="the back patio", id="image-patio")

    return [
        # --- TextArtifact: the three render hints ---
        TextArtifact("Search the LIBRARY for what comes next.", id="text-clue"),
        TextArtifact(
            "48.8584, 2.2945",
            title="Coordinates",
            monospace=True,
            id="text-coordinates",
        ),
        TextArtifact(
            "  /\\_/\\\n ( o.o )\n  > ^ <",
            title="ASCII Art",
            monospace=True,
            id="text-ascii",
        ),
        # --- ImageArtifact: a single picture, inline ---
        patio,
        # --- SvgArtifact: vector markup generated in code, rendered inline (kind=svg) ---
        SvgArtifact(_compass_svg(), id="svg-rosette"),
        # --- CompositeArtifact: a picture with its own caption ---
        CompositeArtifact(
            [
                ImageArtifact.from_file(ASSET, alt="a sunlit patio", id="image-door"),
                TextArtifact("Where the sun hits first, look beneath the third stone."),
            ],
            id="composite-photo-clue",
        ),
        # --- CompositeArtifact: a multi-line riddle (several texts as one piece) ---
        CompositeArtifact(
            [
                TextArtifact("I have cities, but no houses.", id="riddle-line0"),
                TextArtifact("I have mountains, but no trees.", id="riddle-line1"),
                TextArtifact("I have water, but no fish.", id="riddle-line2"),
            ],
            id="composite-riddle",
        ),
        # --- Nested composite: a titled section holding the image-clue + a note ---
        CompositeArtifact(
            [
                TextArtifact("STATION 3", title="Station", id="station-heading"),
                CompositeArtifact(
                    [
                        ImageArtifact.from_file(ASSET, alt="the patio again", id="image-nested"),
                        TextArtifact("Count the flagstones; that many steps north."),
                    ],
                    id="composite-inner",
                ),
                TextArtifact("ANSWER: the birdbath", title="Solution", id="station-answer"),
            ],
            id="composite-nested-station",
        ),
    ]


def write_gallery(artifacts: list[Artifact], path: Path) -> None:
    """Embed every fragment in one document, CSS aggregated and deduplicated."""
    fragments = [a.render() for a in artifacts]
    styles: dict[str, None] = {}
    for frag in fragments:
        if frag.styles:
            styles[frag.styles] = None

    cells = "".join(
        f'<figure class="cell"><figcaption><code>{a.id}</code> '
        f"<small>({a.type_name})</small></figcaption>{frag.markup}</figure>"
        for a, frag in zip(artifacts, fragments, strict=True)
    )
    gallery_css = (
        ".gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(20rem, 1fr));"
        " gap: 1.5rem; font-family: system-ui, sans-serif; padding: 1.5rem; }"
        " .cell { margin: 0; border: 1px solid #ddd; border-radius: 8px; padding: 1rem;"
        " background: #fafafa; } .cell > figcaption { margin-bottom: 0.5rem; color: #333; }"
    )
    body = f"<h1>Artifact showcase</h1><div class='gallery'>{cells}</div>"
    doc = html_document("Artifact showcase", body, gallery_css + "".join(styles))
    path.write_text(doc, encoding="utf-8")


def main() -> None:
    artifacts = showcase()
    OUT.mkdir(exist_ok=True)

    for artifact in artifacts:
        # 1. The serialization round-trip every artifact must satisfy.
        clone = artifact_from_dict(artifact_to_dict(artifact))
        assert clone == artifact, f"round-trip mismatch for {artifact.id}"

        # 2. An HTML preview for every artifact (presentation, via render()).
        written = [write_html(artifact, OUT)]

        # 3. For a primitive, also export its native file. A composite returns None from
        #    native(), so it gets only the HTML preview — no type-check needed here.
        if artifact.native() is not None:
            written.append(write_artifact(artifact, OUT))

        names = ", ".join(p.name for p in written)
        print(f"  {artifact.id:28} {artifact.type_name:10} -> {names}")

    write_gallery(artifacts, OUT / "gallery.html")
    print(f"\nWrote {len(artifacts)} artifacts + gallery.html to {OUT}")


if __name__ == "__main__":
    main()
