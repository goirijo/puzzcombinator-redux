// The seam over HTTP — the frontend analog of the Python `app` layer. It both *transports*
// (the two fetch calls) and *composes*: the two channels (graph + workspace) each have their
// own module (graph.ts / workspace.ts), and here we fuse them on load and split them on save,
// using the `flow.ts` projection. The wire carries both channels as explicit siblings, never
// mixed — losing `workspace` loses only how things are drawn, never the hunt.

import type { ArtifactDTO, GraphBlockDTO } from './graph'
import {
  toFlowEdges,
  toFlowNodes,
  toGraphBlock,
  toPositions,
  type HuntFlowEdge,
  type HuntFlowNode,
} from './flow'
import { activeView, type PositionDTO, type WorkspaceDTO } from './workspace'

/** The auto-arrange orientations the backend accepts (echoes its `Orientation` Literal). */
export type Orientation = 'horizontal' | 'vertical'

/** The full `GET /api/graph` envelope: the two channels as explicit siblings.
 *
 * `unplaced` is the drawn graph's *loose-artifact pool* — created-but-not-yet-placed
 * artifacts. It's hunt data (it rides the graph channel, not the workspace), carried as a
 * flat list because the API is single-graph. The editor doesn't render it yet; it's threaded
 * through load→save so a save can't wipe a pool stored in the file. */
export interface GraphResponseDTO {
  schema_version: string
  graph: GraphBlockDTO
  unplaced: ArtifactDTO[]
  workspace: WorkspaceDTO
}

/** The `PUT /api/graph` body: both channels back, the way the backend composes them. */
export interface SaveRequestDTO {
  graph: GraphBlockDTO
  unplaced: ArtifactDTO[]
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

/**
 * Auto-layout the live graph: `POST /api/arrange` with the current `{ nodes, edges }` and an
 * orientation, returning a `{node_id: {x, y}}` positions map shaped exactly like a view's
 * `positions` (apply it straight onto the nodes). The graph travels in the request because the
 * editor's copy may be unsaved; layout itself is the backend's single source of truth. Surfaces
 * the server's 422 detail (e.g. a cycle) the same way `saveGraph` does.
 */
export async function requestArrange(
  graph: GraphBlockDTO,
  orientation: Orientation,
): Promise<Record<string, PositionDTO>> {
  const res = await fetch('/api/arrange', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ graph, orientation }),
  })
  if (!res.ok) {
    const detail = await res
      .json()
      .then((b: { detail?: string }) => b.detail)
      .catch(() => undefined)
    throw new Error(detail ?? `POST /api/arrange failed: ${res.status}`)
  }
  const body = (await res.json()) as { positions: Record<string, PositionDTO> }
  return body.positions
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
  unplaced: ArtifactDTO[],
  workspace: WorkspaceDTO,
): SaveRequestDTO {
  const active = activeView(workspace)
  const views = active
    ? { ...workspace.views, [active.id]: { ...active.view, positions: toPositions(nodes) } }
    : workspace.views
  // `unplaced` passes through unchanged — the editor doesn't edit the pool yet, but sending it
  // back keeps a save from dropping artifacts the file already holds.
  return { graph: toGraphBlock(nodes, edges), unplaced, workspace: { ...workspace, views } }
}
