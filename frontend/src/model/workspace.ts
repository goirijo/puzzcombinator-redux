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

/** A tab's pan/zoom framing of its view (React Flow's viewport). */
export interface ViewportDTO {
  x: number
  y: number
  zoom: number
}

/** A view (a *buffer*): an arrangement of one graph — its node positions and a title. */
export interface ViewDTO {
  graph: string
  title: string
  positions: Record<string, PositionDTO>
}

/** A tab (a *window*): a display slot referencing a view by id, with its own viewport. */
export interface TabDTO {
  id: string
  view: string
  viewport: ViewportDTO
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
  const tab = ws.tabs.find((t) => t.id === ws.active_tab)
  if (!tab) return undefined
  const view = ws.views[tab.view]
  return view ? { id: tab.view, view } : undefined
}
