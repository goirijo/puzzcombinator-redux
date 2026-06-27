"""The first concrete puzzle: a Caesar cipher.

A zero-dependency vertical slice of the whole abstraction. The
:class:`CaesarCipherPuzzle` generator is authored from plaintext (which encodes
the prompt); it emits three :class:`CipherArtifact`\\ s — ``cipher`` (the ciphertext
to decode), ``shift`` (the Caesar shift), and ``solution`` (the decoded answer).
The artifact serializes round-trip; the solution is *derivable* by decoding, so
there's no separate answer to store or check.
"""

from __future__ import annotations

import html
from typing import Any

from puzzcombinator.artifacts.registry import register_artifact
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.rendering.fragment import Artifact, RenderFragment

_CSS = ".cipher .ciphertext { font-size: 1.25rem; letter-spacing: 0.1em; }"


def _caesar(text: str, shift: int) -> str:
    """Shift letters by ``shift`` (mod 26); leave non-letters untouched."""
    shift %= 26
    out: list[str] = []
    for ch in text:
        if "A" <= ch <= "Z":
            out.append(chr((ord(ch) - ord("A") + shift) % 26 + ord("A")))
        elif "a" <= ch <= "z":
            out.append(chr((ord(ch) - ord("a") + shift) % 26 + ord("a")))
        else:
            out.append(ch)
    return "".join(out)


@register_artifact
class CipherArtifact(Artifact):
    """A Caesar-shifted message. Renders one of three views by which payload field is
    set: the decoded ``solution``, the Caesar ``shift`` alone, or (neither set) the
    ciphertext to decode."""

    type_name = "caesar_cipher"

    def __init__(
        self,
        ciphertext: str,
        *,
        shift: int | None = None,
        solution: str | None = None,
        name: str = "cipher",
        id: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id)
        self.ciphertext = ciphertext
        self.shift = shift
        self.solution = solution

    def to_payload(self) -> dict[str, Any]:
        return {"ciphertext": self.ciphertext, "shift": self.shift, "solution": self.solution}

    @classmethod
    def from_payload(cls, *, name: str, id: str, payload: dict[str, Any]) -> CipherArtifact:
        return cls(
            payload["ciphertext"],
            shift=payload.get("shift"),
            solution=payload.get("solution"),
            name=name,
            id=id,
        )

    def render(self) -> RenderFragment:
        if self.solution is not None:
            kind = "answer"
            body = f"<p>Decoded: <strong>{html.escape(self.solution)}</strong></p>"
        elif self.shift is not None:
            kind = "hint"
            body = f"<p>Caesar shift: <strong>{self.shift}</strong></p>"
        else:
            kind = "puzzle"
            body = (
                "<h3>Cipher</h3>"
                "<p>Decode this message:</p>"
                f'<pre class="ciphertext">{html.escape(self.ciphertext)}</pre>'
            )
        return RenderFragment.html(
            f'<section class="{kind} cipher" data-id="{html.escape(self.id)}">{body}</section>',
            styles=_CSS,
        )


class CaesarCipherPuzzle(Puzzle):
    """Generates a Caesar-shifted message for players to decode."""

    type_name = "caesar_cipher"

    def __init__(self, id: str | None = None, *, shift: int, ciphertext: str) -> None:
        super().__init__(id)
        self.shift = shift % 26
        self.ciphertext = ciphertext

    @classmethod
    def from_plaintext(
        cls, plaintext: str, shift: int, *, id: str | None = None
    ) -> CaesarCipherPuzzle:
        """Author a puzzle from plaintext by encoding the prompt the player sees."""
        return cls(id, shift=shift % 26, ciphertext=_caesar(plaintext, shift))

    @property
    def solution(self) -> str:
        """The decoded message — shown in the game-master answer key."""
        return _caesar(self.ciphertext, -self.shift)

    def _artifacts(self) -> list[Artifact]:
        """Build this puzzle's three artifacts.

        Keys:
        - ``cipher`` — the ciphertext for the player to decode.
        - ``shift`` — the Caesar shift, as a revealed answer-key hint.
        - ``solution`` — the decoded plaintext message.
        """
        return [
            CipherArtifact(self.ciphertext, name="cipher", id=self.artifact_id("cipher")),
            CipherArtifact(
                self.ciphertext, shift=self.shift, name="shift", id=self.artifact_id("shift")
            ),
            CipherArtifact(
                self.ciphertext,
                solution=self.solution,
                name="solution",
                id=self.artifact_id("solution"),
            ),
        ]
