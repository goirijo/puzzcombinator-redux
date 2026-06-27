// The GRAPH command's panel: inspect and edit whatever is selected on the canvas. Three
// parts, per the design (frontend/design/ideas.txt): the SELECTED item, then its RELATED
// items. For a node the related items are its incoming/outgoing edges and the artifacts on
// them — the client mirror of the Python `required_inputs` / `produced_outputs`, derived
// here straight from the edge list. A pure view over `PanelProps`: it reads selection +
// graph and calls back; it owns no state.

import { toPool, type HuntFlowEdge } from '../model/flow'
import type { PanelProps } from '../shell/types'

/** One related edge: the node on its other end plus the artifacts riding it. */
function RelatedEdge({ otherId, edge }: { otherId: string; edge: HuntFlowEdge }) {
  const artifacts = edge.data?.content ?? []
  return (
    <li className="related__edge">
      <span className="related__node">{otherId}</span>
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

/** A node's incoming or outgoing edges as a titled list. `edgeToOtherId` picks the node at
 *  the *far* end of each edge (its source for incoming, its target for outgoing). */
function RelatedEdgeList({
  label,
  edges,
  edgeToOtherId,
}: {
  label: string
  edges: HuntFlowEdge[]
  edgeToOtherId: (edge: HuntFlowEdge) => string
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
            <RelatedEdge key={e.id} otherId={edgeToOtherId(e)} edge={e} />
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

export function GraphInspector({
  nodes,
  edges,
  selection,
  updateNode,
  placeArtifactOnEdge,
  detachArtifact,
}: PanelProps) {
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
            {edge.source} → {edge.target}
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

      <RelatedEdgeList label="Incoming" edges={incoming} edgeToOtherId={(e) => e.source} />
      <RelatedEdgeList label="Outgoing" edges={outgoing} edgeToOtherId={(e) => e.target} />
    </div>
  )
}
