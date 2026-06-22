// The hunt-data channel's wire types — the TypeScript echo of the Python `serialization`
// layer. This is the treasure hunt's source of truth (nodes, edges, artifacts); it knows
// nothing about *drawing* — positions and views live in the workspace channel
// (`workspace.ts`), exactly as the backend keeps `serialization` and `visualization` apart.

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
  // with no action/label/notes. The flow projection (`flow.ts`) coalesces these to '' for
  // the editor and maps '' back to null on save.
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

/** One graph's body: its nodes + edges (no positions — those are the workspace channel). */
export interface GraphBlockDTO {
  nodes: NodeDTO[]
  edges: EdgeDTO[]
}
