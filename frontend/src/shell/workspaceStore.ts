// The workspace store: the UI channel (views/tabs/active tab) as a Zustand store, mirroring
// graphStore.ts. It holds the `WorkspaceDTO` directly (so the pure helpers in model/workspace
// apply unchanged) plus the actions that switch and create views. Unlike the graph store it is
// NOT undoable — switching or creating a view is a UI navigation, not a hunt edit.
//
// The seam between the two stores: a node's *position* belongs to the workspace, but it rides
// the graph store's React Flow nodes while you drag (so React Flow can move it cheaply). So a
// view switch has to (1) flush the live drag positions back into the view you're leaving and
// (3) re-project the target view's stored positions onto the nodes — the latter WITHOUT
// recording an undo step. Those two hand-offs reach into the graph store via its vanilla
// `getState()` API; keeping them here means all the position-lifecycle logic lives in one place.

import { create } from 'zustand'

import { toPositions } from '../model/flow'
import {
  activeView,
  createView as addView,
  deleteView as removeView,
  IDENTITY_VIEWPORT,
  renameView as retitleView,
  setActiveTabView,
  type PositionDTO,
  type ViewportDTO,
  type WorkspaceDTO,
} from '../model/workspace'
import { useGraphStore } from './graphStore'

interface WorkspaceState {
  /** The whole UI channel, held as the DTO. `null` until the first load. */
  workspace: WorkspaceDTO | null
  /** Replace the workspace (initial load). */
  loadWorkspace: (workspace: WorkspaceDTO) => void
  /** Point the active tab at a different view (flushes drags, re-projects positions). */
  selectView: (viewId: string) => void
  /** Switch which tab is active (a tab carries its own view; same flush/re-project dance). */
  selectTab: (tabId: string) => void
  /** Create a view seeded from the current arrangement and land on it. */
  createView: () => void
  /** Retitle a view (metadata only — no canvas change, not undoable). */
  renameView: (viewId: string, title: string) => void
  /** Delete a view; if it was the one on screen, land the active tab on a survivor. */
  deleteView: (viewId: string) => void
  /** Record the current pan/zoom into the active view (the camera moved on the canvas). */
  setActiveViewport: (viewport: ViewportDTO) => void
}

/** Capture the live drag positions back into the view currently shown — before leaving it. */
function flushLivePositions(ws: WorkspaceDTO): WorkspaceDTO {
  const current = activeView(ws)
  if (!current) return ws
  const positions = toPositions(useGraphStore.getState().nodes)
  return { ...ws, views: { ...ws.views, [current.id]: { ...current.view, positions } } }
}

/** Drop a positions map onto the live nodes WITHOUT recording an undo step (a UI move). */
function reprojectNodes(positions: Record<string, PositionDTO>): void {
  const temporal = useGraphStore.temporal.getState()
  temporal.pause()
  useGraphStore.getState().setNodePositions(positions)
  temporal.resume()
}

/**
 * Reset the graph's undo history — call on every view switch. There is one shared undo stack
 * and its entries are whole-graph snapshots that include positions, but positions are the one
 * per-view thing. So undoing after a switch would clobber the view you're on with the *other*
 * view's snapshot. Clearing scopes undo to "since you arrived at this view" — the data itself
 * is untouched, only the cross-switch undo trail. (A per-view stack would need positions split
 * out of the undoable graph store entirely — a larger refactor, deferred.)
 */
function resetHistory(): void {
  useGraphStore.temporal.getState().clear()
}

export const useWorkspaceStore = create<WorkspaceState>()((set, get) => ({
  workspace: null,

  loadWorkspace: (workspace) => set({ workspace }),

  selectView: (viewId) => {
    const ws = get().workspace
    if (!ws) return
    if (activeView(ws)?.id === viewId) return // already showing it
    const next = setActiveTabView(flushLivePositions(ws), viewId)
    set({ workspace: next })
    const target = next.views[viewId]
    if (target) reprojectNodes(target.positions)
    resetHistory()
  },

  selectTab: (tabId) => {
    const ws = get().workspace
    if (!ws || ws.active_tab === tabId) return
    const next = { ...flushLivePositions(ws), active_tab: tabId }
    set({ workspace: next })
    const target = activeView(next)
    if (target) reprojectNodes(target.view.positions)
    resetHistory()
  },

  createView: () => {
    const ws = get().workspace
    if (!ws) return
    const flushed = flushLivePositions(ws)
    const current = activeView(flushed)
    // Seed the new view from the current arrangement so the canvas is already correct —
    // no re-projection needed (the live nodes already match the new view's positions).
    const positions = current?.view.positions ?? toPositions(useGraphStore.getState().nodes)
    const count = Object.keys(flushed.views).length + 1
    const { workspace: ws2, viewId } = addView(flushed, {
      graph: current?.view.graph ?? 'main',
      title: `View ${count}`,
      positions,
      // Inherit the current framing so creating a view doesn't jump the camera.
      viewport: current?.view.viewport ?? IDENTITY_VIEWPORT,
    })
    set({ workspace: setActiveTabView(ws2, viewId) })
    resetHistory()
  },

  renameView: (viewId, title) => {
    const ws = get().workspace
    if (!ws) return
    set({ workspace: retitleView(ws, viewId, title) })
  },

  deleteView: (viewId) => {
    const ws = get().workspace
    if (!ws) return
    const wasActive = activeView(ws)?.id === viewId
    // Deleting the active view discards its arrangement, so don't flush live drags into it.
    // Deleting any other view keeps the active one on screen — flush so its current drags survive.
    const base = wasActive ? ws : flushLivePositions(ws)
    const next = removeView(base, viewId)
    if (next === base) return // nothing removed (missing id, or the last view)
    set({ workspace: next })
    if (wasActive) {
      // The active tab was repointed to a survivor — show that view's stored arrangement.
      const target = activeView(next)
      if (target) reprojectNodes(target.view.positions)
      resetHistory()
    }
  },

  setActiveViewport: (viewport) => {
    const ws = get().workspace
    if (!ws) return
    const active = activeView(ws)
    if (!active) return
    set({ workspace: { ...ws, views: { ...ws.views, [active.id]: { ...active.view, viewport } } } })
  },
}))
