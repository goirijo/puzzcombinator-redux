import { beforeEach, describe, expect, it } from 'vitest'

import type { HuntFlowNode } from '../model/flow'
import type { WorkspaceDTO } from '../model/workspace'
import { useGraphStore } from './graphStore'
import { useWorkspaceStore } from './workspaceStore'

function node(id: string, x: number, y: number): HuntFlowNode {
  return { id, type: 'hunt', position: { x, y }, data: { label: id, action: '', notes: '' } }
}

// A fresh workspace each test: two views of one node at different positions, and two tabs
// (t1→v1 active, t2→v2) each with their own framing. Framing lives on the tab now.
function makeWorkspace(): WorkspaceDTO {
  return {
    views: {
      v1: { graph: 'main', title: 'A', positions: { n1: { x: 0, y: 0 } }, show_unplaced: true },
      v2: { graph: 'main', title: 'B', positions: { n1: { x: 500, y: 500 } }, show_unplaced: true },
    },
    tabs: [
      { id: 't1', view: 'v1', viewport: { x: 0, y: 0, zoom: 1 } },
      { id: 't2', view: 'v2', viewport: { x: -90, y: 12, zoom: 1.5 } },
    ],
    active_tab: 't1',
  }
}

beforeEach(() => {
  useGraphStore.getState().loadGraph([node('n1', 0, 0)], [])
  useGraphStore.temporal.getState().clear() // baseline: no undo history
  useWorkspaceStore.getState().loadWorkspace(makeWorkspace())
})

describe('selectView', () => {
  it('repoints the active tab and re-projects the target view onto the nodes', () => {
    useWorkspaceStore.getState().selectView('v2')
    expect(useWorkspaceStore.getState().workspace!.tabs[0].view).toBe('v2')
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 500, y: 500 })
  })

  it('flushes live drag positions into the view being left', () => {
    useGraphStore.getState().setNodePositions({ n1: { x: 42, y: 7 } }) // a drag in v1
    useWorkspaceStore.getState().selectView('v2')
    expect(useWorkspaceStore.getState().workspace!.views.v1.positions.n1).toEqual({ x: 42, y: 7 })
  })

  it('clears the undo history on switch, so undo never reaches across views', () => {
    // Seed history directly (the debounce makes recording-via-edit unreliable in a unit test).
    useGraphStore.temporal.setState({ pastStates: [{ nodes: [], edges: [] }] })
    useWorkspaceStore.getState().selectView('v2')
    expect(useGraphStore.temporal.getState().pastStates).toHaveLength(0)
  })

  it('is a no-op when the target view is already active', () => {
    useWorkspaceStore.getState().selectView('v1')
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 0, y: 0 })
  })
})

describe('createView', () => {
  it('adds a view seeded from the live positions and lands on it', () => {
    useGraphStore.getState().setNodePositions({ n1: { x: 9, y: 9 } })
    useWorkspaceStore.getState().createView()
    const ws = useWorkspaceStore.getState().workspace!
    expect(Object.keys(ws.views)).toHaveLength(3)
    const landedView = ws.tabs[0].view
    expect(landedView).not.toBe('v1') // switched to the new view
    expect(ws.views[landedView].positions.n1).toEqual({ x: 9, y: 9 }) // seeded from live nodes
  })

  it('keeps the tab framing so the camera does not jump', () => {
    useWorkspaceStore.getState().setActiveViewport({ x: -30, y: 5, zoom: 2 }) // frame the active tab
    useWorkspaceStore.getState().createView()
    const ws = useWorkspaceStore.getState().workspace!
    // The active tab kept its viewport while its view was repointed to the new one.
    expect(ws.tabs[0].viewport).toEqual({ x: -30, y: 5, zoom: 2 })
  })
})

describe('renameView', () => {
  it('retitles a view without touching the canvas', () => {
    useWorkspaceStore.getState().renameView('v2', 'Cellar')
    expect(useWorkspaceStore.getState().workspace!.views.v2.title).toBe('Cellar')
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 0, y: 0 }) // unmoved
  })
})

