"""Puzzle-level demo: a cipher's artifacts, with no graph and no binder.

Run it:

    python examples/puzzles/cipher_artifacts_demo.py

This works *below* the graph layer. It never touches GraphBuilder, edges, or the
binder — it just exercises the Puzzle -> Artifact -> RenderFragment chain directly:

    1. build a CaesarCipherPuzzle from plaintext,
    2. collect every artifact it can emit (the player set and the game-master set),
    3. render each one and print its markup.

The player artifact carries only the ciphertext; the game-master artifact carries
the decoded answer. They are separate instances, so render() takes no audience —
each artifact just draws the data it was given.
"""

from __future__ import annotations

from puzzcombinator import Audience, CaesarCipherPuzzle


def main() -> None:
    # 1. Create the puzzle from plaintext (this encodes the prompt into ciphertext).
    puzzle = CaesarCipherPuzzle.from_plaintext(plaintext="FOUNTAIN", shift=3, id="c1")

    # 2. Collect every available artifact: artifacts(audience=...) returns a
    #    {name: Artifact} map, so flatten both audiences' maps into one list.
    every_artifact = [
        artifact
        for audience in (Audience.PLAYER, Audience.GAME_MASTER)
        for artifact in puzzle.artifacts(audience=audience).values()
    ]

    # 3. Render each artifact and print it. render() takes no audience — the
    #    artifact renders whatever data it holds (player: ciphertext only;
    #    game master: the decoded answer).
    for artifact in every_artifact:
        fragment = artifact.render()
        label = f"{artifact.id}  ({artifact.name}, {artifact.audience.value}, {fragment.kind})"
        print(f"--- {label} ---")
        print(fragment.markup)
        if fragment.styles:
            print(f"# styles: {fragment.styles.strip()}")
        print()


if __name__ == "__main__":
    main()
