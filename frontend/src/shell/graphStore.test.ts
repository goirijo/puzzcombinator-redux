import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  isLooseArtifactNode,
  looseElementId,
  toPool,
  type CanvasNode,
  type HuntFlowEdge,
  type HuntFlowNode,
} from '../model/flow'
import type { ArtifactDTO } from '../model/graph'
import { useGraphStore } from './graphStore'

function node(id: string, x: number, y: number): HuntFlowNode {
  return { id, type: 'hunt', position: { x, y }, data: { label: id, action: '', notes: '' } }
}

function edge(id: string, content: ArtifactDTO[]): HuntFlowEdge {
  return { id, source: 'n1', target: 'n1', type: 'floating', data: { content } }
}

function looseArtifact(id: string): CanvasNode {
  return {
    id: looseElementId(id),
    type: 'artifact',
    connectable: false,
    position: { x: 0, y: 0 },
    data: { artifact: { type: 'text', id, name: id, payload: { text: '' } } },
  }
}

/** Reload the store with a scenario and re-baseline undo history (mirrors the beforeEach). */
function loadScenario(nodes: CanvasNode[], edges: HuntFlowEdge[]): void {
  useGraphStore.getState().loadGraph(nodes, edges)
  useGraphStore.temporal.getState().clear()
  vi.advanceTimersByTime(400)
}

// Fake timers so we can close the history debounce window deterministically. The store
// coalesces a burst of changes into one undo step via a leading-edge debounce (350ms); the
// load below opens such a burst, so we advance past it to get a clean baseline — otherwise a
// `createNode` in the same tick would be swallowed into the load's burst and never recorded.
beforeEach(() => {
  vi.useFakeTimers()
  useGraphStore.getState().loadGraph([node('n1', 0, 0)], [])
  useGraphStore.temporal.getState().clear() // baseline: no undo history
  vi.advanceTimersByTime(400) // let the load's debounce burst close
})

afterEach(() => {
  vi.useRealTimers()
})

describe('createNode', () => {
  it('appends a new blank node with a fresh, non-colliding id', () => {
    useGraphStore.getState().createNode()
    const nodes = useGraphStore.getState().nodes
    expect(nodes).toHaveLength(2)
    const added = nodes[1]
    expect(added.id).not.toBe('n1')
    expect(added.data).toEqual({ label: '', action: '', notes: '' })
  })

  it('adds a hunt node, not an artifact (the pool stays empty)', () => {
    useGraphStore.getState().createNode()
    expect(toPool(useGraphStore.getState().nodes)).toEqual([])
  })

  it('is undoable — undo removes exactly the created node', () => {
    useGraphStore.getState().createNode()
    expect(useGraphStore.getState().nodes).toHaveLength(2)
    useGraphStore.temporal.getState().undo()
    const nodes = useGraphStore.getState().nodes
    expect(nodes).toHaveLength(1)
    expect(nodes[0].id).toBe('n1')
  })
})

describe('createLooseArtifact', () => {
  it('adds a non-connectable artifact node carrying a pre-baked text artifact', () => {
    useGraphStore.getState().createLooseArtifact()
    const nodes = useGraphStore.getState().nodes
    expect(nodes).toHaveLength(2)
    const art = nodes.find(isLooseArtifactNode)!
    expect(art.connectable).toBe(false)
    expect(art.data.artifact.type).toBe('text')
    // The pool now reflects exactly that one artifact.
    expect(toPool(nodes)).toHaveLength(1)
  })

  it('is undoable — undo removes the created artifact', () => {
    useGraphStore.getState().createLooseArtifact()
    expect(useGraphStore.getState().nodes).toHaveLength(2)
    useGraphStore.temporal.getState().undo()
    expect(useGraphStore.getState().nodes).toHaveLength(1)
    expect(toPool(useGraphStore.getState().nodes)).toEqual([])
  })
})

describe('detachEdges', () => {
  const ART: ArtifactDTO = { type: 'text', id: 'a1', name: 'clue', payload: { text: 'hi' } }

  it('returns a deleted edge’s artifacts to the loose pool', () => {
    useGraphStore.getState().detachEdges([edge('e1', [ART])])
    const pool = toPool(useGraphStore.getState().nodes)
    expect(pool).toEqual([ART])
    // It re-entered as a non-connectable canvas node keyed by its loose element id.
    const art = useGraphStore.getState().nodes.find(isLooseArtifactNode)!
    expect(art.id).toBe(looseElementId('a1'))
    expect(art.connectable).toBe(false)
  })

  it('does nothing for edges with no content', () => {
    useGraphStore.getState().detachEdges([edge('e1', [])])
    expect(useGraphStore.getState().nodes).toHaveLength(1)
  })

  it('is undoable — undo drops the artifacts the delete had freed', () => {
    useGraphStore.getState().detachEdges([edge('e1', [ART])])
    expect(toPool(useGraphStore.getState().nodes)).toHaveLength(1)
    useGraphStore.temporal.getState().undo()
    expect(toPool(useGraphStore.getState().nodes)).toEqual([])
  })
})

describe('placeArtifactOnEdge', () => {
  const ART: ArtifactDTO = { type: 'text', id: 'u1', name: 'u1', payload: { text: '' } }

  it('moves a pooled artifact onto the edge and out of the pool', () => {
    loadScenario([node('n1', 0, 0), looseArtifact('u1')], [edge('e1', [])])
    useGraphStore.getState().placeArtifactOnEdge('u1', 'e1')
    const { nodes, edges } = useGraphStore.getState()
    expect(toPool(nodes)).toEqual([])
    expect(edges[0].data!.content).toEqual([ART])
  })

  it('is undoable — undo returns the artifact to the pool and clears the edge', () => {
    loadScenario([node('n1', 0, 0), looseArtifact('u1')], [edge('e1', [])])
    useGraphStore.getState().placeArtifactOnEdge('u1', 'e1')
    useGraphStore.temporal.getState().undo()
    const { nodes, edges } = useGraphStore.getState()
    expect(toPool(nodes)).toHaveLength(1)
    expect(edges[0].data!.content).toEqual([])
  })
})

describe('detachArtifact', () => {
  const ART: ArtifactDTO = { type: 'text', id: 'a1', name: 'clue', payload: { text: 'hi' } }

  it('moves one artifact off the edge back into the pool', () => {
    loadScenario([node('n1', 0, 0)], [edge('e1', [ART])])
    useGraphStore.getState().detachArtifact('e1', 'a1')
    const { nodes, edges } = useGraphStore.getState()
    expect(edges[0].data!.content).toEqual([])
    expect(toPool(nodes)).toEqual([ART])
  })

  it('is undoable — undo puts the artifact back on the edge', () => {
    loadScenario([node('n1', 0, 0)], [edge('e1', [ART])])
    useGraphStore.getState().detachArtifact('e1', 'a1')
    useGraphStore.temporal.getState().undo()
    const { nodes, edges } = useGraphStore.getState()
    expect(edges[0].data!.content).toEqual([ART])
    expect(toPool(nodes)).toEqual([])
  })
})
