// A "floating" edge: its path is computed from the two nodes' live geometry (edges/floating),
// not from a fixed handle, so it attaches to whichever sides face each other. useInternalNode
// subscribes to each endpoint's measured size + absolute position, so the edge re-draws as
// nodes move (drag, arrange, view switch). When the edge carries artifacts we overlay EdgeArtifacts
// at its midpoint — the count pill that explodes into the artifact grid on hover.

import { BaseEdge, getBezierPath, useInternalNode, type EdgeProps } from '@xyflow/react'

import type { HuntFlowEdge } from '../model/flow'
import { EdgeArtifacts } from './EdgeArtifacts'
import { getEdgeParams } from './floating'

export function FloatingEdge({ id, source, target, markerEnd, data, style }: EdgeProps<HuntFlowEdge>) {
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

  const artifacts = data?.content ?? []

  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style} />
      {artifacts.length > 0 && <EdgeArtifacts artifacts={artifacts} labelX={labelX} labelY={labelY} />}
    </>
  )
}
