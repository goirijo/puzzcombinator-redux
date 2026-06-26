import { beforeEach, describe, expect, it } from 'vitest'

import type { HuntFlowNode } from '../model/flow'
import type { WorkspaceDTO } from '../model/workspace'
import { useGraphStore } from './graphStore'
import { useWorkspaceStore } from './workspaceStore'

function node(id: string, x: number, y: number): HuntFlowNode {
  return { id, type: 'hunt', position: { x, y }, data: { label: id, action: '', notes: '' } }
}

// A fresh workspace each test: two views of one node, at different positions/framings, tab on v1.
function makeWorkspace(): WorkspaceDTO {
  return {
    views: {
      v1: { graph: 'main', title: 'A', positions: { n1: { x: 0, y: 0 } }, viewport: { x: 0, y: 0, zoom: 1 } },
      v2: { graph: 'main', title: 'B', positions: { n1: { x: 500, y: 500 } }, viewport: { x: -90, y: 12, zoom: 1.5 } },
    },
    tabs: [{ id: 't1', view: 'v1' }],
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

  it('inherits the current view framing so the camera does not jump', () => {
    useWorkspaceStore.getState().setActiveViewport({ x: -30, y: 5, zoom: 2 }) // frame v1
    useWorkspaceStore.getState().createView()
    const ws = useWorkspaceStore.getState().workspace!
    expect(ws.views[ws.tabs[0].view].viewport).toEqual({ x: -30, y: 5, zoom: 2 })
  })
})

describe('renameView', () => {
  it('retitles a view without touching the canvas', () => {
    useWorkspaceStore.getState().renameView('v2', 'Cellar')
    expect(useWorkspaceStore.getState().workspace!.views.v2.title).toBe('Cellar')
    expect(useGraphStore.getState().nodes[0].position).toEqual({ x: 0, y: 0 }) // unmoved
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
  it('records the framing into the active view only', () => {
    useWorkspaceStore.getState().setActiveViewport({ x: 7, y: 8, zoom: 0.9 })
    const ws = useWorkspaceStore.getState().workspace!
    expect(ws.views.v1.viewport).toEqual({ x: 7, y: 8, zoom: 0.9 }) // active
    expect(ws.views.v2.viewport).toEqual({ x: -90, y: 12, zoom: 1.5 }) // untouched
  })
})
