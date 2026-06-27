// The GRAPH command's panel: inspect and edit whatever is selected on the canvas. Three
// parts, per the design (frontend/design/ideas.txt): the SELECTED item, then its RELATED
// items. For a node the related items are its incoming/outgoing edges and the artifacts on
// them — the client mirror of the Python `required_inputs` / `produced_outputs`, derived
// here straight from the edge list. It subscribes to the stores it needs (the graph store for
// nodes/edges + the mutating actions, the selection store for what's selected) and takes no
// props; it owns no state of its own.

import { toPool, type HuntFlowEdge, type HuntFlowNode } from '../model/flow'
import { shortId } from '../nodes/shortId'
import { useGraphStore } from '../shell/graphStore'
import { useSelectionStore } from '../shell/selectionStore'

/** One related edge: the node on its other end (by display name) plus the artifacts riding it. */
function RelatedEdge({ otherLabel, edge }: { otherLabel: string; edge: HuntFlowEdge }) {
  const artifacts = edge.data?.content ?? []
  return (
    <li className="related__edge">
      <span className="related__node">{otherLabel}</span>
      {artifacts.length > 0 && (
        <ul className="related__artifacts">
          {artifacts.map((a) => (
            <li key={a.id}>
              {a.name} <span className="related__type">{a.type}</span>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

/** A node's incoming or outgoing edges as a titled list. `edgeToOtherLabel` resolves the
 *  *far*-end node's display name (its source for incoming, its target for outgoing). */
function RelatedEdgeList({
  label,
  edges,
  edgeToOtherLabel,
}: {
  label: string
  edges: HuntFlowEdge[]
  edgeToOtherLabel: (edge: HuntFlowEdge) => string
}) {
  return (
    <section className="inspector__related">
      <h4 className="inspector__heading">
        {label} ({edges.length})
      </h4>
      {edges.length === 0 ? (
        <p className="inspector__none">none</p>
      ) : (
        <ul className="related">
          {edges.map((e) => (
            <RelatedEdge key={e.id} otherLabel={edgeToOtherLabel(e)} edge={e} />
          ))}
        </ul>
      )}
    </section>
  )
}

/** One artifact with a single action button — detach it from an edge, or place it onto one. */
function ArtifactRow({
  name,
  type,
  actionLabel,
  onAction,
}: {
  name: string
  type: string
  actionLabel: string
  onAction: () => void
}) {
  return (
    <li className="inspector__artifact-row">
      <span>
        {name} <span className="related__type">{type}</span>
      </span>
      <button type="button" className="ghost-btn" onClick={onAction}>
        {actionLabel}
      </button>
    </li>
  )
}

export function GraphInspector() {
  const nodes = useGraphStore((s) => s.nodes)
  const edges = useGraphStore((s) => s.edges)
  const updateNode = useGraphStore((s) => s.updateNode)
  const placeArtifactOnEdge = useGraphStore((s) => s.placeArtifactOnEdge)
  const detachArtifact = useGraphStore((s) => s.detachArtifact)
  const selection = useSelectionStore((s) => s.selection)

  // How an edge endpoint reads in the inspector: the node's label, or its short-id stub when
  // unlabelled — exactly what the canvas draws on the node. Ids are internal; we don't surface
  // the full one here (debugging affordances can come back later if we need them).
  const nodeName = (id: string) => {
    const n = nodes.find((node): node is HuntFlowNode => node.id === id && node.type === 'hunt')
    return n?.data.label || shortId(id)
  }

  if (!selection) {
    return <p className="inspector__empty">Select a node on the canvas to edit it.</p>
  }

  if (selection.kind === 'edge') {
    const edge = edges.find((e) => e.id === selection.id)
    if (!edge) return <p className="inspector__empty">Edge not found.</p>
    const onEdge = edge.data?.content ?? []
    // Every loose artifact not yet placed; placing one moves it from the pool onto this edge.
    const pool = toPool(nodes)
    return (
      <div className="inspector">
        <section className="inspector__selected">
          <h3 className="inspector__heading">Edge</h3>
          <p className="inspector__edge-ends">
            {nodeName(edge.source)} → {nodeName(edge.target)}
          </p>
        </section>

        <section className="inspector__related">
          <h4 className="inspector__heading">On this edge ({onEdge.length})</h4>
          {onEdge.length === 0 ? (
            <p className="inspector__none">none</p>
          ) : (
            <ul className="related__artifacts">
              {onEdge.map((a) => (
                <ArtifactRow
                  key={a.id}
                  name={a.name}
                  type={a.type}
                  actionLabel="Detach"
                  onAction={() => detachArtifact(edge.id, a.id)}
                />
              ))}
            </ul>
          )}
        </section>

        <section className="inspector__related">
          <h4 className="inspector__heading">Place from pool ({pool.length})</h4>
          {pool.length === 0 ? (
            <p className="inspector__none">none</p>
          ) : (
            <ul className="related__artifacts">
              {pool.map((a) => (
                <ArtifactRow
                  key={a.id}
                  name={a.name}
                  type={a.type}
                  actionLabel="Place"
                  onAction={() => placeArtifactOnEdge(a.id, edge.id)}
                />
              ))}
            </ul>
          )}
        </section>
      </div>
    )
  }

  // The selection may be a loose-artifact node (it shares the canvas); this panel only edits
  // hunt nodes, so narrow to those. A selected artifact has no editor here yet.
  const node = nodes.find((n) => n.id === selection.id && n.type === 'hunt')
  if (!node) return <p className="inspector__empty">No editable node selected.</p>

  const incoming = edges.filter((e) => e.target === node.id)
  const outgoing = edges.filter((e) => e.source === node.id)

  return (
    <div className="inspector">
      <section className="inspector__selected">
        <h3 className="inspector__heading">Node</h3>
        <label className="field">
          <span className="field__label">Label</span>
          <input
            className="field__input"
            value={node.data.label}
            onChange={(e) => updateNode(node.id, { label: e.target.value })}
          />
        </label>
        <label className="field">
          <span className="field__label">Action</span>
          <input
            className="field__input"
            value={node.data.action}
            onChange={(e) => updateNode(node.id, { action: e.target.value })}
          />
        </label>
        <label className="field">
          <span className="field__label">Notes</span>
          <textarea
            className="field__input field__input--area"
            value={node.data.notes}
            onChange={(e) => updateNode(node.id, { notes: e.target.value })}
          />
        </label>
      </section>

      <RelatedEdgeList label="Incoming" edges={incoming} edgeToOtherLabel={(e) => nodeName(e.source)} />
      <RelatedEdgeList label="Outgoing" edges={outgoing} edgeToOtherLabel={(e) => nodeName(e.target)} />
    </div>
  )
}