describe('setShowUnplaced', () => {
  it('flips a view’s flag without moving the canvas', () => {
    useWorkspaceStore.getState().setShowUnplaced('v1', false)
    expect(useWorkspaceStore.getState().workspace!.views.v1.show_unplaced).toBe(false)
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 0, y: 0 }) // unmoved
  })

  it('is per-view — flipping one leaves the others alone', () => {
    useWorkspaceStore.getState().setShowUnplaced('v1', false)
    expect(useWorkspaceStore.getState().workspace!.views.v2.show_unplaced).toBe(true)
  })
})

describe('deleteView', () => {
  it('removes a non-active view and leaves the canvas alone', () => {
    useWorkspaceStore.getState().deleteView('v2') // active tab is on v1
    const ws = useWorkspaceStore.getState().workspace!
    expect(ws.views).not.toHaveProperty('v2')
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 0, y: 0 }) // v1 unmoved
  })

  it('deleting the active view lands the tab on a survivor and re-projects it', () => {
    useWorkspaceStore.getState().deleteView('v1') // active; survivor v2 sits at 500,500
    const ws = useWorkspaceStore.getState().workspace!
    expect(ws.views).not.toHaveProperty('v1')
    expect(ws.tabs[0].view).toBe('v2')
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 500, y: 500 })
  })

  it('is a no-op when only one view remains', () => {
    useWorkspaceStore.getState().deleteView('v2')
    useWorkspaceStore.getState().deleteView('v1') // v1 is now the last view
    expect(Object.keys(useWorkspaceStore.getState().workspace!.views)).toEqual(['v1'])
  })
})

describe('setActiveViewport', () => {
  it('records the framing into the active tab only', () => {
    useWorkspaceStore.getState().setActiveViewport({ x: 7, y: 8, zoom: 0.9 })
    const ws = useWorkspaceStore.getState().workspace!
    expect(ws.tabs[0].viewport).toEqual({ x: 7, y: 8, zoom: 0.9 }) // active t1
    expect(ws.tabs[1].viewport).toEqual({ x: -90, y: 12, zoom: 1.5 }) // t2 untouched
  })

  it('does not persist a hover camera while previewing', () => {
    useWorkspaceStore.getState().previewTab('t2') // now previewing
    useWorkspaceStore.getState().setActiveViewport({ x: 1, y: 2, zoom: 3 })
    expect(useWorkspaceStore.getState().workspace!.tabs[0].viewport).toEqual({ x: 0, y: 0, zoom: 1 })
  })
})

describe('createTab', () => {
  it('opens a tab on the current view, inheriting its framing, and lands on it', () => {
    useWorkspaceStore.getState().setActiveViewport({ x: 3, y: 4, zoom: 2 }) // frame the active tab
    useWorkspaceStore.getState().createTab()
    const ws = useWorkspaceStore.getState().workspace!
    expect(ws.tabs).toHaveLength(3)
    const landed = ws.tabs.find((t) => t.id === ws.active_tab)!
    expect(landed.view).toBe('v1') // same view as the tab we were on
    expect(landed.viewport).toEqual({ x: 3, y: 4, zoom: 2 }) // inherited framing → no jump
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 0, y: 0 }) // same view, unmoved
  })
})

describe('deleteTab', () => {
  it('closing a background tab leaves the canvas and active tab alone', () => {
    useWorkspaceStore.getState().deleteTab('t2') // active is t1
    const ws = useWorkspaceStore.getState().workspace!
    expect(ws.tabs.map((t) => t.id)).toEqual(['t1'])
    expect(ws.active_tab).toBe('t1')
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 0, y: 0 })
  })

  it('closing the active tab lands on a neighbour and re-projects its view', () => {
    useWorkspaceStore.getState().deleteTab('t1') // active; neighbour t2 shows v2 at 500,500
    const ws = useWorkspaceStore.getState().workspace!
    expect(ws.active_tab).toBe('t2')
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 500, y: 500 })
  })

  it('refuses to close the last tab', () => {
    useWorkspaceStore.getState().deleteTab('t2')
    useWorkspaceStore.getState().deleteTab('t1') // t1 is now the last tab
    expect(useWorkspaceStore.getState().workspace!.tabs.map((t) => t.id)).toEqual(['t1'])
  })
})

