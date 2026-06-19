// The shell: the one stateful, I/O-doing file (the analog of the old app.js). It
// fetches the graph once on load, converts it with the pure `toFlow` adapter, holds
// the result in state, and hands it to <ReactFlow>. Everything clever lives elsewhere
// — adapt.ts (pure mapping) and HuntNode.tsx (pure view). This file just wires them
// to the data and the screen.

import { useEffect } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type NodeTypes,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { fetchGraph } from './api'
import { toFlow, type HuntFlowNode, type HuntFlowEdge } from './adapt'
import { HuntNode } from './HuntNode'
import './theme.css'

// Map our node `type` string to the component that draws it. Defined at module scope
// (not inside App) so React Flow sees a stable object and doesn't warn about it
// changing every render.
const nodeTypes: NodeTypes = { hunt: HuntNode }

export default function App() {
  // useNodesState/useEdgesState give us the state plus the change handlers React Flow
  // needs for built-in interactions (dragging, selection). Positions a drag produces
  // are local-only for now — persisting them is the canvas-sidecar milestone.
  const [nodes, setNodes, onNodesChange] = useNodesState<HuntFlowNode>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<HuntFlowEdge>([])

  useEffect(() => {
    fetchGraph()
      .then((res) => {
        const flow = toFlow(res)
        setNodes(flow.nodes)
        setEdges(flow.edges)
      })
      .catch((err) => console.error('failed to load graph', err))
  }, [setNodes, setEdges])

  return (
    <div className="editor-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  )
}
