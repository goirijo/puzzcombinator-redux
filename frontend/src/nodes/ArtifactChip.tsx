// The visual for a single artifact: a warm dashed card with its type tag + name. Extracted
// from LooseArtifactNode so the same look serves both the loose-artifact canvas node AND the
// edge "explode" grid (edges/FloatingEdge) — one place owns the artifact's on-canvas identity.
// Type-agnostic: it shows ONLY what every artifact has (its type and name), never the
// type-specific `payload`, so one chip works for every artifact kind. Purely presentational;
// all colors/sizes come from theme.css.

import type { ArtifactDTO } from '../model/graph'

export function ArtifactChip({ artifact }: { artifact: ArtifactDTO }) {
  return (
    <div className="artifact-node">
      <span className="artifact-node__tag">{artifact.type}</span>
      <div className="artifact-node__body">{artifact.name}</div>
    </div>
  )
}
