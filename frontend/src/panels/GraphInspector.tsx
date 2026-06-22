// The GRAPH command's panel: inspect and edit whatever is selected on the canvas. Three
// parts, per the design (frontend/design/ideas.txt): the SELECTED item, then its RELATED
// items. For a node the related items are its incoming/outgoing edges and the artifacts on
// them — the client mirror of the Python `required_inputs` / `produced_outputs`, derived
// here straight from the edge list. A pure view over `PanelProps`: it reads selection +
// graph and calls back; it owns no state.

import type { HuntFlowEdge } from '../model/flow'
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

export function GraphInspector({ nodes, edges, selection, updateNode }: PanelProps) {
  if (!selection) {
    return <p className="inspector__empty">Select a node on the canvas to edit it.</p>
  }

  if (selection.kind === 'edge') {
    const edge = edges.find((e) => e.id === selection.id)
    if (!edge) return <p className="inspector__empty">Edge not found.</p>
    return (
      <div className="inspector">
        <section className="inspector__selected">
          <h3 className="inspector__heading">Edge</h3>
          <p className="inspector__edge-ends">
            {edge.source} → {edge.target}
          </p>
          <ul className="related__artifacts">
            {(edge.data?.content ?? []).map((a) => (
              <li key={a.id}>
                {a.name} <span className="related__type">{a.type}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    )
  }

  const node = nodes.find((n) => n.id === selection.id)
  if (!node) return <p className="inspector__empty">Node not found.</p>

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

      <section className="inspector__related">
        <h4 className="inspector__heading">Incoming ({incoming.length})</h4>
        {incoming.length === 0 ? (
          <p className="inspector__none">none</p>
        ) : (
          <ul className="related">
            {incoming.map((e) => (
              <RelatedEdge key={e.id} otherId={e.source} edge={e} />
            ))}
          </ul>
        )}
      </section>

      <section className="inspector__related">
        <h4 className="inspector__heading">Outgoing ({outgoing.length})</h4>
        {outgoing.length === 0 ? (
          <p className="inspector__none">none</p>
        ) : (
          <ul className="related">
            {outgoing.map((e) => (
              <RelatedEdge key={e.id} otherId={e.target} edge={e} />
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
