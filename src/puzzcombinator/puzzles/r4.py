"""The R4 decoder: a turning-grille (rotating-grille) cipher.

An NxN grid of seemingly random letters hides a message. An NxN *decoder* grille
has some squares open and the rest opaque. Overlaying the grille, reading the
letters showing through the open squares, then rotating the grille 90 degrees and
repeating four times in total, reveals the message in order.

The grille is built so that each four-cell rotation orbit has exactly one open
square; across the four rotations every cell is therefore read exactly once. For
odd N the centre cell is its own orbit and is always opaque (never read).

Re-derived in pure Python (no numpy) from the old repo's ``encoder`` module, and
rendered as inline SVG (no cairo). Unused cells are filled with random letters so
the grid reads as gibberish without the decoder.
"""

from __future__ import annotations

import html
import math
import random
import string
from collections.abc import Iterable
from typing import Any

from puzzcombinator.artifacts.registry import register_artifact
from puzzcombinator.artifacts.text import TextArtifact
from puzzcombinator.errors import PuzzleError
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.rendering.fragment import Artifact, Audience, RenderFragment

OPEN = "O"
SHADED = "#"

Cell = tuple[int, int]


# -- pure-Python generator ------------------------------------------------


def _grid_dim(n: int) -> int:
    """Smallest grid dimension that fits ``n`` message letters.

    ``ceil(sqrt(n))``, bumped by one when an odd grid (which loses its centre
    cell) would be too small.
    """
    dim = math.ceil(math.sqrt(n)) if n > 0 else 2
    if dim % 2 == 1 and dim * dim - 1 < n:
        dim += 1
    return max(dim, 2)


def _rot90(cell: Cell, dim: int) -> Cell:
    """One 90-degree rotation of a cell coordinate (order 4; fixes odd centre)."""
    r, c = cell
    return (c, dim - 1 - r)


def _rotate_cw(matrix: list[list[bool]]) -> list[list[bool]]:
    """Rotate a square boolean matrix 90 degrees clockwise.

    A cell's content moves from ``(r, c)`` to :func:`_rot90` ``(r, c)``, so the
    matrix rotation and the orbit map agree.
    """
    dim = len(matrix)
    return [[matrix[dim - 1 - c][r] for c in range(dim)] for r in range(dim)]


