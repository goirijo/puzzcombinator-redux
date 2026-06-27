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
  activeTab,
  activeView,
  createTab as addTab,
  createView as addView,
  deleteTab as removeTab,
  deleteView as removeView,
  IDENTITY_VIEWPORT,
  renameView as retitleView,
  setActiveTabView,
  setShowUnplaced as setViewShowUnplaced,
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
  /** Open a new tab (window) on the current view, inheriting its framing, and land on it. */
  createTab: () => void
  /** Close a tab; if it was active, land on a neighbour. Never closes the last tab. */
  deleteTab: (tabId: string) => void
  /** Retitle a view (metadata only — no canvas change, not undoable). */
  renameView: (viewId: string, title: string) => void
  /** Set a view's "draw the unplaced pool?" flag (per-view display state, not undoable). */
  setShowUnplaced: (viewId: string, value: boolean) => void
  /** Delete a view; if it was the one on screen, land the active tab on a survivor. */
  deleteView: (viewId: string) => void
  /** Record the current pan/zoom into the active tab (the camera moved on the canvas). */
  setActiveViewport: (viewport: ViewportDTO) => void

  /** The tab currently being hover-previewed, or null. Transient (not persisted). */
  previewTabId: string | null
  /** Live node positions snapshotted at preview start, restored on clear. Transient. */
  previewRestore: Record<string, PositionDTO> | null
  /** Preview a tab's arrangement on hover (pass null to revert). Canvas-inert while active. */
  previewTab: (tabId: string | null) => void
  /** Revert a hover-preview, restoring the true active arrangement. No-op when not previewing. */
  clearPreview: () => void
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

