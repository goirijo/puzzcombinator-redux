"""The first concrete puzzle: a Caesar cipher.

A zero-dependency vertical slice that exercises the whole abstraction: the
designer authors it from plaintext (which encodes the prompt), it renders the
ciphertext for players and the decoded solution for the game master, and it
serializes round-trip. Its solution is *derivable* by decoding, so there's no
separate answer to store or check.
"""

from __future__ import annotations

import html
from typing import Any

from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.registry import register_puzzle
from puzzcombinator.rendering.fragment import Audience, RenderFragment

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


@register_puzzle
class CaesarCipherPuzzle(Puzzle):
    """A Caesar-shifted message for players to decode."""

    type_name = "caesar_cipher"

    def __init__(self, id: str, *, shift: int, ciphertext: str) -> None:
        super().__init__(id)
        self.shift = shift % 26
        self.ciphertext = ciphertext

    @classmethod
    def from_plaintext(cls, id: str, plaintext: str, shift: int) -> CaesarCipherPuzzle:
        """Author a puzzle from plaintext by encoding the prompt the player sees."""
        return cls(id, shift=shift % 26, ciphertext=_caesar(plaintext, shift))

    @property
    def solution(self) -> str:
        """The decoded message — shown in the game-master answer key."""
        return _caesar(self.ciphertext, -self.shift)

    def to_payload(self) -> dict[str, Any]:
        return {"shift": self.shift, "ciphertext": self.ciphertext}

    @classmethod
    def from_payload(cls, id: str, payload: dict[str, Any]) -> CaesarCipherPuzzle:
        return cls(id, shift=payload["shift"], ciphertext=payload["ciphertext"])

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
