"""A crossword puzzle type.

The designer supplies a **solution grid** (rows of letters, with ``#`` for black
squares) plus the across/down clue text. The library derives the standard cell
numbering and the across/down slots from the grid, so the designer thinks in the
usual crossword terms ("1 Across", "2 Down").

A treasure-hunt crossword usually *reveals* something: pass ``highlight`` cells
and the letters at those cells, read in order, form the **emergent word** — the
clue the designer then wires onto this node's outgoing edge. The
:class:`CrosswordPuzzle` generator emits two :class:`CrosswordArtifact`\\ s —
``crossword`` (a numbered blank grid + clues) and ``solution`` (the filled grid,
answers, and emergent word). It does no answer-checking.
"""

from __future__ import annotations

import html
from collections.abc import Iterable, Mapping
from typing import Any, NamedTuple

from puzzcombinator.artifacts.registry import register_artifact
from puzzcombinator.errors import PuzzleError
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.rendering.fragment import Artifact, RenderFragment

#: The character marking a black (blocked) square in a solution grid.
BLOCK = "#"

_CSS = """
  .crossword table.grid { border-collapse: collapse; }
  .crossword table.grid td {
    width: 2.2em; height: 2.2em; border: 1px solid #000;
    text-align: center; vertical-align: middle; position: relative;
    font-size: 1.1rem; text-transform: uppercase;
  }
  .crossword table.grid td.block { background: #000; }
  .crossword table.grid td.theme { background: #fff3b0; }
  .crossword table.grid .num {
    position: absolute; top: 1px; left: 2px; font-size: 0.55rem; font-weight: normal;
  }
  .crossword .clues { display: inline-block; vertical-align: top; margin-right: 2rem; }
  .crossword .answer { font-weight: bold; }
  .crossword .len { color: #888; }
"""


class Slot(NamedTuple):
    """A numbered across/down entry derived from the grid."""

    number: int
    row: int
    col: int
    answer: str


def _analyze(
    grid: list[str],
) -> tuple[dict[tuple[int, int], int], list[Slot], list[Slot]]:
    """Derive cell numbering and across/down slots using standard crossword rules.

    A cell starts an across (down) entry when it has no open neighbour to the
    left (above) and at least one open neighbour to the right (below), i.e. it
    begins a run of two or more open cells. Numbers increment in row-major order
    over cells that start at least one entry.
    """
    height, width = len(grid), len(grid[0])

    def is_block(r: int, c: int) -> bool:
        return grid[r][c] == BLOCK

    numbering: dict[tuple[int, int], int] = {}
    across: list[Slot] = []
    down: list[Slot] = []
    number = 0

    for r in range(height):
        for c in range(width):
            if is_block(r, c):
                continue
            starts_across = (c == 0 or is_block(r, c - 1)) and (
                c + 1 < width and not is_block(r, c + 1)
            )
            starts_down = (r == 0 or is_block(r - 1, c)) and (
                r + 1 < height and not is_block(r + 1, c)
            )
            if not (starts_across or starts_down):
                continue
            number += 1
            numbering[(r, c)] = number
            if starts_across:
                cc = c
                while cc < width and not is_block(r, cc):
                    cc += 1
                across.append(Slot(number, r, c, grid[r][c:cc]))
            if starts_down:
                rr = r
                while rr < height and not is_block(rr, c):
                    rr += 1
                down.append(Slot(number, r, c, "".join(grid[i][c] for i in range(r, rr))))

    return numbering, across, down


