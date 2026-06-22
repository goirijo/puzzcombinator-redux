import { describe, expect, it } from 'vitest'

import type { GraphBlockDTO } from './graph'
import { toFlowEdges, toFlowNodes, toGraphBlock, toPositions } from './flow'
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

describe('round-trip', () => {
  it('the hunt-data half reproduces the original graph block', () => {
    const nodes = toFlowNodes(GRAPH.nodes, POSITIONS)
    const edges = toFlowEdges(GRAPH.edges)
    expect(toGraphBlock(nodes, edges)).toEqual(GRAPH)
  })
})
