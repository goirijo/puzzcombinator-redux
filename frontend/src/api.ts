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
  action: string
  label: string
  notes: string
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