describe('previewTab / clearPreview', () => {
  it('reprojects the hovered tab without committing, and reverts on clear', () => {
    useWorkspaceStore.getState().previewTab('t2') // active t1 (v1@0,0); t2 shows v2@500,500
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 500, y: 500 })
    expect(useWorkspaceStore.getState().previewTabId).toBe('t2')
    expect(useWorkspaceStore.getState().workspace!.active_tab).toBe('t1') // not committed

    useWorkspaceStore.getState().clearPreview()
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 0, y: 0 }) // reverted
    expect(useWorkspaceStore.getState().previewTabId).toBeNull()
  })

  it('restores an un-flushed drag on revert (snapshot, not stored positions)', () => {
    useGraphStore.getState().setNodePositions({ n1: { x: 42, y: 7 } }) // a drag in v1, not flushed
    useWorkspaceStore.getState().previewTab('t2')
    useWorkspaceStore.getState().previewTab(null) // mouse-out
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 42, y: 7 }) // drag survives
  })

  it('previewing a tab on the SAME view keeps the live (un-flushed) edit', () => {
    // Two tabs on one view, active t1; edit the view live, then hover the other tab on it.
    useWorkspaceStore.getState().loadWorkspace({
      views: { v1: { graph: 'main', title: 'A', positions: { n1: { x: 0, y: 0 } }, show_unplaced: true } },
      tabs: [
        { id: 't1', view: 'v1', viewport: { x: 0, y: 0, zoom: 1 } },
        { id: 't2', view: 'v1', viewport: { x: 9, y: 9, zoom: 2 } },
      ],
      active_tab: 't1',
    })
    useGraphStore.getState().setNodePositions({ n1: { x: 33, y: 44 } }) // un-flushed live edit
    useWorkspaceStore.getState().previewTab('t2') // same view → must not clobber with stale stored
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 33, y: 44 })
  })

  it('reverts to the active view when hovering from one preview to a same-as-active tab', () => {
    // t1 & t3 share view A (with the active tab t3); t2 shows view B. Edit A live, then hover
    // t2 (→ shows B), then hover t1 (same view as active) — must snap back to the live A edit.
    useWorkspaceStore.getState().loadWorkspace({
      views: {
        A: { graph: 'main', title: 'A', positions: { n1: { x: 0, y: 0 } }, show_unplaced: true },
        B: { graph: 'main', title: 'B', positions: { n1: { x: 500, y: 500 } }, show_unplaced: true },
      },
      tabs: [
        { id: 't1', view: 'A', viewport: { x: 0, y: 0, zoom: 1 } },
        { id: 't2', view: 'B', viewport: { x: 0, y: 0, zoom: 1 } },
        { id: 't3', view: 'A', viewport: { x: 0, y: 0, zoom: 1 } },
      ],
      active_tab: 't3',
    })
    useGraphStore.getState().setNodePositions({ n1: { x: 77, y: 88 } }) // un-flushed edit in A
    useWorkspaceStore.getState().previewTab('t2') // → view B
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 500, y: 500 })
    useWorkspaceStore.getState().previewTab('t1') // same view as active t3 → back to live A edit
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 77, y: 88 })
  })

  it('hovering the active tab is a no-op', () => {
    useWorkspaceStore.getState().previewTab('t1') // already active
    expect(useWorkspaceStore.getState().previewTabId).toBeNull()
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 0, y: 0 })
  })

  it('committing (selectTab) ends a preview first, flushing the true active view', () => {
    useGraphStore.getState().setNodePositions({ n1: { x: 11, y: 22 } }) // un-flushed drag in v1
    useWorkspaceStore.getState().previewTab('t2') // canvas now shows v2
    useWorkspaceStore.getState().selectTab('t2') // commit to t2
    // The drag was flushed into v1 (not lost to the previewed positions), and we're on v2.
    expect(useWorkspaceStore.getState().workspace!.views.v1.positions.n1).toEqual({ x: 11, y: 22 })
    expect(useWorkspaceStore.getState().previewTabId).toBeNull()
  })
})
