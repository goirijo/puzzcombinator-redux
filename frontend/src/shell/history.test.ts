import { describe, expect, it, vi } from 'vitest'

import type { CanvasGraph, HuntFlowEdge, HuntFlowNode } from '../model/flow'
import { graphSignature, leadingDebounce } from './history'

function node(over: Partial<HuntFlowNode> = {}): HuntFlowNode {
  return {
    id: 'n1',
    type: 'hunt',
    position: { x: 10, y: 20 },
    data: { label: 'L', action: 'a', notes: '' },
    ...over,
  }
}

const state = (nodes: HuntFlowNode[], edges: HuntFlowEdge[] = []): CanvasGraph => ({ nodes, edges })

describe('graphSignature', () => {
  it('is unchanged by selection/drag flags (so clicking a node makes no undo step)', () => {
    const base = state([node()])
    const selected = state([node({ selected: true, dragging: true })])
    expect(graphSignature(base)).toBe(graphSignature(selected))
  })

  it('is unchanged by sub-pixel position jitter (rounds positions)', () => {
    const a = state([node({ position: { x: 10.2, y: 20.4 } })])
    const b = state([node({ position: { x: 9.8, y: 19.6 } })])
    expect(graphSignature(a)).toBe(graphSignature(b))
  })

  it('changes when an editable field changes', () => {
    const before = state([node()])
    const after = state([node({ data: { label: 'L2', action: 'a', notes: '' } })])
    expect(graphSignature(before)).not.toBe(graphSignature(after))
  })

  it('changes when a node moves a meaningful distance', () => {
    const before = state([node({ position: { x: 10, y: 20 } })])
    const after = state([node({ position: { x: 200, y: 20 } })])
    expect(graphSignature(before)).not.toBe(graphSignature(after))
  })

  it('changes when edge wiring changes', () => {
    const e = (over: Partial<HuntFlowEdge>): HuntFlowEdge => ({ id: 'e1', source: 'a', target: 'b', ...over })
    expect(graphSignature(state([], [e({})]))).not.toBe(graphSignature(state([], [e({ target: 'c' })])))
  })
})

describe('leadingDebounce', () => {
  it('fires once on the leading edge of a burst with the FIRST call args', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const d = leadingDebounce(fn, 300)

    d('a')
    d('b')
    d('c')
    expect(fn).toHaveBeenCalledTimes(1)
    expect(fn).toHaveBeenCalledWith('a') // the pre-burst state, the correct undo target

    vi.useRealTimers()
  })

  it('fires again only after the quiet window elapses', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const d = leadingDebounce(fn, 300)

    d('first')
    expect(fn).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(150)
    d('still-suppressed') // within the window — resets the timer, does not fire
    expect(fn).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(300) // now quiet for >300ms since the last call
    d('next-burst')
    expect(fn).toHaveBeenCalledTimes(2)
    expect(fn).toHaveBeenLastCalledWith('next-burst')

    vi.useRealTimers()
  })
})
