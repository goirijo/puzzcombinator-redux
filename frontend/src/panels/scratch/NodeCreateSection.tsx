// A SCRATCH-panel section: create a blank loose node on the canvas. Like ViewPanel, it
// subscribes to the graph store's action directly and takes no props, so it lifts out cleanly
// into a real command later. One button, no options — clunky on purpose for now.

import { useGraphStore } from '../../shell/graphStore'

export function NodeCreateSection() {
  const createNode = useGraphStore((s) => s.createNode)
  return (
    <section className="view-panel__section">
      <h3 className="inspector__heading">Nodes</h3>
      <button type="button" className="ghost-btn view-panel__action" onClick={createNode}>
        + Create node
      </button>
    </section>
  )
}