@register_artifact
class CrosswordArtifact(Artifact):
    """A crossword grid + clues. ``reveal`` switches between the blank sheet (numbered
    grid + clue enumerations) and the filled grid with answers and emergent word."""

    type_name = "crossword"

    def __init__(
        self,
        *,
        solution: list[str],
        across: dict[int, str],
        down: dict[int, str],
        highlight: list[tuple[int, int]],
        reveal: bool,
        name: str = "crossword",
        id: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id)
        self.solution = solution
        self.across = across
        self.down = down
        self.highlight = highlight
        self.reveal = reveal

    @property
    def emergent_word(self) -> str:
        """Letters at the highlighted cells, in order — the revealed clue."""
        return "".join(self.solution[r][c] for r, c in self.highlight)

    def to_payload(self) -> dict[str, Any]:
        return {
            "solution": list(self.solution),
            "across": dict(self.across),
            "down": dict(self.down),
            "highlight": [[r, c] for r, c in self.highlight],
            "reveal": self.reveal,
        }

    @classmethod
    def from_payload(cls, *, name: str, id: str, payload: dict[str, Any]) -> CrosswordArtifact:
        return cls(
            solution=payload["solution"],
            across={int(k): v for k, v in payload.get("across", {}).items()},
            down={int(k): v for k, v in payload.get("down", {}).items()},
            highlight=[(int(r), int(c)) for r, c in payload.get("highlight", [])],
            reveal=payload["reveal"],
            name=name,
            id=id,
        )

    def render(self) -> RenderFragment:
        parts = [
            f'<section class="puzzle crossword" data-id="{html.escape(self.id)}">',
            "<h3>Crossword</h3>",
            self._render_grid(),
            self._render_clues(),
        ]
        if self.reveal and self.highlight:
            parts.append(
                f'<p class="emergent">Hidden word: '
                f"<strong>{html.escape(self.emergent_word)}</strong></p>"
            )
        parts.append("</section>")
        return RenderFragment.html("".join(parts), styles=_CSS)

    def _render_grid(self) -> str:
        numbering, _, _ = _analyze(self.solution)
        highlight = set(self.highlight)
        rows: list[str] = []
        for r, row in enumerate(self.solution):
            cells: list[str] = []
            for c, ch in enumerate(row):
                if ch == BLOCK:
                    cells.append('<td class="block"></td>')
                    continue
                css = "cell theme" if (r, c) in highlight else "cell"
                number = numbering.get((r, c))
                num_html = f'<span class="num">{number}</span>' if number else ""
                letter = html.escape(ch) if self.reveal else ""
                cells.append(f'<td class="{css}">{num_html}{letter}</td>')
            rows.append("<tr>" + "".join(cells) + "</tr>")
        return f'<table class="grid">{"".join(rows)}</table>'

    def _render_clues(self) -> str:
        _, across, down = _analyze(self.solution)

        def section(title: str, slots: list[Slot], clues: dict[int, str]) -> str:
            items: list[str] = []
            for slot in slots:
                clue = html.escape(clues.get(slot.number, ""))
                if self.reveal:
                    extra = f' <span class="answer">{html.escape(slot.answer)}</span>'
                else:
                    extra = f' <span class="len">({len(slot.answer)})</span>'
                items.append(f'<li value="{slot.number}">{clue}{extra}</li>')
            return f'<div class="clues"><h4>{title}</h4><ol>{"".join(items)}</ol></div>'

        return section("Across", across, self.across) + section("Down", down, self.down)


class CrosswordPuzzle(Puzzle):
    """Generates a crossword from its solution grid and clues."""

    type_name = "crossword"

    def __init__(
        self,
        id: str | None = None,
        *,
        solution: Iterable[str],
        across: Mapping[int, str],
        down: Mapping[int, str],
        highlight: Iterable[tuple[int, int]] | None = None,
    ) -> None:
        super().__init__(id)
        self.solution: list[str] = [row.upper() for row in solution]
        self.across: dict[int, str] = dict(across)
        self.down: dict[int, str] = dict(down)
        self.highlight: list[tuple[int, int]] = [(int(r), int(c)) for r, c in (highlight or [])]
        self._validate()

    @property
    def size(self) -> tuple[int, int]:
        """``(height, width)`` of the grid."""
        return len(self.solution), len(self.solution[0])

    def slots(self) -> tuple[list[Slot], list[Slot]]:
        """The derived ``(across, down)`` slots, in numbering order."""
        _, across, down = _analyze(self.solution)
        return across, down

    @property
    def emergent_word(self) -> str:
        """Letters at the highlighted cells, in order — the revealed clue."""
        return "".join(self.solution[r][c] for r, c in self.highlight)

    def _validate(self) -> None:
        grid = self.solution
        if not grid or not grid[0]:
            raise PuzzleError("crossword grid must be non-empty")
        width = len(grid[0])
        for r, row in enumerate(grid):
            if len(row) != width:
                raise PuzzleError(f"crossword row {r} has width {len(row)}, expected {width}")
            for ch in row:
                if ch != BLOCK and not ("A" <= ch <= "Z"):
                    raise PuzzleError(f"crossword cell {ch!r} must be a letter or {BLOCK!r}")
        _, across, down = _analyze(grid)
        dangling_across = set(self.across) - {s.number for s in across}
        dangling_down = set(self.down) - {s.number for s in down}
        if dangling_across:
            raise PuzzleError(
                f"across clues reference non-existent slots: {sorted(dangling_across)}"
            )
        if dangling_down:
            raise PuzzleError(f"down clues reference non-existent slots: {sorted(dangling_down)}")
        height = len(grid)
        for r, c in self.highlight:
            if not (0 <= r < height and 0 <= c < width):
                raise PuzzleError(f"highlight cell {(r, c)} is out of bounds")
            if grid[r][c] == BLOCK:
                raise PuzzleError(f"highlight cell {(r, c)} is a block")

    def _artifacts(self) -> list[Artifact]:
        """The blank player grid plus the revealed solution (filled grid + answers)."""

        def grid(*, reveal: bool, name: str) -> CrosswordArtifact:
            return CrosswordArtifact(
                solution=list(self.solution),
                across=dict(self.across),
                down=dict(self.down),
                highlight=list(self.highlight),
                reveal=reveal,
                name=name,
                id=self.artifact_id(name),
            )

        return [
            grid(reveal=False, name="crossword"),
            grid(reveal=True, name="solution"),
        ]
