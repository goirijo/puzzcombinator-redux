// The seam: types mirroring what `GET /api/graph` returns, plus the one fetch call.
// This is the TypeScript echo of the Python serialization layer — the single place
// the shape of the backend response is written down. Everything else works off these
// types, so the compiler tells us if the seam and the UI drift apart.

/** One artifact riding an edge (the serialized `{type, id, name, payload}` envelope). */
export interface ArtifactDTO {
  type: string
  id: string
  name: string
  payload: Record<string, unknown>
}

export interface NodeDTO {
  id: string
  // The backend's Node fields default to None, so the wire value can be null for a node
  // with no action/label/notes. `toFlow` coalesces these to '' for the editor; `fromFlow`
  // maps '' back to null on save (see adapt.ts).
  action: string | null
  label: string | null
  notes: string | null
}

export interface EdgeDTO {
  id: string
  source: string
  target: string
  content: ArtifactDTO[]
}

/** A node's server-computed position (from `layered_layout`). */
export interface NodePositionDTO {
  layer: number
  row: number
  x: number
  y: number
}

/** The full `GET /api/graph` envelope: the graph block + the layout map. */
export interface GraphResponseDTO {
  schema_version: string
  graph: {
    nodes: NodeDTO[]
    edges: EdgeDTO[]
  }
  layout: Record<string, NodePositionDTO>
}

/** Fetch the drawn graph + its layout from the backend. */
export async function fetchGraph(): Promise<GraphResponseDTO> {
  const res = await fetch('/api/graph')
  if (!res.ok) throw new Error(`GET /api/graph failed: ${res.status}`)
  return res.json() as Promise<GraphResponseDTO>
}

/**
 * Persist an edited graph: `PUT /api/graph` with the bare `{nodes, edges}` block (the
 * server wraps it in the schema envelope). The backend returns **409 in demo mode** (no
 * `PUZZ_GRAPH` file to write to) and **422** on an invalid graph — we surface that detail
 * rather than swallow it, so the UI can show why a save didn't take.
 */
export async function saveGraph(graph: GraphResponseDTO['graph']): Promise<void> {
  const res = await fetch('/api/graph', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(graph),
  })
  if (!res.ok) {
    const detail = await res
      .json()
      .then((b: { detail?: string }) => b.detail)
      .catch(() => undefined)
    throw new Error(detail ?? `PUT /api/graph failed: ${res.status}`)
  }
}