export const useWorkspaceStore = create<WorkspaceState>()((set, get) => {
  // Every action that flushes live positions must first end any hover-preview, or the flush
  // would capture the *previewed* arrangement and write it into the wrong view. Wrapping the
  // action keeps that invariant in one place instead of a copy-pasted first line per action —
  // and makes it impossible to forget when adding the next committing action.
  function committing<A extends unknown[]>(fn: (...args: A) => void): (...args: A) => void {
    return (...args) => {
      get().clearPreview()
      fn(...args)
    }
  }

  return {
    workspace: null,

    // A fresh load starts with no transient preview in flight.
    loadWorkspace: (workspace) => set({ workspace, previewTabId: null, previewRestore: null }),

    selectView: committing((viewId) => {
      const ws = get().workspace
      if (!ws) return
      if (activeView(ws)?.id === viewId) return // already showing it
      const next = setActiveTabView(flushLivePositions(ws), viewId)
      set({ workspace: next })
      const target = next.views[viewId]
      if (target) reprojectNodes(target.positions)
      resetHistory()
    }),

    selectTab: committing((tabId) => {
      const ws = get().workspace
      if (!ws || ws.active_tab === tabId) return
      const next = { ...flushLivePositions(ws), active_tab: tabId }
      set({ workspace: next })
      const target = activeView(next)
      if (target) reprojectNodes(target.view.positions)
      resetHistory()
    }),

    createView: committing(() => {
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
        // A new view copies the current arrangement, so inherit its show-unplaced choice too.
        show_unplaced: current?.view.show_unplaced ?? true,
      })
      // Repoint the active tab at the new view; the tab keeps its own framing, so the
      // (current-seeded) view shows with the current camera — no jump.
      set({ workspace: setActiveTabView(ws2, viewId) })
      resetHistory()
    }),

    renameView: (viewId, title) => {
      const ws = get().workspace
      if (!ws) return
      set({ workspace: retitleView(ws, viewId, title) })
    },

    // A pure display flag on the view — no positions move, so (like rename) no flush, no
    // reproject, no history reset. The canvas re-derives what it draws from the new flag.
    setShowUnplaced: (viewId, value) => {
      const ws = get().workspace
      if (!ws) return
      set({ workspace: setViewShowUnplaced(ws, viewId, value) })
    },

    deleteView: committing((viewId) => {
      const ws = get().workspace
      if (!ws) return
      const wasActive = activeView(ws)?.id === viewId
      // Deleting the active view discards its arrangement, so don't flush live drags into it.
      // Deleting any other view keeps the active one on screen — flush so its drags survive.
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
    }),

    createTab: committing(() => {
      const ws = get().workspace
      if (!ws) return
      const flushed = flushLivePositions(ws)
      const current = activeTab(flushed)
      // A new window on the CURRENT view, inheriting its framing (opens where you are).
      const viewId = current?.view ?? Object.keys(flushed.views)[0]
      if (!viewId) return
      const { workspace: ws2, tabId } = addTab(flushed, viewId, current?.viewport ?? IDENTITY_VIEWPORT)
      // Same view → live nodes already correct, so no reproject; just land on the new tab.
      set({ workspace: { ...ws2, active_tab: tabId } })
      resetHistory()
    }),

    deleteTab: committing((tabId) => {
      const ws = get().workspace
      if (!ws) return
      if (ws.active_tab !== tabId) {
        // Closing a background tab: the canvas doesn't change — no flush/reproject/history reset.
        const next = removeTab(ws, tabId)
        if (next !== ws) set({ workspace: next })
        return
      }
      // Closing the active tab: preserve its live drags, then land on the neighbour.
      const deletedView = activeTab(ws)?.view
      const flushed = flushLivePositions(ws)
      const next = removeTab(flushed, tabId)
      if (next === flushed) return // refused (last tab)
      set({ workspace: next })
      // Reproject only when the neighbour shows a different view (same view → nodes already right).
      const target = activeView(next)
      if (target && target.id !== deletedView) reprojectNodes(target.view.positions)
      resetHistory()
    }),

    setActiveViewport: (viewport) => {
      const ws = get().workspace
      if (!ws) return
      // While previewing, the camera on screen is the hovered tab's — don't persist it into
      // the active tab. A real pan only happens on the active tab (preview is canvas-inert).
      if (get().previewTabId !== null) return
      const tab = activeTab(ws)
      if (!tab) return
      // Framing belongs to the tab now: persist the camera into the active tab, not its view.
      set({
        workspace: {
          ...ws,
          tabs: ws.tabs.map((t) => (t.id === tab.id ? { ...t, viewport } : t)),
        },
      })
    },

    previewTabId: null,
    previewRestore: null,

    previewTab: (tabId) => {
      const ws = get().workspace
      if (!ws) return
      // Hovering the tab already on screen (or leaving the bar) just reverts any active preview.
      if (tabId === null || tabId === ws.active_tab) {
        get().clearPreview()
        return
      }
      if (get().previewTabId === tabId) return // already previewing it
      const tab = ws.tabs.find((t) => t.id === tabId)
      const view = tab && ws.views[tab.view]
      if (!view) return
      // Never disturb an in-flight node drag — previewing is a strictly canvas-inert state.
      if (useGraphStore.getState().nodes.some((n) => n.dragging)) return
      // First hover snapshots the TRUE live positions so mouse-out restores them exactly
      // (including any un-flushed drag) without mutating the persisted workspace.
      const restore = get().previewRestore ?? toPositions(useGraphStore.getState().nodes)
      set({ previewTabId: tabId, previewRestore: restore })
      // If the hovered tab shows the SAME view as the active tab, the active view's live
      // arrangement (including un-flushed edits) is the truth — and that's exactly our restore
      // snapshot. Reproject it rather than the stale stored positions; this also undoes any
      // prior preview of a *different* view. Otherwise show the hovered view's stored positions.
      reprojectNodes(tab.view === activeView(ws)?.id ? restore : view.positions)
    },

    clearPreview: () => {
      const { previewTabId, previewRestore } = get()
      if (previewTabId === null) return
      if (previewRestore) reprojectNodes(previewRestore)
      set({ previewTabId: null, previewRestore: null })
    },
  }
})