def _make_grille(dim: int, rng: random.Random) -> list[list[bool]]:
    """Build a valid grille: one open hole per rotation orbit (``True`` = open)."""
    grille = [[False] * dim for _ in range(dim)]
    used: set[Cell] = set()
    if dim % 2 == 1:
        used.add((dim // 2, dim // 2))  # centre is its own orbit; never a hole
    cells = [(r, c) for r in range(dim) for c in range(dim)]
    rng.shuffle(cells)
    for cell in cells:
        if cell in used:
            continue
        grille[cell[0]][cell[1]] = True
        orbit = cell
        for _ in range(4):
            used.add(orbit)
            orbit = _rot90(orbit, dim)
    return grille


def _read_sequence(grille: list[list[bool]], dim: int) -> list[Cell]:
    """Grid cells in the order they are read across the four rotations.

    A permutation of every non-centre cell (each read exactly once).
    """
    g = [row[:] for row in grille]
    sequence: list[Cell] = []
    for _ in range(4):
        for r in range(dim):
            for c in range(dim):
                if g[r][c]:
                    sequence.append((r, c))
        g = _rotate_cw(g)
    return sequence


def _fill(message: str, sequence: list[Cell], dim: int, rng: random.Random) -> list[str]:
    """A grid of random letters with ``message`` laid along the read sequence."""
    grid = [[rng.choice(string.ascii_uppercase) for _ in range(dim)] for _ in range(dim)]
    for i, ch in enumerate(message):
        r, c = sequence[i]
        grid[r][c] = ch
    return ["".join(row) for row in grid]


# -- rendering ------------------------------------------------------------

_TS = 40  # cell size, px
_PAD = 16  # margin, px (also hosts the orientation marker)


def _svg(
    dim: int,
    *,
    letters: list[str] | None = None,
    shaded: set[Cell] | None = None,
) -> str:
    """Render a dim x dim grid as inline SVG, with a top-left orientation marker."""
    span = dim * _TS
    full = span + 2 * _PAD
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{full}" height="{full}" '
        f'viewBox="0 0 {full} {full}" class="r4-svg">',
        f'<rect x="{_PAD}" y="{_PAD}" width="{span}" height="{span}" '
        f'fill="white" stroke="black" stroke-width="2"/>',
    ]
    for r, c in sorted(shaded or set()):
        x, y = _PAD + c * _TS, _PAD + r * _TS
        parts.append(f'<rect x="{x}" y="{y}" width="{_TS}" height="{_TS}" fill="black"/>')
    for i in range(1, dim):
        off = _PAD + i * _TS
        parts.append(
            f'<line x1="{off}" y1="{_PAD}" x2="{off}" y2="{_PAD + span}" '
            f'stroke="black" stroke-width="1"/>'
        )
        parts.append(
            f'<line x1="{_PAD}" y1="{off}" x2="{_PAD + span}" y2="{off}" '
            f'stroke="black" stroke-width="1"/>'
        )
    if letters is not None:
        for r in range(dim):
            for c in range(dim):
                cx = _PAD + c * _TS + _TS // 2
                cy = _PAD + r * _TS + _TS // 2
                parts.append(
                    f'<text x="{cx}" y="{cy}" text-anchor="middle" '
                    f'dominant-baseline="central" font-family="monospace" '
                    f'font-size="{int(_TS * 0.55)}">{html.escape(letters[r][c])}</text>'
                )
    # Orientation marker: a red right-triangle in the top-left margin corner.
    parts.append('<polygon points="2,2 13,2 2,13" fill="red"/>')
    parts.append("</svg>")
    return "".join(parts)


# -- artifact -------------------------------------------------------------


@register_artifact
class R4PieceArtifact(Artifact):
    """One printable R4 sheet — the letter grid or the decoder grille — as inline
    SVG. Renders exactly what its payload specifies (letters and/or shaded cells),
    so the generator bakes the player (blank/revealed) or game-master (solved) view
    into each instance."""

    type_name = "r4_piece"

    def __init__(
        self,
        *,
        dim: int,
        letters: list[str] | None = None,
        shaded: list[tuple[int, int]] | None = None,
        name: str,
        audience: Audience = Audience.PLAYER,
        id: str | None = None,
    ) -> None:
        super().__init__(name=name, audience=audience, id=id)
        self.dim = dim
        self.letters = letters
        self.shaded = [(int(r), int(c)) for r, c in shaded] if shaded is not None else None

    def to_payload(self) -> dict[str, Any]:
        return {
            "dim": self.dim,
            "letters": list(self.letters) if self.letters is not None else None,
            "shaded": [[r, c] for r, c in self.shaded] if self.shaded is not None else None,
        }

    @classmethod
    def from_payload(
        cls, *, name: str, audience: Audience, id: str, payload: dict[str, Any]
    ) -> R4PieceArtifact:
        return cls(
            dim=payload["dim"],
            letters=payload.get("letters"),
            shaded=payload.get("shaded"),
            name=name,
            audience=audience,
            id=id,
        )

    def render(self) -> RenderFragment:
        shaded = set(self.shaded) if self.shaded is not None else None
        return RenderFragment.svg(_svg(self.dim, letters=self.letters, shaded=shaded))


# -- puzzle ---------------------------------------------------------------


class R4DecoderPuzzle(Puzzle):
    """A turning-grille cipher: a letter grid plus a rotating decoder."""

    type_name = "r4_decoder"

    def __init__(
        self,
        id: str | None = None,
        *,
        grid: Iterable[str],
        grille: Iterable[str],
        message_length: int,
        reveal_grid: bool = True,
        reveal_decoder: bool = True,
    ) -> None:
        super().__init__(id)
        self.grid: list[str] = [row.upper() for row in grid]
        self.grille: list[str] = list(grille)
        self.message_length = message_length
        #: Whether the player view shows the grid's letters (else a blank grid to fill).
        self.reveal_grid = reveal_grid
        #: Whether the player view shows the decoder's shading (else blank, to shade in).
        self.reveal_decoder = reveal_decoder
        self._validate()

    @classmethod
    def from_message(
        cls,
        message: str,
        *,
        size: int | None = None,
        seed: int | None = None,
        reveal_grid: bool = True,
        reveal_decoder: bool = True,
        id: str | None = None,
    ) -> R4DecoderPuzzle:
        """Author a puzzle by encoding ``message`` (letters only; spacing dropped)."""
        cleaned = "".join(ch for ch in message.upper() if "A" <= ch <= "Z")
        dim = size if size is not None else _grid_dim(len(cleaned))
        rng = random.Random(seed)
        grille_bool = _make_grille(dim, rng)
        sequence = _read_sequence(grille_bool, dim)
        if len(cleaned) > len(sequence):
            raise PuzzleError(
                f"message of {len(cleaned)} letters exceeds capacity {len(sequence)} for size {dim}"
            )
        grid = _fill(cleaned, sequence, dim, rng)
        grille = ["".join(OPEN if cell else SHADED for cell in row) for row in grille_bool]
        return cls(
            id,
            grid=grid,
            grille=grille,
            message_length=len(cleaned),
            reveal_grid=reveal_grid,
            reveal_decoder=reveal_decoder,
        )

    # -- derived structure -------------------------------------------------

    @property
    def size(self) -> int:
        return len(self.grid)

    def _grille_bool(self) -> list[list[bool]]:
        return [[ch == OPEN for ch in row] for row in self.grille]

    @property
    def hole_cells(self) -> list[Cell]:
        """Open (hole) cells of the decoder, in row-major order."""
        return [
            (r, c) for r, row in enumerate(self.grille) for c, ch in enumerate(row) if ch == OPEN
        ]

    @property
    def reading_sequence(self) -> list[Cell]:
        """Grid cells in the order the message is read across the four rotations."""
        return _read_sequence(self._grille_bool(), self.size)

    @property
    def message(self) -> str:
        """The decoded message (the game-master answer key)."""
        seq = self.reading_sequence[: self.message_length]
        return "".join(self.grid[r][c] for r, c in seq)

    def _validate(self) -> None:
        grid, grille = self.grid, self.grille
        dim = len(grid)
        if dim == 0:
            raise PuzzleError("R4 grid must be non-empty")
        for name, rows in (("grid", grid), ("grille", grille)):
            if len(rows) != dim or any(len(row) != dim for row in rows):
                raise PuzzleError(f"R4 {name} must be a square {dim}x{dim} grid")
        for row in grid:
            for ch in row:
                if not ("A" <= ch <= "Z"):
                    raise PuzzleError(f"R4 grid cell {ch!r} must be A-Z")
        for row in grille:
            for ch in row:
                if ch not in (OPEN, SHADED):
                    raise PuzzleError(f"R4 grille cell {ch!r} must be {OPEN!r} or {SHADED!r}")
        if dim % 2 == 1:
            mid = dim // 2
            if grille[mid][mid] != SHADED:
                raise PuzzleError("odd-sized R4 grille must have an opaque centre")
        self._validate_orbits(dim)
        capacity = 4 * len(self.hole_cells)
        if not 0 <= self.message_length <= capacity:
            raise PuzzleError(f"message_length {self.message_length} out of range [0, {capacity}]")

    def _validate_orbits(self, dim: int) -> None:
        """Each four-cell rotation orbit must hold exactly one open square."""
        grille_bool = self._grille_bool()
        seen: set[Cell] = set()
        for r in range(dim):
            for c in range(dim):
                if (r, c) in seen:
                    continue
                orbit: set[Cell] = set()
                cell = (r, c)
                for _ in range(4):
                    orbit.add(cell)
                    cell = _rot90(cell, dim)
                seen |= orbit
                if len(orbit) == 1:
                    continue  # the odd-N centre; its opacity is checked above
                opens = sum(1 for rr, cc in orbit if grille_bool[rr][cc])
                if opens != 1:
                    raise PuzzleError(
                        f"R4 grille orbit {sorted(orbit)} must have exactly one open cell"
                    )

    # -- artifacts ---------------------------------------------------------

    def _shaded_cells(self) -> list[tuple[int, int]]:
        dim = self.size
        return [(r, c) for r in range(dim) for c in range(dim) if self.grille[r][c] == SHADED]

    def _artifacts(self, audience: Audience) -> list[Artifact]:
        """Grid and grille as separate printable sheets (the grille is cut out);
        the game-master set adds a text solution (message + reading order)."""
        gm = audience is Audience.GAME_MASTER
        dim = self.size
        grid_letters = self.grid if (gm or self.reveal_grid) else None
        grille_shaded = self._shaded_cells() if (gm or self.reveal_decoder) else None
        out: list[Artifact] = [
            R4PieceArtifact(
                dim=dim,
                letters=grid_letters,
                name="grid",
                audience=audience,
                id=self.artifact_id("grid"),
            ),
            R4PieceArtifact(
                dim=dim,
                shaded=grille_shaded,
                name="grille",
                audience=audience,
                id=self.artifact_id("grille"),
            ),
        ]
        if gm:
            order = " -> ".join(
                f"({r},{c})" for r, c in self.reading_sequence[: self.message_length]
            )
            out.append(
                TextArtifact(
                    f"Message: {self.message}\nReading order: {order}",
                    title="R4 solution",
                    monospace=True,
                    name="solution",
                    audience=audience,
                    id=self.artifact_id("solution"),
                )
            )
        return out
