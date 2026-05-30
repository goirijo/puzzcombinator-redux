"""The first concrete puzzle: a Caesar cipher.

A zero-dependency vertical slice that exercises the whole abstraction: it can
*generate* the encoded prompt from plaintext and *validate* the player's decode,
and it renders both a player fragment (the ciphertext to solve) and a
game-master fragment (the solution).
"""

from __future__ import annotations

import html
from collections.abc import Iterable
from typing import Any

from puzzcombinator.puzzles.base import Puzzle
from puzzcombinator.puzzles.registry import register_puzzle
from puzzcombinator.rendering.fragment import Audience, RenderFragment
from puzzcombinator.validation.base import Validator
from puzzcombinator.validation.builtins import NormalizedText


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
    """Decode a Caesar-shifted message."""

    type_name = "caesar_cipher"

    def __init__(
        self,
        id: str,
        *,
        shift: int,
        ciphertext: str,
        validators: Iterable[Validator],
        require_all: bool = False,
    ) -> None:
        super().__init__(id, validators, require_all)
        self.shift = shift % 26
        self.ciphertext = ciphertext

    @classmethod
    def from_plaintext(
        cls,
        id: str,
        plaintext: str,
        shift: int,
        *,
        validator: Validator | None = None,
    ) -> CaesarCipherPuzzle:
        """Author a puzzle from plaintext: encodes the prompt and wires a validator."""
        ciphertext = _caesar(plaintext, shift)
        chosen = validator if validator is not None else NormalizedText(answer=plaintext)
        return cls(id, shift=shift % 26, ciphertext=ciphertext, validators=[chosen])

    def to_payload(self) -> dict[str, Any]:
        return {"shift": self.shift, "ciphertext": self.ciphertext}

    @classmethod
    def from_payload(
        cls,
        id: str,
        payload: dict[str, Any],
        validators: list[Validator],
        require_all: bool = False,
    ) -> CaesarCipherPuzzle:
        return cls(
            id,
            shift=payload["shift"],
            ciphertext=payload["ciphertext"],
            validators=validators,
            require_all=require_all,
        )

    def render(self, audience: Audience) -> RenderFragment:
        if audience is Audience.PLAYER:
            return RenderFragment.html(
                f'<section class="puzzle cipher" data-id="{html.escape(self.id)}">'
                f"<h3>Cipher</h3>"
                f"<p>Decode this message:</p>"
                f'<pre class="ciphertext">{html.escape(self.ciphertext)}</pre>'
                f"</section>"
            )
        decoded = _caesar(self.ciphertext, -self.shift)
        return RenderFragment.html(
            f'<section class="answer cipher" data-id="{html.escape(self.id)}">'
            f"<p>Caesar shift {self.shift} &rarr; "
            f"<strong>{html.escape(decoded)}</strong></p>"
            f"</section>"
        )
