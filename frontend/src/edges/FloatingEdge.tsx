// A "floating" edge: its path is computed from the two nodes' live geometry (edges/floating),
// not from a fixed handle, so it attaches to whichever sides face each other. useInternalNode
// subscribes to each endpoint's measured size + absolute position, so the edge re-draws as
// nodes move (drag, arrange, view switch).
//
// An edge that carries artifacts shows a small count pill at its midpoint. Hovering it reveals a
// grid of every artifact on the edge (reusing ArtifactChip, the same visual as a loose artifact).
// The reveal is pure CSS :hover (theme.css) — both the pill and the grid are always rendered, so
// there's no React state to get stuck: the browser keeps the grid open while the pointer is over
// the pill or any chip, and closes it the moment it leaves. We only feed CSS the edge midpoint and
// the inverse zoom (as custom properties) so the grid can pin itself there at a fixed on-screen
// size regardless of zoom.

import type { CSSProperties } from 'react'
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  useInternalNode,
  useStore,
  type EdgeProps,
} from '@xyflow/react'

import type { HuntFlowEdge } from '../model/flow'
import { ArtifactChip } from '../nodes/ArtifactChip'
import { getEdgeParams } from './floating'

// Lay the exploded chips out as a compact block instead of one long row. We aim for a near-square
// *cell* grid (cols ≈ rows); because a chip is wider than it is tall, that reads as a roughly 3:1
// wide box. Raise GRID_ASPECT to bias toward more columns (wider), lower it toward a single column.
const GRID_ASPECT = 0.3
function gridColumns(count: number): number {
  return Math.min(count, Math.max(1, Math.ceil(Math.sqrt(count * GRID_ASPECT))))
}

export function FloatingEdge({ id, source, target, markerEnd, data, style }: EdgeProps<HuntFlowEdge>) {
  const sourceNode = useInternalNode(source)
  const targetNode = useInternalNode(target)
  // The live zoom (transform is [x, y, zoom]); the grid counter-scales by its inverse to hold a
  // fixed on-screen size at any zoom.
  const zoom = useStore((s) => s.transform[2])

  // Nodes can be momentarily unmeasured on first mount; skip until both are ready.
  if (!sourceNode || !targetNode) return null

  const { sx, sy, tx, ty, sourcePos, targetPos } = getEdgeParams(sourceNode, targetNode)
  const [path, labelX, labelY] = getBezierPath({
    sourceX: sx,
    sourceY: sy,
    sourcePosition: sourcePos,
    targetPosition: targetPos,
    targetX: tx,
    targetY: ty,
  })

  const artifacts = data?.content ?? []

  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style} />
      {artifacts.length > 0 && (
        <EdgeLabelRenderer>
          {/* Dynamic values (midpoint + inverse zoom) ride in as CSS custom properties; theme.css
              composes the positioning/scale. `nodrag nopan` so hovering the overlay doesn't pan. */}
          <div
            className="edge-artifacts nodrag nopan"
            style={
              {
                '--edge-x': `${labelX}px`,
                '--edge-y': `${labelY}px`,
                '--edge-inv-zoom': 1 / zoom,
                '--edge-grid-cols': gridColumns(artifacts.length),
              } as CSSProperties
            }
          >
            <span className="edge-artifacts__count">{artifacts.length}</span>
            <div className="edge-artifacts__grid">
              {artifacts.map((a) => (
                <ArtifactChip key={a.id} artifact={a} />
              ))}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}
