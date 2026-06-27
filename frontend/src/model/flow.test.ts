import { describe, expect, it } from 'vitest'

import type { GraphBlockDTO } from './graph'
import {
  applyPositions,
  detachedArtifactNodes,
  looseElementId,
  makeLooseArtifact,
  makeNode,
  toFlowArtifacts,
  toFlowEdges,
  toFlowNodes,
  toGraphBlock,
  toPool,
  toPositions,
} from './flow'
import type { PositionDTO } from './workspace'

// A small chain: n1 -> n2 -> n3, one artifact on the first edge, and some null fields
// (the backend sends null for an unset action/label/notes).
const GRAPH: GraphBlockDTO = {
  nodes: [
    { id: 'n1', action: null, label: 'Start', notes: null },
    { id: 'n2', action: 'solve', label: null, notes: 'a note' },
    { id: 'n3', action: null, label: 'End', notes: null },
  ],
  edges: [
    {
      id: 'e1',
      source: 'n1',
      target: 'n2',
      content: [{ type: 'text', id: 'a1', name: 'clue', payload: { text: 'hi' } }],
    },
    { id: 'e2', source: 'n2', target: 'n3', content: [] },
  ],
}

// Positions come from a view (the workspace channel), not the graph.
const POSITIONS: Record<string, PositionDTO> = {
  n1: { x: 10, y: 20 },
  n2: { x: 230, y: 20 },
  n3: { x: 450, y: 20 },
}

describe('toFlowNodes', () => {
  it('projects nodes through the view positions, falling back to 0,0 when absent', () => {
    const nodes = toFlowNodes(GRAPH.nodes, POSITIONS)
    expect(nodes.find((n) => n.id === 'n1')!.position).toEqual({ x: 10, y: 20 })
    expect(toFlowNodes(GRAPH.nodes, {})[0].position).toEqual({ x: 0, y: 0 })
  })

  it('coalesces null label/action/notes to empty string (so inputs stay controlled)', () => {
    const n1 = toFlowNodes(GRAPH.nodes, POSITIONS).find((n) => n.id === 'n1')!
    expect(n1.data.label).toBe('Start')
    expect(n1.data.action).toBe('')
    expect(n1.data.notes).toBe('')
  })
})

describe('toFlowEdges', () => {
  it('labels edges with their artifact count, undefined when empty', () => {
    const edges = toFlowEdges(GRAPH.edges)
    expect(edges.find((e) => e.id === 'e1')!.label).toBe('1')
    expect(edges.find((e) => e.id === 'e2')!.label).toBeUndefined()
    expect(edges.find((e) => e.id === 'e1')!.data!.content).toHaveLength(1)
  })
})

describe('toGraphBlock', () => {
  it('maps empty-string fields back to null (the inverse of the projection coalescing)', () => {
    const block = toGraphBlock(toFlowNodes(GRAPH.nodes, POSITIONS), [])
    const n1 = block.nodes.find((n) => n.id === 'n1')!
    expect(n1.label).toBe('Start')
    expect(n1.action).toBeNull()
    expect(n1.notes).toBeNull()
  })

  it('preserves edge wiring and artifact content', () => {
    const block = toGraphBlock([], toFlowEdges(GRAPH.edges))
    expect(block.edges.find((e) => e.id === 'e1')!.content).toEqual(GRAPH.edges[0].content)
    expect(block.edges.find((e) => e.id === 'e2')!.content).toEqual([])
  })
})

describe('toPositions', () => {
  it('extracts each node’s current position for the workspace channel', () => {
    expect(toPositions(toFlowNodes(GRAPH.nodes, POSITIONS))).toEqual(POSITIONS)
  })
})

describe('applyPositions', () => {
  it('swaps in new positions while preserving node identity and data', () => {
    const nodes = toFlowNodes(GRAPH.nodes, POSITIONS)
    const moved = applyPositions(nodes, { n1: { x: 5, y: 6 } })
    const n1 = moved.find((n) => n.id === 'n1')!
    expect(n1.position).toEqual({ x: 5, y: 6 })
    expect(n1.data).toEqual(nodes.find((n) => n.id === 'n1')!.data) // data untouched
  })

  it('falls back to 0,0 for nodes absent from the map', () => {
    const nodes = toFlowNodes(GRAPH.nodes, POSITIONS)
    expect(applyPositions(nodes, {}).find((n) => n.id === 'n2')!.position).toEqual({ x: 0, y: 0 })
  })

  it('round-trips with toPositions (apply then read back)', () => {
    const nodes = toFlowNodes(GRAPH.nodes, POSITIONS)
    expect(toPositions(applyPositions(nodes, POSITIONS))).toEqual(POSITIONS)
  })
})

