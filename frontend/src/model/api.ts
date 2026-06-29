// The seam over HTTP — the frontend analog of the Python `app` layer. It both *transports*
// (the two fetch calls) and *composes*: the two channels (graph + workspace) each have their
// own module (graph.ts / workspace.ts), and here we fuse them on load and split them on save,
// using the `flow.ts` projection. The wire carries both channels as explicit siblings, never
// mixed — losing `workspace` loses only how things are drawn, never the hunt.

import type { ArtifactDTO, GraphBlockDTO } from './graph'
import {
  toFlowArtifacts,
  toFlowEdges,
  toFlowNodes,
  toGraphBlock,
  toPool,
  toPositions,
  type CanvasGraph,
  type CanvasNode,
  type HuntFlowEdge,
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

/** Throw with the backend's `detail` (the way the save/arrange calls do), for a failed POST. */
async function failWithDetail(res: Response, endpoint: string): Promise<never> {
  const detail = await res
    .json()
    .then((b: { detail?: string }) => b.detail)
    .catch(() => undefined)
  throw new Error(detail ?? `POST ${endpoint} failed: ${res.status}`)
}

/** POST a `{ path, ...extra }` body to a document endpoint, surfacing the server detail. */
async function postDocument(endpoint: string, body: Record<string, unknown>): Promise<void> {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) await failWithDetail(res, endpoint)
}

/**
 * Start a fresh empty document at `path` and switch the backend onto it (`POST
 * /api/document/new`). The backend refuses (409) if the file already exists — use
 * {@link openDocument} for existing files. The caller reloads the page on success so the
 * mount-load reseeds every store from the now-active document.
 */
export async function newDocument(path: string): Promise<void> {
  await postDocument('/api/document/new', { path })
}

/**
 * Switch the backend onto the existing document at `path` (`POST /api/document/open`),
 * dropping the current one. The backend validates the file first (404 missing, 422
 * unparseable). The caller reloads the page on success to draw the newly-active document.
 */
export async function openDocument(path: string): Promise<void> {
  await postDocument('/api/document/open', { path })
}

/**
 * Save the *current* graph to a new file at `path` and switch the backend onto it (`POST
 * /api/document/save-as`) — the "name this untitled document" action. Sends the live save
 * body alongside the path; the backend refuses (409) if the file already exists, like New.
 * The caller reloads the page on success: the work is already on disk, so the mount-load
 * reseeds from the now-saved, now-active document with a clean (not-dirty) state.
 */
export async function saveDocumentAs(path: string, body: SaveRequestDTO): Promise<void> {
  await postDocument('/api/document/save-as', { path, ...body })
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

// --- Composition: fuse the channels on load, split them on save. -------------------------
// Pure (no fetch/state), so they're unit-testable. The load↔save pair is symmetric: load
// fuses graph nodes + the loose-artifact pool into one canvas array and projects the active
// view's positions onto all of them; save reads positions back off and partitions the array
// back into the graph block and the pool.

/** Load: fuse hunt nodes + pooled artifacts into one canvas array, with active-view positions. */
export function toFlowGraph(res: GraphResponseDTO): CanvasGraph {
  const active = activeView(res.workspace)
  const positions = active?.view.positions ?? {}
  return {
    nodes: [...toFlowNodes(res.graph.nodes, positions), ...toFlowArtifacts(res.unplaced, positions)],
    edges: toFlowEdges(res.graph.edges),
  }
}

/**
 * Save: split the live canvas back into its channels. The graph block comes from the hunt
 * nodes + edges (positions dropped, loose artifacts filtered out); the pool comes from the
 * loose-artifact nodes; the active view's positions are refreshed from *all* nodes (positions
 * ride the graph store during editing — this is the split-at-save step).
 */
export function buildSaveRequest(
  nodes: CanvasNode[],
  edges: HuntFlowEdge[],
  workspace: WorkspaceDTO,
): SaveRequestDTO {
  const active = activeView(workspace)
  const views = active
    ? { ...workspace.views, [active.id]: { ...active.view, positions: toPositions(nodes) } }
    : workspace.views
  return { graph: toGraphBlock(nodes, edges), unplaced: toPool(nodes), workspace: { ...workspace, views } }
}
