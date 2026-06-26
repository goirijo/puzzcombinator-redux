// The workspace channel — the TypeScript echo of the Python `visualization` layer. This is
// the editor's UI state: which views (buffers) exist, which tabs (windows) are open, and
// where nodes are drawn. Self-contained — it references nodes by opaque id only and never
// touches the hunt-data types. Lose it and you lose only how things are drawn, not the hunt.
//
// Unlike a node (whose in-memory shape React Flow forces into `HuntFlowNode`, see flow.ts),
// the workspace has no such forcing function — so the editor holds this DTO shape *directly*
// (in the workspace store), with no separate camelCased view-model. The price is snake_case
// field access (`active_tab`, `tab.view`), which is fine.

/** A node's pixel position within a view. */
export interface PositionDTO {
  x: number
  y: number
}

/** A view's pan/zoom framing of its graph (React Flow's viewport). */
export interface ViewportDTO {
  x: number
  y: number
  zoom: number
}

/** React Flow's identity viewport — a view still at this is treated as "auto-fit me". */
export const IDENTITY_VIEWPORT: ViewportDTO = { x: 0, y: 0, zoom: 1 }

/** True when a view has never been framed (still at the identity viewport). */
export function isIdentityViewport(vp: ViewportDTO): boolean {
  return vp.x === 0 && vp.y === 0 && vp.zoom === 1
}

/**
 * A view (a *buffer*): an arrangement of one graph — node positions, a title, and the saved
 * pan/zoom framing (so two views of one graph can each remember their own camera).
 */
export interface ViewDTO {
  graph: string
  title: string
  positions: Record<string, PositionDTO>
  viewport: ViewportDTO
}

/** A tab (a *window*): a display slot referencing a view by id. */
export interface TabDTO {
  id: string
  view: string
}

/**
 * The whole UI channel: every view (keyed by id), every tab, and the active tab.
 *
 * Vim model: a *view* (`ViewDTO`) is a buffer — an arrangement of one graph; a *tab*
 * (`TabDTO`) is a window showing a view. Several tabs may show one view. This is the shape
 * the workspace store holds directly.
 */
export interface WorkspaceDTO {
  views: Record<string, ViewDTO>
  tabs: TabDTO[]
  active_tab: string | null
}

/**
 * The view the active tab is showing, with its id — or `undefined` before load, when no tab
 * is active, or when the active tab points at a missing view. Pure query over the workspace.
 */
export function activeView(ws: WorkspaceDTO): { id: string; view: ViewDTO } | undefined {
  const tab = activeTab(ws)
  if (!tab) return undefined
  const view = ws.views[tab.view]
  return view ? { id: tab.view, view } : undefined
}

// --- Mutations (pure: workspace in, new workspace out) ------------------------------------
// Every view-state change goes through one of these, so the panel/orchestrator never
// hand-mutate the DTO. They are the CRUD seam — rename/delete slot in here later the same way.

/** The tab the workspace currently shows — or `undefined` when none is active. Pure query. */
export function activeTab(ws: WorkspaceDTO): TabDTO | undefined {
  return ws.tabs.find((t) => t.id === ws.active_tab)
}

/** Point the active tab at a different view. Immutable; a no-op when no tab is active. */
export function setActiveTabView(ws: WorkspaceDTO, viewId: string): WorkspaceDTO {
  return {
    ...ws,
    tabs: ws.tabs.map((t) => (t.id === ws.active_tab ? { ...t, view: viewId } : t)),
  }
}

/**
 * Add a view and return the new workspace plus the freshly generated view id. It does **not**
 * switch any tab to the new view — selecting is the orchestrator's call, so "create then land
 * on it" stays two explicit steps. The id is random so views never collide.
 */
export function createView(
  ws: WorkspaceDTO,
  view: ViewDTO,
): { workspace: WorkspaceDTO; viewId: string } {
  const viewId = `view-${crypto.randomUUID().slice(0, 8)}`
  return { workspace: { ...ws, views: { ...ws.views, [viewId]: view } }, viewId }
}

/** Retitle a view. Immutable; a no-op when the view does not exist. */
export function renameView(ws: WorkspaceDTO, viewId: string, title: string): WorkspaceDTO {
  const view = ws.views[viewId]
  if (!view) return ws
  return { ...ws, views: { ...ws.views, [viewId]: { ...view, title } } }
}

/**
 * Remove a view, repointing any tab that showed it at a surviving view so no tab is left
 * dangling. Refuses to delete the last view — a workspace needs at least one — and is a no-op
 * for a missing id; both cases return the input unchanged (referentially), which the store
 * uses to detect "nothing happened".
 */
export function deleteView(ws: WorkspaceDTO, viewId: string): WorkspaceDTO {
  if (!ws.views[viewId]) return ws
  const survivors = Object.keys(ws.views).filter((id) => id !== viewId)
  if (survivors.length === 0) return ws // never delete the last view
  const fallback = survivors[0]
  const views = { ...ws.views }
  delete views[viewId]
  return {
    ...ws,
    views,
    tabs: ws.tabs.map((t) => (t.view === viewId ? { ...t, view: fallback } : t)),
  }
}
