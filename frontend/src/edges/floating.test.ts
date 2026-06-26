import { Position, type InternalNode } from '@xyflow/react'
import { describe, expect, it } from 'vitest'

import { getEdgeParams } from './floating'

// A minimal stand-in for what getEdgeParams reads off an InternalNode: its measured size and
// absolute position. (All hunt nodes share one size, so a fixed 100×40 is representative.)
function inode(x: number, y: number): InternalNode {
  return {
    measured: { width: 100, height: 40 },
    internals: { positionAbsolute: { x, y } },
  } as unknown as InternalNode
}

describe('getEdgeParams', () => {
  it('attaches to right→left when the target is to the right (horizontal layout)', () => {
    const { sourcePos, targetPos } = getEdgeParams(inode(0, 0), inode(200, 0))
    expect(sourcePos).toBe(Position.Right)
    expect(targetPos).toBe(Position.Left)
  })

  it('attaches to bottom→top when the target is below (vertical layout)', () => {
    const { sourcePos, targetPos } = getEdgeParams(inode(0, 0), inode(0, 200))
    expect(sourcePos).toBe(Position.Bottom)
    expect(targetPos).toBe(Position.Top)
  })

  it('flips sides when the relationship reverses, so edges re-aim on drag', () => {
    const { sourcePos, targetPos } = getEdgeParams(inode(200, 0), inode(0, 0))
    expect(sourcePos).toBe(Position.Left)
    expect(targetPos).toBe(Position.Right)
  })
})
