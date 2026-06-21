import { describe, expect, it } from 'vitest'

import type { GraphResponseDTO } from './api'
import { fromFlow, toFlow } from './adapt'

// A small chain: start -> middle -> end, with one artifact on the first edge and some
// null fields (the backend sends null for an unset action/label/notes).
const SAMPLE: GraphResponseDTO = {
  schema_version: '3',
  graph: {
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
  },
  layout: {
    n1: { layer: 0, row: 0, x: 10, y: 20 },
    n2: { layer: 1, row: 0, x: 230, y: 20 },
    n3: { layer: 2, row: 0, x: 450, y: 20 },
  },
}

describe('toFlow', () => {
  it('places nodes from the layout map, falling back to 0,0 when absent', () => {
    const { nodes } = toFlow(SAMPLE)
    expect(nodes.find((n) => n.id === 'n1')!.position).toEqual({ x: 10, y: 20 })

    const noLayout = { ...SAMPLE, layout: {} }
    expect(toFlow(noLayout).nodes[0].position).toEqual({ x: 0, y: 0 })
  })

  it('coalesces null label/action/notes to empty string (so inputs stay controlled)', () => {
    const n1 = toFlow(SAMPLE).nodes.find((n) => n.id === 'n1')!
    // n1 has null action and notes, and a real label.
    expect(n1.data.label).toBe('Start')
    expect(n1.data.action).toBe('')
    expect(n1.data.notes).toBe('')
  })

  it('labels edges with their artifact names, undefined when empty', () => {
    const edges = toFlow(SAMPLE).edges
    expect(edges.find((e) => e.id === 'e1')!.label).toBe('clue')
    expect(edges.find((e) => e.id === 'e2')!.label).toBeUndefined()
    expect(edges.find((e) => e.id === 'e1')!.data!.content).toHaveLength(1)
  })
})

describe('fromFlow', () => {
  it('maps empty-string fields back to null (the inverse of toFlow coalescing)', () => {
    const { nodes } = toFlow(SAMPLE)
    const block = fromFlow(nodes, [])
    const n1 = block.nodes.find((n) => n.id === 'n1')!
    expect(n1.label).toBe('Start')
    expect(n1.action).toBeNull()
    expect(n1.notes).toBeNull()
  })

  it('preserves edge wiring and artifact content', () => {
    const { nodes, edges } = toFlow(SAMPLE)
    const block = fromFlow(nodes, edges)
    expect(block.edges.find((e) => e.id === 'e1')!.content).toEqual(SAMPLE.graph.edges[0].content)
    expect(block.edges.find((e) => e.id === 'e2')!.content).toEqual([])
  })
})

describe('round-trip', () => {
  it('fromFlow(toFlow(res)) reproduces the original graph block', () => {
    const { nodes, edges } = toFlow(SAMPLE)
    expect(fromFlow(nodes, edges)).toEqual(SAMPLE.graph)
  })
})
