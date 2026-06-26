// A "floating" edge: its path is computed from the two nodes' live geometry (edges/floating),
// not from a fixed handle, so it attaches to whichever sides face each other. We render through
// BaseEdge so the artifact-count label and the arrowhead look exactly like a default edge —
// no extra styling. useInternalNode subscribes to each endpoint's measured size + absolute
// position, so the edge re-draws as nodes move (drag, arrange, view switch).

import { BaseEdge, getBezierPath, useInternalNode, type EdgeProps } from '@xyflow/react'

import { getEdgeParams } from './floating'

export function FloatingEdge({ id, source, target, markerEnd, label, style }: EdgeProps) {
  const sourceNode = useInternalNode(source)
  const targetNode = useInternalNode(target)
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

  return (
    <BaseEdge
      id={id}
      path={path}
      markerEnd={markerEnd}
      label={label}
      labelX={labelX}
      labelY={labelY}
      style={style}
    />
  )
}