describe('round-trip', () => {
  it('the hunt-data half reproduces the original graph block', () => {
    const nodes = toFlowNodes(GRAPH.nodes, POSITIONS)
    const edges = toFlowEdges(GRAPH.edges)
    expect(toGraphBlock(nodes, edges)).toEqual(GRAPH)
  })
})

describe('makeNode', () => {
  it('builds a blank hunt node with empty fields and an id', () => {
    const n = makeNode()
    expect(n.type).toBe('hunt')
    expect(n.data).toEqual({ label: '', action: '', notes: '' })
    expect(n.id).toBeTruthy()
  })

  it('mints a distinct opaque id each call (not the backend nN scheme)', () => {
    const a = makeNode()
    const b = makeNode()
    expect(a.id).not.toBe(b.id)
    // Opaque on purpose — not GraphBuilder's readable `nN` sugar.
    expect(a.id).not.toMatch(/^n\d+$/)
  })

  it('cascades the spawn position by spawnIndex so creations do not stack', () => {
    expect(makeNode(1).position).not.toEqual(makeNode(0).position)
  })
})

describe('loose artifacts on the canvas', () => {
  const POOL = [{ type: 'text', id: 'u1', name: 'text', payload: { text: 'hi' } }]

  it('toFlowArtifacts projects the pool into non-connectable artifact nodes with positions', () => {
    const [node] = toFlowArtifacts(POOL, { 'loose:u1': { x: 5, y: 6 } })
    expect(node.id).toBe(looseElementId('u1'))
    expect(node.type).toBe('artifact')
    expect(node.connectable).toBe(false)
    expect(node.position).toEqual({ x: 5, y: 6 })
    expect(node.data.artifact).toEqual(POOL[0])
  })

  it('toFlowArtifacts falls back to 0,0 when the artifact has no stored position', () => {
    expect(toFlowArtifacts(POOL, {})[0].position).toEqual({ x: 0, y: 0 })
  })

  it('toPool extracts artifacts back out, ignoring hunt nodes', () => {
    const mixed = [...toFlowNodes(GRAPH.nodes, {}), ...toFlowArtifacts(POOL, {})]
    expect(toPool(mixed)).toEqual(POOL)
  })

  it('toGraphBlock drops artifact nodes from the hunt-data block', () => {
    const mixed = [...toFlowNodes(GRAPH.nodes, {}), ...toFlowArtifacts(POOL, {})]
    expect(toGraphBlock(mixed, []).nodes.map((n) => n.id)).toEqual(['n1', 'n2', 'n3'])
  })

  it('makeLooseArtifact builds a non-connectable node with a pre-baked, named text artifact', () => {
    const node = makeLooseArtifact()
    expect(node.type).toBe('artifact')
    expect(node.connectable).toBe(false)
    expect(node.data.artifact.type).toBe('text')
    // Every artifact has a name (what the generic node renders) — not payload-specific.
    expect(node.data.artifact.name).toBe('New artifact')
    expect(node.id).toBe(looseElementId(node.data.artifact.id))
  })
})

describe('detachedArtifactNodes', () => {
  // e1 (n1→n2) carries one artifact (a1); e2 carries none. Both are real flow edges.
  const [e1, e2] = toFlowEdges(GRAPH.edges)
  // n1 at x=10, n2 at x=230 (from POSITIONS) → e1's midpoint is x=120.
  const POS = new Map(Object.entries(POSITIONS))

  it('turns a deleted edge’s artifacts into non-connectable loose-artifact nodes', () => {
    const detached = detachedArtifactNodes([e1], new Set(), POS)
    expect(detached).toHaveLength(1)
    expect(detached[0].id).toBe(looseElementId('a1'))
    expect(detached[0].type).toBe('artifact')
    expect(detached[0].connectable).toBe(false)
    expect(detached[0].data.artifact).toEqual(GRAPH.edges[0].content[0])
  })

  it('anchors the freed artifact at the deleted edge’s midpoint', () => {
    const [node] = detachedArtifactNodes([e1], new Set(), POS)
    // midpoint of n1 (10,20) and n2 (230,20).
    expect(node.position).toEqual({ x: 120, y: 20 })
  })

  it('falls back to a neutral spot when the edge’s endpoints have no known position', () => {
    expect(detachedArtifactNodes([e1], new Set(), new Map())[0].position).toEqual({ x: 200, y: 300 })
  })

  it('yields nothing for an edge with no content', () => {
    expect(detachedArtifactNodes([e2], new Set(), POS)).toEqual([])
  })

  it('skips artifacts already present (e.g. still in the pool), keyed by element id', () => {
    expect(detachedArtifactNodes([e1], new Set([looseElementId('a1')]), POS)).toEqual([])
  })
})
