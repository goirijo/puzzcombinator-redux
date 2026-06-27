import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { isLooseArtifactNode, toPool, type HuntFlowNode } from '../model/flow'
import { useGraphStore } from './graphStore'

function node(id: string, x: number, y: number): HuntFlowNode {
  return { id, type: 'hunt', position: { x, y }, data: { label: id, action: '', notes: '' } }
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
