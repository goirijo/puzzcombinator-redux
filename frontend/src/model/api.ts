// The seam over HTTP — the frontend analog of the Python `app` layer. It both *transports*
// (the two fetch calls) and *composes*: the two channels (graph + workspace) each have their
// own module (graph.ts / workspace.ts), and here we fuse them on load and split them on save,
// using the `flow.ts` projection. The wire carries both channels as explicit siblings, never
// mixed — losing `workspace` loses only how things are drawn, never the hunt.

import type { GraphBlockDTO } from './graph'
import {
  toFlowEdges,
  toFlowNodes,
  toGraphBlock,
  toPositions,
  type HuntFlowEdge,
  type HuntFlowNode,
} from './flow'
import { activeView, type WorkspaceDTO } from './workspace'

/** The full `GET /api/graph` envelope: the two channels as explicit siblings. */
export interface GraphResponseDTO {
  schema_version: string
  graph: GraphBlockDTO
  workspace: WorkspaceDTO
}

/** The `PUT /api/graph` body: both channels back, the way the backend composes them. */
export interface SaveRequestDTO {
  graph: GraphBlockDTO
  workspace: WorkspaceDTO
}

/** Fetch the drawn graph + the workspace from the backend. */
export async function fetchGraph(): Promise<GraphResponseDTO> {
  const res = await fetch('/api/graph')
  if (!res.ok) throw new Error(`GET /api/graph failed: ${res.status}`)
  return res.json() as Promise<GraphResponseDTO>
}

/**
 * Persist both channels: `PUT /api/graph` with `{ graph, workspace }`. The backend returns
 * **409 in demo mode** (no `PUZZ_GRAPH` file to write to) and **422** on an invalid body —
 * we surface that detail rather than swallow it, so the UI can show why a save didn't take.
 */
export async function saveGraph(body: SaveRequestDTO): Promise<void> {
  const res = await fetch('/api/graph', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res
      .json()
      .then((b: { detail?: string }) => b.detail)
      .catch(() => undefined)
    throw new Error(detail ?? `PUT /api/graph failed: ${res.status}`)
  }
}

// --- Composition: fuse the two channels on load, split them on save. ---------------------
// Pure (no fetch/state), so they're unit-testable. The load↔save pair is symmetric: load
// projects the active view's positions onto the nodes; save reads them back off.

/** Load: project the response's active-view positions onto React Flow nodes. */
export function toFlowGraph(res: GraphResponseDTO): {
  nodes: HuntFlowNode[]
  edges: HuntFlowEdge[]
} {
  const active = activeView(res.workspace)
  return {
    nodes: toFlowNodes(res.graph.nodes, active?.view.positions ?? {}),
    edges: toFlowEdges(res.graph.edges),
  }
}

/**
 * Save: split the live editor state back into the two channels. The graph block comes from
 * the nodes/edges (positions dropped); the active view's positions are refreshed from those
 * same nodes (positions ride the graph store during editing — this is the split-at-save step).
 */
export function buildSaveRequest(
  nodes: HuntFlowNode[],
  edges: HuntFlowEdge[],
  workspace: WorkspaceDTO,
): SaveRequestDTO {
  const active = activeView(workspace)
  const views = active
    ? { ...workspace.views, [active.id]: { ...active.view, positions: toPositions(nodes) } }
    : workspace.views
  return { graph: toGraphBlock(nodes, edges), workspace: { ...workspace, views } }
}
