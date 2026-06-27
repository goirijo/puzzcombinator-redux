import { afterEach, describe, expect, it, vi } from 'vitest'

import { buildSaveRequest, requestArrange, toFlowGraph, type GraphResponseDTO } from './api'
import type { GraphBlockDTO } from './graph'
import type { WorkspaceDTO } from './workspace'

const WS: WorkspaceDTO = {
  views: {
    v1: { graph: 'main', title: 'Main', positions: { n1: { x: 10, y: 20 } } },
  },
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
  unplaced: [{ type: 'text', id: 'u1', name: 'text', payload: { text: 'loose' } }],
  workspace: WS,
}

describe('toFlowGraph (load: fuse the channels)', () => {
  it('projects the active view positions onto nodes, falling back to 0,0 when absent', () => {
    const { nodes } = toFlowGraph(RES)
    expect(nodes.find((n) => n.id === 'n1')!.position).toEqual({ x: 10, y: 20 })
    expect(nodes.find((n) => n.id === 'n2')!.position).toEqual({ x: 0, y: 0 })
  })

  it('fuses the loose-artifact pool in as a non-connectable artifact node', () => {
    const { nodes } = toFlowGraph(RES)
    const art = nodes.find((n) => n.id === 'loose:u1')
    expect(art?.type).toBe('artifact')
    expect(art?.connectable).toBe(false)
  })
})

describe('buildSaveRequest (save: split the channels)', () => {
  it('drops positions from the graph block and refreshes the active view from the nodes', () => {
    const { nodes, edges } = toFlowGraph(RES)
    const moved = nodes.map((n) => (n.id === 'n2' ? { ...n, position: { x: 99, y: 88 } } : n))
    const body = buildSaveRequest(moved, edges, WS)

    // The graph block is hunt data only — no positions, and no loose-artifact node.
    expect(body.graph.nodes.map((n) => n.id)).toEqual(['n1', 'n2'])
    expect(body.graph.nodes.find((n) => n.id === 'n1')).toEqual({
      id: 'n1',
      action: null,
      label: 'Start',
      notes: null,
    })
    // The active view's positions came from the live nodes (incl. the move) — hunt nodes AND
    // the artifact node (per-view placement applies to both; the artifact had none, so 0,0).
    expect(body.workspace.views.v1.positions).toEqual({
      n1: { x: 10, y: 20 },
      n2: { x: 99, y: 88 },
      'loose:u1': { x: 0, y: 0 },
    })
    // The rest of the workspace is preserved untouched.
    expect(body.workspace.active_tab).toBe('t1')
    expect(body.workspace.tabs).toEqual(WS.tabs)
  })

  it('round-trips the loose-artifact pool: fused in on load, extracted back on save', () => {
    const { nodes, edges } = toFlowGraph(RES)
    const body = buildSaveRequest(nodes, edges, WS)
    expect(body.unplaced).toEqual(RES.unplaced)
  })
})

describe('requestArrange', () => {
  const GRAPH: GraphBlockDTO = {
    nodes: [{ id: 'n1', action: null, label: null, notes: null }],
    edges: [],
  }

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('POSTs the graph + orientation and returns the positions map', async () => {
    const positions = { n1: { x: 40, y: 0 } }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ positions }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await requestArrange(GRAPH, 'vertical')

    expect(result).toEqual(positions)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/arrange')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ graph: GRAPH, orientation: 'vertical' })
  })

  it('surfaces the server detail on a non-ok response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: () => Promise.resolve({ detail: 'cannot arrange: cycle' }),
      }),
    )

    await expect(requestArrange(GRAPH, 'horizontal')).rejects.toThrow('cannot arrange: cycle')
  })
})
