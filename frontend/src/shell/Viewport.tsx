// The viewport region: React Flow drawing the active view. React Flow is just the widget
// here — the rail/tabs/panel are plain React around it. The component takes the nodes/edges +
// change handlers from the shell (which owns the state) and reports selection back up.
//
// Per-tab framing: each tab remembers its own pan/zoom (two tabs on one view can be framed
// differently). React Flow's camera is imperative, so we (a) RESTORE the active tab's viewport
// whenever the active tab changes (keyed on its id — the view id can't distinguish two tabs on
// one view), and (b) CAPTURE the camera back into the active tab on every pan/zoom (onMoveEnd →
// onViewportChange, the framing analog of dragging a node). A tab still at the identity viewport
// has never been framed, so we auto-fit it instead — and only auto-fit on resize while still
// unframed, so a remembered camera is never clobbered by a panel-divider drag.

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
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
  type OnSelectionChangeParams,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { FloatingEdge } from '../edges/FloatingEdge'
import type { CanvasNode, HuntFlowEdge } from '../model/flow'
import { isIdentityViewport, type ViewportDTO } from '../model/workspace'
import { HuntNode } from '../nodes/HuntNode'
import { LooseArtifactNode } from '../nodes/LooseArtifactNode'

// Module scope so React Flow sees stable objects (it warns if these change each render).
const nodeTypes: NodeTypes = { hunt: HuntNode, artifact: LooseArtifactNode }
const edgeTypes: EdgeTypes = { floating: FloatingEdge }

interface ViewportProps {
  nodes: CanvasNode[]
  edges: HuntFlowEdge[]
  onNodesChange: OnNodesChange<CanvasNode>
  onEdgesChange: OnEdgesChange<HuntFlowEdge>
  /** Deleted edges (Delete/Backspace, or cascaded by a node delete) — return their artifacts. */
  onEdgesDelete: (edges: HuntFlowEdge[]) => void
  /** A user dragged a connection between two nodes — create the edge. */
  onConnect: OnConnect
  onSelectionChange: (params: OnSelectionChangeParams<CanvasNode, HuntFlowEdge>) => void
  /** Id of the active tab — changing it triggers a camera restore. */
  activeTabId?: string
  /** The active tab's saved framing (or undefined before load). */
  viewport?: ViewportDTO
  /** Report a pan/zoom back so it persists into the active tab. */
  onViewportChange: (viewport: ViewportDTO) => void
}

function ViewportInner({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onEdgesDelete,
  onConnect,
  onSelectionChange,
  activeTabId,
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

  // Restore the camera when the active TAB changes (not on every pan): apply its saved
  // framing, or auto-fit if it has never been framed. rAF lets React Flow measure the new
  // nodes first so fitView/setViewport land correctly.
  useEffect(() => {
    const raf = requestAnimationFrame(() => {
      const vp = viewportRef.current
      if (!vp || isIdentityViewport(vp)) fitView()
      else void setViewport(vp)
    })
    return () => cancelAnimationFrame(raf)
  }, [activeTabId, fitView, setViewport])

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
        // Delete/Backspace removal is React Flow's built-in: it emits the 'remove' changes that
        // onNodesChange/onEdgesChange already apply (cascading a node's edges for free). We add
        // only onEdgesDelete, to return a removed edge's artifacts to the pool rather than lose them.
        onEdgesDelete={onEdgesDelete}
        // A drag from one node's handle to another fires onConnect (ConnectionMode.Loose lets
        // any side handle be either end); we create a floating edge from it.
        onConnect={onConnect}
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
