// A SCRATCH-panel section: drop a pre-baked loose artifact onto the canvas (it joins the
// graph's unplaced pool, so it shows in every view). Like NodeCreateSection it subscribes to
// the graph store's action directly and takes no props, so it lifts out cleanly later. One
// button, pre-baked text artifact — clunky on purpose for now.

import { useGraphStore } from '../../shell/graphStore'

export function ArtifactCreateSection() {
  const createLooseArtifact = useGraphStore((s) => s.createLooseArtifact)
  return (
    <section className="view-panel__section">
      <h3 className="inspector__heading">Artifacts</h3>
      <button type="button" className="ghost-btn view-panel__action" onClick={createLooseArtifact}>
        + Create loose artifact
      </button>
    </section>
  )
}
