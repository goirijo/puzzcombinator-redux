// Geometry for "floating" edges: instead of pinning an edge to a fixed handle, we compute the
// point on each node's border that faces the other node, so an edge always attaches to whichever
// sides face each other. That's what lets the graph take any shape — a horizontal arrange makes
// edges run left↔right, a vertical one top↔bottom, and hand-dragging re-aims them live — without
// a node ever committing to a direction. Adapted from React Flow's floating-edges example; pure
// geometry, no React, so it unit-tests on plain numbers.

import { Position, type InternalNode, type XYPosition } from '@xyflow/react'

/** Half-width/height + center of a node, in absolute canvas coordinates. */
function box(node: InternalNode) {
  const { width = 0, height = 0 } = node.measured ?? {}
  const w = width / 2
  const h = height / 2
  return { w, h, cx: node.internals.positionAbsolute.x + w, cy: node.internals.positionAbsolute.y + h }
}

// The point where the line from `node`'s center toward `other`'s center crosses `node`'s border.
// (Both nodes are treated as the same size — ours are uniform — which is what keeps this to the
// upstream example's diamond-intersection trick.)
function borderPoint(node: InternalNode, other: InternalNode): XYPosition {
  const { w, h, cx, cy } = box(node)
  const o = box(other)

  const xx = (o.cx - cx) / (2 * w) - (o.cy - cy) / (2 * h)
  const yy = (o.cx - cx) / (2 * w) + (o.cy - cy) / (2 * h)
  const a = 1 / (Math.abs(xx) + Math.abs(yy))
  const bx = a * xx
  const by = a * yy
  return { x: w * (bx + by) + cx, y: h * (-bx + by) + cy }
}

// Which side of `node` the border point sits on — fed to getBezierPath so the curve leaves/enters
// perpendicular to that side.
function sideOf(node: InternalNode, point: XYPosition): Position {
  const { x, y } = node.internals.positionAbsolute
  const { width = 0 } = node.measured ?? {}
  if (Math.round(point.x) <= Math.round(x) + 1) return Position.Left
  if (Math.round(point.x) >= Math.round(x) + width - 1) return Position.Right
  if (Math.round(point.y) <= Math.round(y) + 1) return Position.Top
  return Position.Bottom
}

export interface EdgeGeometry {
  sx: number
  sy: number
  tx: number
  ty: number
  sourcePos: Position
  targetPos: Position
}

/** Border-attach points + sides for an edge between two nodes, recomputed from live positions. */
export function getEdgeParams(source: InternalNode, target: InternalNode): EdgeGeometry {
  const sp = borderPoint(source, target)
  const tp = borderPoint(target, source)
  return {
    sx: sp.x,
    sy: sp.y,
    tx: tp.x,
    ty: tp.y,
    sourcePos: sideOf(source, sp),
    targetPos: sideOf(target, tp),
  }
}
