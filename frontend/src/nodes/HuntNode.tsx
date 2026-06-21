// One small presentational node component. Pure structure: it sets class names and a
// data-role attribute, and all colors/sizes come from theme.css — the component holds
// no styling values of its own. React Flow needs the two Handles for edges to attach;
// we lay out left→right (layer = column), so target is on the left, source on the right.

import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { HuntFlowNode } from '../model/adapt'

export function HuntNode({ id, data }: NodeProps<HuntFlowNode>) {
  return (
    <div className="hunt-node" data-role={data.role}>
      <Handle type="target" position={Position.Left} />
      <div className="hunt-node__label">{data.label || id}</div>
      <div className="hunt-node__action">{data.action}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}
