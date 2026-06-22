// The viewport region: React Flow drawing the active tab's view. React Flow is just the
// widget here — the rail/tabs/panel are plain React around it. The component takes the
// nodes/edges + change handlers from the shell (which owns the state) and reports selection
// back up. It consumes a `view` so that per-view positioning/framing drops in without
// rewiring; the store projects the view's positions onto the nodes before they get here.

import { useEffect, useRef } from 'react'
import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type NodeTypes,
  type OnEdgesChange,
  type OnNodesChange,
  type OnSelectionChangeParams,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import type { HuntFlowEdge, HuntFlowNode } from '../model/flow'
import type { ViewDTO } from '../model/workspace'
import { HuntNode } from '../nodes/HuntNode'

// Module scope so React Flow sees a stable object (it warns if this changes each render).
const nodeTypes: NodeTypes = { hunt: HuntNode }

interface ViewportProps {
  nodes: HuntFlowNode[]
  edges: HuntFlowEdge[]
  onNodesChange: OnNodesChange<HuntFlowNode>
  onEdgesChange: OnEdgesChange<HuntFlowEdge>
  onSelectionChange: (params: OnSelectionChangeParams<HuntFlowNode, HuntFlowEdge>) => void
  view?: ViewDTO
}

function ViewportInner({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onSelectionChange,
}: Omit<ViewportProps, 'view'>) {
  const { fitView } = useReactFlow()
  const wrapperRef = useRef<HTMLDivElement>(null)

  // The known React Flow gotcha: its container can change size out from under it (dragging
  // the panel divider, collapsing the rail). Re-fit on any size change so the graph never
  // looks stale. Coalesced into one frame so a drag doesn't fire fitView per pixel.
  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    let raf = 0
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => fitView())
    })
    ro.observe(el)
    return () => {
      ro.disconnect()
      cancelAnimationFrame(raf)
    }
  }, [fitView])

  return (
    <div className="editor-canvas" ref={wrapperRef}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onSelectionChange={onSelectionChange}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  )
}

export function Viewport({ view: _view, ...inner }: ViewportProps) {
  // Provider so ViewportInner can use the `useReactFlow` hook for fitView.
  return (
    <ReactFlowProvider>
      <ViewportInner {...inner} />
    </ReactFlowProvider>
  )
}
