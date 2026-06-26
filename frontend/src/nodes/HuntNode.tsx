// One small presentational node component. Pure structure: it sets class names and all
// colors/sizes come from theme.css — the component holds no styling values of its own.
//
// A handle on every side. We don't pin the graph to a direction (see edges/FloatingEdge): an
// edge attaches to whichever sides face each other, and with the canvas in ConnectionMode.Loose
// (Viewport.tsx) any handle can be either end of a connection — so a designer can wire nodes
// from any side, whatever shape the graph takes.

import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { HuntFlowNode } from '../model/flow'

const SIDES = [Position.Top, Position.Right, Position.Bottom, Position.Left]

export function HuntNode({ id, data }: NodeProps<HuntFlowNode>) {
  return (
    <div className="hunt-node">
      {SIDES.map((side) => (
        <Handle key={side} type="source" position={side} id={side} />
      ))}
      <div className="hunt-node__label">{data.label || id}</div>
      <div className="hunt-node__action">{data.action}</div>
    </div>
  )
}
