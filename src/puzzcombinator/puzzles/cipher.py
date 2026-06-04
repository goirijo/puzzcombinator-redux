"""The first concrete puzzle: a Caesar cipher.

A zero-dependency vertical slice of the whole abstraction. The
:class:`CaesarCipherPuzzle` generator is authored from plaintext (which encodes
the prompt); it emits a :class:`CipherArtifact` showing the ciphertext for players
and one showing the decoded solution for the game master. The artifact serializes
round-trip; the solution is *derivable* by decoding, so there's no separate answer
to store or check.
"""

from __future__ import annotations

import html
from typing import Any

from puzzcombinator.artifacts.registry import register_artifact
from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.rendering.fragment import Artifact, Audience, RenderFragment

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
    """A Caesar-shifted message. Shows the ciphertext alone for players; with the
    shift and decoded solution when ``solution`` is present (the game-master view)."""

    type_name = "caesar_cipher"

    def __init__(
        self,
        ciphertext: str,
        *,
        shift: int | None = None,
        solution: str | None = None,
        name: str = "cipher",
        audience: Audience = Audience.PLAYER,
        id: str | None = None,
    ) -> None:
        super().__init__(name=name, audience=audience, id=id)
        self.ciphertext = ciphertext
        self.shift = shift
        self.solution = solution

    def to_payload(self) -> dict[str, Any]:
        return {"ciphertext": self.ciphertext, "shift": self.shift, "solution": self.solution}

    @classmethod
    def from_payload(
        cls, *, name: str, audience: Audience, id: str, payload: dict[str, Any]
    ) -> CipherArtifact:
        return cls(
            payload["ciphertext"],
            shift=payload.get("shift"),
            solution=payload.get("solution"),
            name=name,
            audience=audience,
            id=id,
        )

    def render(self) -> RenderFragment:
        if self.solution is None:
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

    def _artifacts(self, audience: Audience) -> list[Artifact]:
        if audience is Audience.GAME_MASTER:
            return [
                CipherArtifact(
                    self.ciphertext,
                    shift=self.shift,
                    solution=self.solution,
                    name="cipher",
                    audience=audience,
                    id=self.artifact_id("cipher"),
                )
            ]
        return [
            CipherArtifact(
                self.ciphertext, name="cipher", audience=audience, id=self.artifact_id("cipher")
            )
        ]
