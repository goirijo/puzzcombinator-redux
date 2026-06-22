import { describe, expect, it } from 'vitest'

import { buildSaveRequest, toFlowGraph, type GraphResponseDTO } from './api'
import type { WorkspaceDTO } from './workspace'

const WS: WorkspaceDTO = {
  views: { v1: { graph: 'main', title: 'Main', positions: { n1: { x: 10, y: 20 } } } },
  tabs: [{ id: 't1', view: 'v1', viewport: { x: 0, y: 0, zoom: 1 } }],
  active_tab: 't1',
}

const RES: GraphResponseDTO = {
  schema_version: '3',
  graph: {
    nodes: [
      { id: 'n1', action: null, label: 'Start', notes: null },
      { id: 'n2', action: null, label: 'End', notes: null },
    ],
    edges: [],
  },
  workspace: WS,
}

describe('toFlowGraph (load: fuse the channels)', () => {
  it('projects the active view positions onto nodes, falling back to 0,0 when absent', () => {
    const { nodes } = toFlowGraph(RES)
    expect(nodes.find((n) => n.id === 'n1')!.position).toEqual({ x: 10, y: 20 })
    expect(nodes.find((n) => n.id === 'n2')!.position).toEqual({ x: 0, y: 0 })
  })
})

describe('buildSaveRequest (save: split the channels)', () => {
  it('drops positions from the graph block and refreshes the active view from the nodes', () => {
    const { nodes, edges } = toFlowGraph(RES)
    const moved = nodes.map((n) => (n.id === 'n2' ? { ...n, position: { x: 99, y: 88 } } : n))
    const body = buildSaveRequest(moved, edges, WS)

    // The graph block is hunt data only — no positions.
    expect(body.graph.nodes.find((n) => n.id === 'n1')).toEqual({
      id: 'n1',
      action: null,
      label: 'Start',
      notes: null,
    })
    // The active view's positions came from the live nodes (incl. the move).
    expect(body.workspace.views.v1.positions).toEqual({
      n1: { x: 10, y: 20 },
      n2: { x: 99, y: 88 },
    })
    // The rest of the workspace is preserved untouched.
    expect(body.workspace.active_tab).toBe('t1')
    expect(body.workspace.tabs).toEqual(WS.tabs)
  })
})
