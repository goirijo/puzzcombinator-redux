// The viewport region: React Flow drawing the active view. React Flow is just the widget
// here — the rail/tabs/panel are plain React around it. The component takes the nodes/edges +
// change handlers from the shell (which owns the state) and reports selection back up.
//
// Per-view framing: each view remembers its own pan/zoom. React Flow's camera is imperative,
// so we (a) RESTORE the active view's viewport whenever the view changes (keyed on its id), and
// (b) CAPTURE the camera back into the active view on every pan/zoom (onMoveEnd → onViewportChange,
// the framing analog of dragging a node). A view still at the identity viewport has never been
// framed, so we auto-fit it instead — and only auto-fit on resize while still unframed, so a
// remembered camera is never clobbered by a panel-divider drag.

import { useEffect, useRef } from 'react'
import {
  Background,
  ConnectionMode,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type EdgeTypes,
  type NodeTypes,
  type OnEdgesChange,
  type OnNodesChange,
  type OnSelectionChangeParams,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { FloatingEdge } from '../edges/FloatingEdge'
import type { HuntFlowEdge, HuntFlowNode } from '../model/flow'
import { isIdentityViewport, type ViewportDTO } from '../model/workspace'
import { HuntNode } from '../nodes/HuntNode'

// Module scope so React Flow sees stable objects (it warns if these change each render).
const nodeTypes: NodeTypes = { hunt: HuntNode }
const edgeTypes: EdgeTypes = { floating: FloatingEdge }

interface ViewportProps {
  nodes: HuntFlowNode[]
  edges: HuntFlowEdge[]
  onNodesChange: OnNodesChange<HuntFlowNode>
  onEdgesChange: OnEdgesChange<HuntFlowEdge>
  onSelectionChange: (params: OnSelectionChangeParams<HuntFlowNode, HuntFlowEdge>) => void
  /** Id of the active view — changing it triggers a camera restore. */
  activeViewId?: string
  /** The active view's saved framing (or undefined before load). */
  viewport?: ViewportDTO
  /** Report a pan/zoom back so it persists into the active view. */
  onViewportChange: (viewport: ViewportDTO) => void
}

function ViewportInner({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onSelectionChange,
  activeViewId,
  viewport,
  onViewportChange,
}: ViewportProps) {
  const { fitView, setViewport } = useReactFlow()
  const wrapperRef = useRef<HTMLDivElement>(null)
  // Latest framing, read by the effects below without making them depend on it (which would
  // re-run the camera restore on every pan). Synced in an effect (not during render); the
  // restore reads it inside rAF, so it's current by the time that fires.
  const viewportRef = useRef(viewport)
  useEffect(() => {
    viewportRef.current = viewport
  })

  // Restore the camera when the active VIEW changes (not on every pan): apply its saved
  // framing, or auto-fit if it has never been framed. rAF lets React Flow measure the new
  // nodes first so fitView/setViewport land correctly.
  useEffect(() => {
    const raf = requestAnimationFrame(() => {
      const vp = viewportRef.current
      if (!vp || isIdentityViewport(vp)) fitView()
      else void setViewport(vp)
    })
    return () => cancelAnimationFrame(raf)
  }, [activeViewId, fitView, setViewport])

  // The known React Flow gotcha: its container can change size out from under it (dragging the
  // panel divider, collapsing the rail). Re-fit on resize ONLY while the view is unframed; once
  // it has a remembered camera, leave it alone (React Flow keeps the viewport across resizes).
  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    let raf = 0
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const vp = viewportRef.current
        if (!vp || isIdentityViewport(vp)) fitView()
      })
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
        edgeTypes={edgeTypes}
        // Loose: a connection can start or end on any handle, regardless of source/target — the
        // four-sided, direction-agnostic wiring that floating edges are there to support.
        connectionMode={ConnectionMode.Loose}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onSelectionChange={onSelectionChange}
        onMoveEnd={(_, vp) => onViewportChange({ x: vp.x, y: vp.y, zoom: vp.zoom })}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  )
}

export function Viewport(props: ViewportProps) {
  // Provider so ViewportInner can use the `useReactFlow` hook for fit/set viewport.
  return (
    <ReactFlowProvider>
      <ViewportInner {...props} />
    </ReactFlowProvider>
  )
}
